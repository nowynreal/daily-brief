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

        paths = save_brief(
            settings.output_dir,
            settings.site_dir,
            settings.region_name,
            brief_markdown,
            snapshots,
            flags,
        )

        append_history(
            settings.history_file,
            paths,
            signal_environment(flags),
            signal_score(flags),
        )
        index_path = render_index(settings.site_dir, settings.history_file)

        review_url = settings.base_review_url.strip() or f"briefs/{date.today().isoformat()}.html"
        if settings.send_email:
            send_ready_email(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_user=settings.smtp_user,
                smtp_password=settings.smtp_password,
                email_from=settings.email_from,
                email_to=settings.email_to,
                email_cc=settings.email_cc,
                reply_to=settings.reply_to,
                review_url=review_url,
                brief_date=date.today().isoformat(),
            )

        print("Daily brief generated.")
        print(f"- Markdown: {paths['markdown']}")
        print(f"- JSON: {paths['json']}")
        print(f"- HTML: {paths['html']}")
        print(f"- Index: {index_path}")
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
