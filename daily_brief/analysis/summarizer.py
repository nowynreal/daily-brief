from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import List

from daily_brief.analysis.rules import signal_environment
from daily_brief.models import IndicatorSnapshot, WarningFlag


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


def build_template_brief(region_name: str, snapshots: List[IndicatorSnapshot], flags: List[WarningFlag]) -> str:
    ok_count = sum(1 for item in snapshots if item.status == "ok")
    fail_count = sum(1 for item in snapshots if item.status != "ok")

    lines = [
        f"# Daily Brief - {date.today().isoformat()}",
        "",
        "## Executive Summary",
        f"- Region: {region_name}",
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

    lines.extend(["", "## Caveats", "- This MVP uses deterministic, rule-based summaries by default."])
    return "\n".join(lines)


def maybe_build_llm_brief(
    use_llm: bool,
    api_key: str,
    model: str,
    region_name: str,
    snapshots: List[IndicatorSnapshot],
    flags: List[WarningFlag],
) -> str:
    if not use_llm:
        return build_template_brief(region_name, snapshots, flags)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("USE_LLM=true but openai package is not installed.") from exc

    client = OpenAI(api_key=api_key)
    prompt = {
        "region": region_name,
        "snapshots": [asdict(item) for item in snapshots],
        "flags": [asdict(item) for item in flags],
        "requirements": [
            "Keep under 500 words.",
            "Use markdown headings.",
            "State clearly if any indicator failed.",
            "Do not invent data.",
        ],
    }

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "You are a concise economic briefing assistant. Stay factual and specific.",
            },
            {"role": "user", "content": str(prompt)},
        ],
    )
    return response.output_text.strip()
