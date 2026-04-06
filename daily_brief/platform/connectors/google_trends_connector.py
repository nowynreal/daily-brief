from __future__ import annotations

import importlib
from datetime import datetime, timezone

from daily_brief.platform.connectors.base import SourceConnector
from daily_brief.platform.models import ConnectorFetchResult, IndicatorDefinition


class GoogleTrendsConnector(SourceConnector):
    def __init__(self, hl: str = "en-US", tz: int = 360) -> None:
        self.hl = hl
        self.tz = tz

    def fetch(self, indicator: IndicatorDefinition) -> ConnectorFetchResult:
        fetched_at = datetime.now(timezone.utc).isoformat()
        params = indicator.source_params or {}

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [item.strip() for item in keywords.split(",") if item.strip()]

        if not keywords:
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note="Missing Google Trends keywords in source_params.",
                fetched_at=fetched_at,
                raw_observations=[],
            )

        geo = str(params.get("geo", "US-TN"))
        timeframe = str(params.get("timeframe", "today 3-m"))

        try:
            trend_module = importlib.import_module("pytrends.request")
            TrendReq = getattr(trend_module, "TrendReq")
        except Exception:
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note="pytrends package is not installed.",
                fetched_at=fetched_at,
                raw_observations=[],
            )

        try:
            client = TrendReq(hl=self.hl, tz=self.tz, retries=2, backoff_factor=0.2)
            client.build_payload(keywords, timeframe=timeframe, geo=geo)
            frame = client.interest_over_time()

            if frame is None or frame.empty:
                return ConnectorFetchResult(
                    indicator_id=indicator.id,
                    status="error",
                    note="Google Trends returned no data.",
                    fetched_at=fetched_at,
                    raw_observations=[],
                )

            if "isPartial" in frame.columns:
                frame = frame.drop(columns=["isPartial"])

            series = frame.mean(axis=1) if len(frame.columns) > 1 else frame.iloc[:, 0]
            observations = []
            for idx, value in series.items():
                date_text = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
                observations.append({"date": date_text, "value": float(value)})

            observations.sort(key=lambda row: row["date"], reverse=True)
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="ok",
                note="",
                fetched_at=fetched_at,
                raw_observations=observations,
            )
        except Exception as exc:
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note=f"Google Trends fetch failed: {exc}",
                fetched_at=fetched_at,
                raw_observations=[],
            )
