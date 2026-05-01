from __future__ import annotations

import json
import traceback
from dataclasses import asdict
from datetime import date
from typing import List

from daily_brief.analysis.rules import build_warning_flags, signal_environment, signal_score
from daily_brief.collectors.fred_collector import fetch_snapshots
from daily_brief.config.settings import DEFAULT_INDICATORS, load_settings, validate_settings
from daily_brief.models import IndicatorSnapshot, WarningFlag
from daily_brief.platform.pipeline import run_indicator_pipeline
from daily_brief.services.emailer import send_ready_email
from daily_brief.services.storage import append_history, render_index, save_brief


def _display_date(value: date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _format_value(value, units: str) -> str:
    if value is None:
        return "NA"
    if units == "percent":
        return f"{value:.2f}%"
    if units == "count":
        return f"{value:,.0f}"
    if units == "thousands":
        return f"{value:,.1f} thousand"
    return f"{value:,.2f}"


def _build_review_url(base_review_url: str, brief_date_iso: str) -> str:
    base = (base_review_url or "").strip()
    fallback = f"briefs/{brief_date_iso}.html"
    if not base:
        return fallback

    # If a concrete page URL is provided, keep it.
    if base.endswith(".html"):
        return base

    # BASE_REVIEW_URL may point to a site root or /briefs; append the daily page.
    if base.endswith("/briefs"):
        return f"{base}/{brief_date_iso}.html"
    return f"{base.rstrip('/')}/briefs/{brief_date_iso}.html"


def _build_platform_summary_markdown(platform_payload: dict) -> str:
    lines = [
        "## Platform Highlights",
        f"- Expanded signal environment: {platform_payload.get('signal_environment', 'Unknown')}",
        f"- Expanded signal score: {platform_payload.get('signal_score', 0)}",
    ]

    counts = platform_payload.get("headline_counts", {})
    lines.append(
        "- Indicator directions: "
        + f"{counts.get('improving', 0)} improving, "
        + f"{counts.get('worsening', 0)} worsening, "
        + f"{counts.get('stable', 0)} stable, "
        + f"{counts.get('unknown', 0)} unknown"
    )

    phase_summary = platform_payload.get("phase_summary", {})
    if phase_summary:
        lines.extend(["", "## Roadmap Status"])
        for phase_name, counts_by_phase in sorted(phase_summary.items()):
            lines.append(
                "- "
                + f"{phase_name}: {counts_by_phase.get('active', 0)} active, "
                + f"{counts_by_phase.get('inactive', 0)} inactive, "
                + f"{counts_by_phase.get('total', 0)} total"
            )

    lines.extend(["", "## Category Snapshot"])
    for category in platform_payload.get("categories", []):
        category_name = category.get("category", "Unknown category")
        signal = category.get("signal", "stable")
        cat_counts = category.get("counts", {})
        lines.append(
            "- "
            + f"{category_name}: signal={signal}; "
            + f"improving={cat_counts.get('improving', 0)}, "
            + f"worsening={cat_counts.get('worsening', 0)}, "
            + f"stable={cat_counts.get('stable', 0)}, "
            + f"unknown={cat_counts.get('unknown', 0)}"
        )

    methods = platform_payload.get("source_summary", {}).get("by_collection_method", {})
    if methods:
        lines.extend(["", "## Source Methods"])
        for method, count in sorted(methods.items()):
            lines.append(f"- {method}: {count} indicator(s)")

    return "\n".join(lines)


def build_brief_markdown(region_name: str, snapshots: List[IndicatorSnapshot], flags: List[WarningFlag]) -> str:
    today = _display_date(date.today())
    ok_count = sum(1 for item in snapshots if item.status == "ok")
    fail_count = sum(1 for item in snapshots if item.status != "ok")

    lines = [
        f"# BERC Daily Briefer | {today}",
        "Prepared by Semih Yucekan",
        "",
        "## Executive Summary",
        f"- Region: {region_name}",
        "- Audience: Faculty-style morning read",
        f"- Signal environment: {signal_environment(flags)}",
        f"- Indicators collected successfully: {ok_count}",
        f"- Indicators failed or missing: {fail_count}",
        "",
        "## Indicator Snapshot",
    ]

    for item in snapshots:
        lines.append(
            "- "
            + f"{item.name} ({item.series_id}): latest {_format_value(item.latest_value, item.units)} "
            + f"on {item.latest_date}; previous {_format_value(item.previous_value, item.units)}; "
            + f"change {_format_value(item.abs_change, item.units)}; "
            + ("pct change NA" if item.pct_change is None else f"pct change {item.pct_change:.2f}%")
        )

    lines.extend(["", "## Warning Flags"])
    for flag in flags:
        lines.append(f"- [{flag.level.upper()}] {flag.message}")

    lines.extend(["", "## Caveats", "- This edition uses deterministic, rule-based summarization."])
    return "\n".join(lines)


def build_llm_brief_markdown(
    region_name: str,
    snapshots: List[IndicatorSnapshot],
    flags: List[WarningFlag],
    openai_api_key: str,
    openai_model: str,
) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("USE_LLM=true but openai package is not installed.") from exc

    client = OpenAI(api_key=openai_api_key)
    prompt = {
        "brand": "BERC Daily Briefer",
        "author": "Semih Yucekan",
        "region": region_name,
        "date": _display_date(date.today()),
        "signal_environment": signal_environment(flags),
        "snapshots": [asdict(item) for item in snapshots],
        "flags": [asdict(item) for item in flags],
        "requirements": [
            "Write as a clear faculty newsletter.",
            "Keep under 500 words.",
            "Use markdown headings and bullets.",
            "Do not invent missing data.",
            "Title must include a human-readable date.",
        ],
    }

    response = client.responses.create(
        model=openai_model,
        input=[
            {
                "role": "system",
                "content": "You write concise, readable economic daily briefings. Keep language calm and practical.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
    )
    return response.output_text.strip()


def main() -> int:
    settings = load_settings()

    try:
        validate_settings(settings)
        snapshots = fetch_snapshots(DEFAULT_INDICATORS, settings.fred_api_key)
        flags = build_warning_flags(snapshots)

        platform_payload = None
        try:
            platform_payload = run_indicator_pipeline(
                output_dir=settings.output_dir,
                fred_api_key=settings.fred_api_key,
                geography=settings.region_name,
                registry_path=settings.indicator_registry_path,
                db_path=settings.indicator_db_path,
            )
        except Exception as platform_exc:
            print(f"WARN: indicator platform pipeline failed; continuing legacy flow. {platform_exc}")

        if settings.use_llm:
            brief_markdown = build_llm_brief_markdown(
                settings.region_name,
                snapshots,
                flags,
                settings.openai_api_key,
                settings.openai_model,
            )
        else:
            brief_markdown = build_brief_markdown(settings.region_name, snapshots, flags)

        if platform_payload:
            brief_markdown = brief_markdown + "\n\n" + _build_platform_summary_markdown(platform_payload)

        paths = save_brief(
            settings.output_dir,
            settings.site_dir,
            settings.region_name,
            brief_markdown,
            snapshots,
            flags,
            platform_payload=platform_payload,
        )

        alert_count = len([f for f in flags if f.score > 0])
        append_history(
            settings.history_file,
            paths,
            signal_environment(flags),
            signal_score(flags),
            alert_count=alert_count,
        )
        index_path = render_index(settings.site_dir, settings.history_file)

        today_iso = date.today().isoformat()
        review_url = _build_review_url(settings.base_review_url, today_iso)
        if settings.send_email:
            send_ready_email(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_user=settings.smtp_user,
                smtp_password=settings.smtp_password,
                email_from_name=settings.email_from_name,
                email_from=settings.email_from,
                email_to=settings.email_to,
                email_cc=settings.email_cc,
                reply_to=settings.reply_to,
                review_url=review_url,
                brief_date=today_iso,
            )

        print("Daily brief generated.")
        print(f"- Markdown: {paths['markdown']}")
        print(f"- JSON: {paths['json']}")
        print(f"- HTML: {paths['html']}")
        print(f"- Index: {index_path}")
        if platform_payload:
            platform_artifacts = platform_payload.get("artifacts", {})
            print(f"- Platform normalized data: {platform_artifacts.get('normalized', 'NA')}")
            print(f"- Platform raw data: {platform_artifacts.get('raw', 'NA')}")
            print(f"- Platform SQLite: {platform_artifacts.get('sqlite', 'NA')}")
        if settings.send_email:
            print("- Notification email sent.")
        else:
            print("- Email disabled (SEND_EMAIL=false).")

        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
