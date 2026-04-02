from __future__ import annotations

import json
from datetime import datetime
from typing import List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from daily_brief.models import IndicatorConfig, IndicatorSnapshot


def _safe_float(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_observations(series_id: str, api_key: str) -> list:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": "5",
    }
    url = "https://api.stlouisfed.org/fred/series/observations?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "daily-brief-mvp/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("observations", [])


def fetch_snapshots(indicators: List[IndicatorConfig], fred_api_key: str) -> List[IndicatorSnapshot]:
    snapshots: List[IndicatorSnapshot] = []

    for indicator in indicators:
        try:
            observations = _fetch_observations(indicator.series_id, fred_api_key)
            valid = [obs for obs in observations if obs.get("value") not in {".", None, ""}]
            if not valid:
                snapshots.append(
                    IndicatorSnapshot(
                        name=indicator.name,
                        series_id=indicator.series_id,
                        units=indicator.units,
                        frequency=indicator.frequency,
                        latest_date="NA",
                        latest_value=None,
                        previous_value=None,
                        abs_change=None,
                        pct_change=None,
                        status="error",
                        note="No valid observation.",
                    )
                )
                continue

            latest_raw = valid[0]
            previous_raw = valid[1] if len(valid) > 1 else None
            latest = _safe_float(latest_raw.get("value"))
            previous = _safe_float(previous_raw.get("value")) if previous_raw else None

            abs_change = None
            pct_change = None
            if latest is not None and previous is not None:
                abs_change = latest - previous
                if previous != 0:
                    pct_change = (abs_change / previous) * 100.0

            snapshots.append(
                IndicatorSnapshot(
                    name=indicator.name,
                    series_id=indicator.series_id,
                    units=indicator.units,
                    frequency=indicator.frequency,
                    latest_date=latest_raw.get("date", datetime.utcnow().date().isoformat()),
                    latest_value=latest,
                    previous_value=previous,
                    abs_change=abs_change,
                    pct_change=pct_change,
                )
            )
        except Exception as exc:
            snapshots.append(
                IndicatorSnapshot(
                    name=indicator.name,
                    series_id=indicator.series_id,
                    units=indicator.units,
                    frequency=indicator.frequency,
                    latest_date="NA",
                    latest_value=None,
                    previous_value=None,
                    abs_change=None,
                    pct_change=None,
                    status="error",
                    note=f"Fetch failed: {exc}",
                )
            )

    return snapshots
