from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List

from daily_brief.platform.connectors.fred_connector import FredConnector
from daily_brief.platform.connectors.google_trends_connector import GoogleTrendsConnector
from daily_brief.platform.models import ConnectorFetchResult, IndicatorSnapshot
from daily_brief.platform.normalization import normalize_fetch_result
from daily_brief.platform.registry import list_active_indicators, load_indicator_registry
from daily_brief.platform.scoring import (
    apply_indicator_signal,
    build_category_summaries,
    platform_signal_environment,
)
from daily_brief.platform.storage import PlatformStorage, normalize_export_payload


def _source_summary(indicators: List[dict]) -> Dict[str, object]:
    by_source: Dict[str, int] = {}
    by_method: Dict[str, int] = {}
    reliability_mix = {"high": 0, "medium": 0, "low": 0}

    for item in indicators:
        source_name = str(item.get("source_name", "Unknown"))
        by_source[source_name] = by_source.get(source_name, 0) + 1

        method = str(item.get("collection_method", "Unknown"))
        by_method[method] = by_method.get(method, 0) + 1

        reliability = str(item.get("reliability", "medium"))
        if reliability not in reliability_mix:
            reliability = "medium"
        reliability_mix[reliability] += 1

    return {
        "by_source": by_source,
        "by_collection_method": by_method,
        "reliability_mix": reliability_mix,
    }


def _headline_counts(snapshots: List[IndicatorSnapshot]) -> Dict[str, int]:
    return {
        "improving": sum(1 for item in snapshots if item.signal_direction == "improving"),
        "worsening": sum(1 for item in snapshots if item.signal_direction == "worsening"),
        "stable": sum(1 for item in snapshots if item.signal_direction == "stable"),
        "unknown": sum(1 for item in snapshots if item.signal_direction == "unknown" or item.status != "ok"),
    }


def run_indicator_pipeline(
    output_dir: Path,
    fred_api_key: str,
    geography: str,
    registry_path: Path | None = None,
    db_path: Path | None = None,
) -> Dict[str, object]:
    generated_at = datetime.now(timezone.utc).isoformat()
    run_day = date.today()
    run_date = run_day.isoformat()

    registry_file = registry_path or (Path(__file__).resolve().parents[1] / "config" / "indicator_registry_tn.json")
    all_indicators = load_indicator_registry(registry_file)
    active_indicators = list_active_indicators(all_indicators)

    storage = PlatformStorage(output_dir=output_dir, db_path=(db_path or output_dir / "indicator_store.sqlite3"))
    storage.initialize()
    storage.upsert_indicators(all_indicators, updated_at=generated_at)

    connectors = {}
    if fred_api_key:
        connectors["fred_api"] = FredConnector(api_key=fred_api_key)
    connectors["google_trends_api"] = GoogleTrendsConnector()

    snapshots: List[IndicatorSnapshot] = []
    normalized_rows = []
    raw_records = []

    for indicator in active_indicators:
        connector = connectors.get(indicator.collection_method)
        if connector is None:
            fetch_result = ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note=f"No connector configured for method: {indicator.collection_method}",
                fetched_at=generated_at,
                raw_observations=[],
            )
        else:
            fetch_result = connector.fetch(indicator)

        snapshot, observations, raw_record = normalize_fetch_result(indicator, fetch_result)
        snapshots.append(apply_indicator_signal(snapshot, indicator))
        normalized_rows.extend(observations)
        raw_records.append(raw_record)

    storage.upsert_observations(normalized_rows)

    for snapshot in snapshots:
        history = storage.recent_values(snapshot.indicator_id, limit=14)
        if history:
            snapshot.trend_dates = [str(item["observation_date"]) for item in history]
            snapshot.trend_values = [float(item["value"]) for item in history if item.get("value") is not None]

    snapshots = sorted(snapshots, key=lambda item: (item.display_priority, item.indicator_id))
    snapshot_dicts = [asdict(item) for item in snapshots]

    category_summaries = build_category_summaries(snapshots)
    category_indexes = [
        {
            "category": item.get("category"),
            "index_name": item.get("index_name"),
            "status": item.get("status"),
            "composite_score": item.get("composite_score"),
            "indicator_count": item.get("indicator_count"),
        }
        for item in category_summaries
    ]
    total_signal_score = sum(item.signal_score for item in snapshots)
    signal_environment = platform_signal_environment(total_signal_score)

    headline_counts = _headline_counts(snapshots)
    source_summary = _source_summary(snapshot_dicts)

    methodology_notes = [
        "Source priority follows official/public datasets first, then structured APIs, then controlled scraping only when needed.",
        "Current active Tennessee-first indicators are primarily FRED-backed for reliability and low operational cost.",
        "Signals are rule-based and deterministic; thresholds are configurable in the indicator registry.",
    ]

    normalized_payload = normalize_export_payload(
        run_date=run_day,
        generated_at=generated_at,
        geography=geography,
        signal_environment=signal_environment,
        signal_score=total_signal_score,
        category_summaries=category_summaries,
        snapshots=snapshot_dicts,
        source_summary=source_summary,
    )

    raw_path = storage.write_raw_records(run_date=run_date, records=raw_records)
    normalized_path = storage.write_normalized_export(run_date=run_date, payload=normalized_payload)
    storage.record_run(
        run_date=run_date,
        generated_at=generated_at,
        raw_path=raw_path,
        normalized_path=normalized_path,
        indicator_count=len(active_indicators),
        observation_count=len(normalized_rows),
    )

    return {
        "generated_at": generated_at,
        "run_date": run_date,
        "geography": geography,
        "signal_environment": signal_environment,
        "signal_score": total_signal_score,
        "headline_counts": headline_counts,
        "categories": category_summaries,
        "category_indexes": category_indexes,
        "indicators": snapshot_dicts,
        "source_summary": source_summary,
        "methodology_notes": methodology_notes,
        "artifacts": {
            "registry": str(registry_file).replace("\\", "/"),
            "raw": str(raw_path).replace("\\", "/"),
            "normalized": str(normalized_path).replace("\\", "/"),
            "sqlite": str(storage.db_path).replace("\\", "/"),
        },
        "counts": {
            "active": len(active_indicators),
            "inactive": len(all_indicators) - len(active_indicators),
            "observations": len(normalized_rows),
        },
    }
