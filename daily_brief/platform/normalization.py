from __future__ import annotations

from typing import Dict, List, Tuple

from daily_brief.platform.models import (
    ConnectorFetchResult,
    IndicatorDefinition,
    IndicatorSnapshot,
    NormalizedObservation,
)


def _safe_float(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reliability_label(source_type: str, collection_method: str) -> str:
    key = f"{source_type}:{collection_method}".lower()
    if "official" in key or "fred" in key:
        return "high"
    if "api" in key:
        return "medium"
    if "scrape" in key:
        return "low"
    return "medium"


def normalize_fetch_result(
    indicator: IndicatorDefinition,
    fetch_result: ConnectorFetchResult,
) -> Tuple[IndicatorSnapshot, List[NormalizedObservation], Dict[str, object]]:
    raw_valid = [
        row for row in fetch_result.raw_observations if row.get("value") not in {None, "", "."}
    ]

    normalized_rows: List[NormalizedObservation] = []
    for row in raw_valid:
        value = _safe_float(row.get("value"))
        normalized_rows.append(
            NormalizedObservation(
                indicator_id=indicator.id,
                observation_date=row.get("date", "NA"),
                value=value,
                units=indicator.units,
                frequency=indicator.frequency,
                geography=indicator.geography,
                source_type=indicator.source_type,
                source_name=indicator.source_name,
                source_url=indicator.source_url,
                collection_method=indicator.collection_method,
                collected_at=fetch_result.fetched_at,
                status="ok" if value is not None else "error",
                note="" if value is not None else "Observation value is not numeric.",
            )
        )

    latest = normalized_rows[0] if normalized_rows else None
    previous = normalized_rows[1] if len(normalized_rows) > 1 else None

    latest_value = latest.value if latest else None
    previous_value = previous.value if previous else None
    abs_change = None
    pct_change = None
    if latest_value is not None and previous_value is not None:
        abs_change = latest_value - previous_value
        if previous_value != 0:
            pct_change = (abs_change / previous_value) * 100.0

    if fetch_result.status != "ok":
        status = "error"
        note = fetch_result.note
    elif not normalized_rows:
        status = "error"
        note = "No valid observations returned by source."
    else:
        status = "ok"
        note = ""

    max_points = int(indicator.transform_rules.get("max_trend_points", 10))
    trend_rows = normalized_rows[: max(2, min(max_points, len(normalized_rows)))] if normalized_rows else []

    snapshot = IndicatorSnapshot(
        indicator_id=indicator.id,
        title=indicator.title,
        category=indicator.category,
        geography=indicator.geography,
        frequency=indicator.frequency,
        units=indicator.units,
        latest_date=latest.observation_date if latest else "NA",
        latest_value=latest_value,
        previous_value=previous_value,
        abs_change=abs_change,
        pct_change=pct_change,
        trend_dates=[row.observation_date for row in reversed(trend_rows)],
        trend_values=[float(row.value) for row in reversed(trend_rows) if row.value is not None],
        status=status,
        note=note,
        source_type=indicator.source_type,
        source_name=indicator.source_name,
        source_url=indicator.source_url,
        collection_method=indicator.collection_method,
        economic_signal=indicator.economic_signal,
        interpretation=indicator.interpretation,
        display_priority=indicator.display_priority,
        reliability=_reliability_label(indicator.source_type, indicator.collection_method),
    )

    raw_record = {
        "indicator_id": indicator.id,
        "title": indicator.title,
        "category": indicator.category,
        "collected_at": fetch_result.fetched_at,
        "status": fetch_result.status,
        "note": fetch_result.note,
        "source_name": indicator.source_name,
        "source_type": indicator.source_type,
        "source_url": indicator.source_url,
        "collection_method": indicator.collection_method,
        "observations": fetch_result.raw_observations,
    }
    return snapshot, normalized_rows, raw_record
