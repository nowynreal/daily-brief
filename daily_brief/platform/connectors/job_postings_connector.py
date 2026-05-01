from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from daily_brief.platform.connectors.base import SourceConnector
from daily_brief.platform.models import ConnectorFetchResult, IndicatorDefinition


@dataclass
class _SourceMetric:
    source_id: str
    source_name: str
    current_count: float
    previous_count: Optional[float]


class JobPostingsConnector(SourceConnector):
    """Aggregate high-frequency labor-demand signals across multiple job-posting sources."""

    def __init__(self, user_agent: str = "daily-brief-platform/1.0", timeout: int = 30) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch(self, indicator: IndicatorDefinition) -> ConnectorFetchResult:
        fetched_at = datetime.now(timezone.utc).isoformat()
        params = indicator.source_params or {}

        sources = params.get("sources", [])
        if not isinstance(sources, list) or not sources:
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note="Missing source_params.sources for job_postings_aggregate connector.",
                fetched_at=fetched_at,
                raw_observations=[],
            )

        window_days = self._as_int(params.get("window_days", 7), default=7, lower=1, upper=30)
        min_success_sources = self._as_int(
            params.get("min_success_sources", 1),
            default=1,
            lower=1,
            upper=max(1, len(sources)),
        )

        source_metrics: List[_SourceMetric] = []
        errors: List[str] = []

        for source in sources:
            if not isinstance(source, dict):
                errors.append("Invalid source entry: expected object.")
                continue
            if not bool(source.get("enabled", True)):
                continue

            try:
                metric = self._fetch_source_metric(source=source, window_days=window_days)
                source_metrics.append(metric)
            except Exception as exc:
                source_label = str(source.get("name") or source.get("id") or "unknown")
                errors.append(f"{source_label}: {exc}")

        if len(source_metrics) < min_success_sources:
            note = (
                f"Insufficient source coverage for labor demand. "
                f"Needed {min_success_sources}, got {len(source_metrics)}."
            )
            if errors:
                note = note + " Errors: " + " | ".join(errors)
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note=note,
                fetched_at=fetched_at,
                raw_observations=[],
            )

        current_total = sum(item.current_count for item in source_metrics)
        previous_values = [item.previous_count for item in source_metrics if item.previous_count is not None]
        previous_total = sum(previous_values) if previous_values else None

        today = date.today()
        previous_period_date = today - timedelta(days=window_days)

        observations: List[Dict[str, Any]] = [
            {
                "date": today.isoformat(),
                "value": round(current_total, 2),
                "source_breakdown": [
                    {
                        "source_id": item.source_id,
                        "source_name": item.source_name,
                        "current_count": item.current_count,
                        "previous_count": item.previous_count,
                    }
                    for item in source_metrics
                ],
            }
        ]
        if previous_total is not None:
            observations.append(
                {
                    "date": previous_period_date.isoformat(),
                    "value": round(previous_total, 2),
                }
            )

        note_parts: List[str] = []
        if errors:
            note_parts.append("Partial source coverage: " + " | ".join(errors))
        if previous_total is None:
            note_parts.append("Previous-period volume unavailable for one or more sources.")

        return ConnectorFetchResult(
            indicator_id=indicator.id,
            status="ok",
            note=" ".join(note_parts).strip(),
            fetched_at=fetched_at,
            raw_observations=observations,
        )

    def _fetch_source_metric(self, source: Dict[str, Any], window_days: int) -> _SourceMetric:
        source_id = str(source.get("id") or source.get("name") or "source")
        source_name = str(source.get("name") or source_id)
        source_kind = str(source.get("kind", "rss")).strip().lower()

        url = self._resolve_url(source)
        if not url:
            raise ValueError("URL is missing. Provide source.url or source.url_env.")

        headers = {"User-Agent": self.user_agent}
        static_headers = source.get("headers", {})
        if isinstance(static_headers, dict):
            headers.update({str(k): str(v) for k, v in static_headers.items()})

        env_headers = source.get("headers_env", {})
        if isinstance(env_headers, dict):
            for header_name, env_name in env_headers.items():
                env_value = os.getenv(str(env_name), "").strip()
                if env_value:
                    headers[str(header_name)] = env_value

        payload_text = self._fetch_text(url=url, headers=headers)
        weight = self._as_float(source.get("weight", 1.0), default=1.0, lower=0.0)

        if source_kind == "json_count":
            current_count, previous_count = self._parse_json_count(payload_text, source)
        elif source_kind == "json_items":
            current_count, previous_count = self._parse_json_items(payload_text, source, window_days)
        else:
            current_count, previous_count = self._parse_rss(payload_text, window_days)

        return _SourceMetric(
            source_id=source_id,
            source_name=source_name,
            current_count=round(current_count * weight, 2),
            previous_count=round(previous_count * weight, 2) if previous_count is not None else None,
        )

    def _resolve_url(self, source: Dict[str, Any]) -> str:
        raw_url = str(source.get("url", "")).strip()
        if raw_url:
            return raw_url

        env_name = str(source.get("url_env", "")).strip()
        if env_name:
            return os.getenv(env_name, "").strip()
        return ""

    def _fetch_text(self, url: str, headers: Dict[str, str]) -> str:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    def _parse_rss(self, payload_text: str, window_days: int) -> tuple[float, Optional[float]]:
        root = ET.fromstring(payload_text)

        item_dates: List[date] = []
        item_count = 0
        for elem in root.iter():
            local_name = elem.tag.rsplit("}", 1)[-1].lower()
            if local_name not in {"item", "entry"}:
                continue
            item_count += 1

            raw_date: Optional[str] = None
            for child in list(elem):
                child_name = child.tag.rsplit("}", 1)[-1].lower()
                if child_name in {"pubdate", "published", "updated", "date"} and child.text:
                    raw_date = child.text.strip()
                    if raw_date:
                        break
            parsed = self._parse_date(raw_date)
            if parsed:
                item_dates.append(parsed)

        if item_count == 0:
            raise ValueError("No RSS entries returned.")

        if not item_dates:
            return float(item_count), None

        return self._window_counts(item_dates=item_dates, window_days=window_days)

    def _parse_json_count(self, payload_text: str, source: Dict[str, Any]) -> tuple[float, Optional[float]]:
        payload = json.loads(payload_text)

        current_path = str(source.get("current_path", "count"))
        previous_path = str(source.get("previous_path", "")).strip()

        current_value = self._extract_path(payload, current_path)
        if current_value is None:
            raise ValueError(f"Current count path not found: {current_path}")

        previous_value = self._extract_path(payload, previous_path) if previous_path else None
        return float(current_value), (float(previous_value) if previous_value is not None else None)

    def _parse_json_items(
        self,
        payload_text: str,
        source: Dict[str, Any],
        window_days: int,
    ) -> tuple[float, Optional[float]]:
        payload = json.loads(payload_text)

        items_path = str(source.get("items_path", "items"))
        date_field = str(source.get("date_field", "posted_at"))
        items = self._extract_path(payload, items_path)

        if not isinstance(items, list):
            raise ValueError(f"Items path is not a list: {items_path}")

        item_dates: List[date] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            parsed = self._parse_date(item.get(date_field))
            if parsed:
                item_dates.append(parsed)

        if item_dates:
            return self._window_counts(item_dates=item_dates, window_days=window_days)

        return float(len(items)), None

    def _window_counts(self, item_dates: List[date], window_days: int) -> tuple[float, float]:
        today = date.today()
        current_start = today - timedelta(days=window_days - 1)
        previous_start = current_start - timedelta(days=window_days)
        previous_end = current_start - timedelta(days=1)

        current_count = sum(1 for value in item_dates if current_start <= value <= today)
        previous_count = sum(1 for value in item_dates if previous_start <= value <= previous_end)
        return float(current_count), float(previous_count)

    def _extract_path(self, payload: Any, path: str) -> Any:
        if not path:
            return payload

        current = payload
        for token in path.split("."):
            key = token.strip()
            if not key:
                return None

            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                current = current[index] if 0 <= index < len(current) else None
            else:
                return None

            if current is None:
                return None
        return current

    def _parse_date(self, raw_value: Any) -> Optional[date]:
        if raw_value is None:
            return None

        text = str(raw_value).strip()
        if not text:
            return None

        iso_candidate = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(iso_candidate).date()
        except ValueError:
            pass

        try:
            return parsedate_to_datetime(text).date()
        except (TypeError, ValueError):
            pass

        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _as_int(self, raw_value: Any, default: int, lower: int, upper: int) -> int:
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            return default
        return max(lower, min(parsed, upper))

    def _as_float(self, raw_value: Any, default: float, lower: float = 0.0) -> float:
        try:
            parsed = float(raw_value)
        except (TypeError, ValueError):
            return default
        return max(lower, parsed)