from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from daily_brief.platform.connectors.base import SourceConnector
from daily_brief.platform.models import ConnectorFetchResult, IndicatorDefinition


class FredConnector(SourceConnector):
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str, user_agent: str = "daily-brief-platform/1.0") -> None:
        self.api_key = api_key
        self.user_agent = user_agent

    def fetch(self, indicator: IndicatorDefinition) -> ConnectorFetchResult:
        fetched_at = datetime.now(timezone.utc).isoformat()
        series_id = str(indicator.source_params.get("series_id", "")).strip()
        if not series_id:
            return ConnectorFetchResult(
                indicator_id=indicator.id,
                status="error",
                note="Missing FRED series_id in source_params.",
                fetched_at=fetched_at,
                raw_observations=[],
            )

        limit = int(indicator.source_params.get("limit", 18))
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": str(max(2, min(limit, 52))),
        }

        try:
            request = Request(
                self.BASE_URL + "?" + urlencode(params),
                headers={"User-Agent": self.user_agent},
            )
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))

            observations = payload.get("observations", [])
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
                note=f"FRED fetch failed: {exc}",
                fetched_at=fetched_at,
                raw_observations=[],
            )
