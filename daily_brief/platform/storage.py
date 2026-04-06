from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Dict, List

from daily_brief.platform.models import IndicatorDefinition, NormalizedObservation


class PlatformStorage:
    def __init__(self, output_dir: Path, db_path: Path) -> None:
        self.output_dir = output_dir
        self.db_path = db_path
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS indicators (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    geography TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    units TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    collection_method TEXT NOT NULL,
                    economic_signal TEXT NOT NULL,
                    interpretation TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    transform_rules_json TEXT NOT NULL,
                    display_priority INTEGER NOT NULL,
                    source_params_json TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    indicator_id TEXT NOT NULL,
                    observation_date TEXT NOT NULL,
                    value REAL,
                    units TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    geography TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    collection_method TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    PRIMARY KEY (indicator_id, observation_date)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_date TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    raw_path TEXT NOT NULL,
                    normalized_path TEXT NOT NULL,
                    indicator_count INTEGER NOT NULL,
                    observation_count INTEGER NOT NULL
                )
                """
            )

    def upsert_indicators(self, indicators: List[IndicatorDefinition], updated_at: str) -> None:
        rows = []
        for item in indicators:
            rows.append(
                (
                    item.id,
                    item.title,
                    item.category,
                    item.geography,
                    item.frequency,
                    item.units,
                    item.source_type,
                    item.source_name,
                    item.source_url,
                    item.collection_method,
                    item.economic_signal,
                    item.interpretation,
                    1 if item.active else 0,
                    json.dumps(item.transform_rules, ensure_ascii=True),
                    item.display_priority,
                    json.dumps(item.source_params, ensure_ascii=True),
                    item.phase,
                    updated_at,
                )
            )

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO indicators (
                    id, title, category, geography, frequency, units, source_type,
                    source_name, source_url, collection_method, economic_signal,
                    interpretation, active, transform_rules_json, display_priority,
                    source_params_json, phase, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    category=excluded.category,
                    geography=excluded.geography,
                    frequency=excluded.frequency,
                    units=excluded.units,
                    source_type=excluded.source_type,
                    source_name=excluded.source_name,
                    source_url=excluded.source_url,
                    collection_method=excluded.collection_method,
                    economic_signal=excluded.economic_signal,
                    interpretation=excluded.interpretation,
                    active=excluded.active,
                    transform_rules_json=excluded.transform_rules_json,
                    display_priority=excluded.display_priority,
                    source_params_json=excluded.source_params_json,
                    phase=excluded.phase,
                    updated_at=excluded.updated_at
                """,
                rows,
            )

    def upsert_observations(self, observations: List[NormalizedObservation]) -> None:
        if not observations:
            return

        rows = [
            (
                row.indicator_id,
                row.observation_date,
                row.value,
                row.units,
                row.frequency,
                row.geography,
                row.source_type,
                row.source_name,
                row.source_url,
                row.collection_method,
                row.collected_at,
                row.status,
                row.note,
            )
            for row in observations
        ]

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO observations (
                    indicator_id, observation_date, value, units, frequency, geography,
                    source_type, source_name, source_url, collection_method,
                    collected_at, status, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_id, observation_date) DO UPDATE SET
                    value=excluded.value,
                    units=excluded.units,
                    frequency=excluded.frequency,
                    geography=excluded.geography,
                    source_type=excluded.source_type,
                    source_name=excluded.source_name,
                    source_url=excluded.source_url,
                    collection_method=excluded.collection_method,
                    collected_at=excluded.collected_at,
                    status=excluded.status,
                    note=excluded.note
                """,
                rows,
            )

    def write_raw_records(self, run_date: str, records: List[Dict[str, object]]) -> Path:
        raw_dir = self.output_dir / "raw" / run_date
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "raw_observations.jsonl"
        with raw_path.open("w", encoding="utf-8") as handle:
            for row in records:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")
        return raw_path

    def write_normalized_export(self, run_date: str, payload: Dict[str, object]) -> Path:
        normalized_dir = self.output_dir / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)
        normalized_path = normalized_dir / f"indicators_{run_date}.json"
        normalized_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return normalized_path

    def record_run(
        self,
        run_date: str,
        generated_at: str,
        raw_path: Path,
        normalized_path: Path,
        indicator_count: int,
        observation_count: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_runs (
                    run_date, generated_at, raw_path, normalized_path,
                    indicator_count, observation_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_date) DO UPDATE SET
                    generated_at=excluded.generated_at,
                    raw_path=excluded.raw_path,
                    normalized_path=excluded.normalized_path,
                    indicator_count=excluded.indicator_count,
                    observation_count=excluded.observation_count
                """,
                (
                    run_date,
                    generated_at,
                    str(raw_path).replace("\\", "/"),
                    str(normalized_path).replace("\\", "/"),
                    indicator_count,
                    observation_count,
                ),
            )

    def recent_values(self, indicator_id: str, limit: int = 12) -> List[Dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT observation_date, value
                FROM observations
                WHERE indicator_id = ? AND status = 'ok' AND value IS NOT NULL
                ORDER BY observation_date DESC
                LIMIT ?
                """,
                (indicator_id, max(2, min(limit, 52))),
            ).fetchall()

        ordered = list(reversed(rows))
        return [
            {"observation_date": row["observation_date"], "value": row["value"]}
            for row in ordered
        ]


def normalize_export_payload(
    run_date: date,
    generated_at: str,
    geography: str,
    signal_environment: str,
    signal_score: int,
    category_summaries: List[Dict[str, object]],
    snapshots: List[Dict[str, object]],
    source_summary: Dict[str, object],
) -> Dict[str, object]:
    return {
        "run_date": run_date.isoformat(),
        "generated_at": generated_at,
        "geography": geography,
        "signal_environment": signal_environment,
        "signal_score": signal_score,
        "categories": category_summaries,
        "indicators": snapshots,
        "source_summary": source_summary,
    }


def snapshots_to_dicts(snapshots) -> List[Dict[str, object]]:
    return [asdict(item) for item in snapshots]
