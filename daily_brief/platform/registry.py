from __future__ import annotations

import json
from pathlib import Path
from typing import List

from daily_brief.platform.models import IndicatorDefinition


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "indicator_registry_tn.json"


def _as_indicator_definition(item: dict) -> IndicatorDefinition:
    return IndicatorDefinition(
        id=item["id"],
        title=item["title"],
        category=item["category"],
        geography=item.get("geography", "Tennessee"),
        frequency=item.get("frequency", "monthly"),
        units=item.get("units", "index"),
        source_type=item.get("source_type", "official_dataset"),
        source_name=item.get("source_name", "Unknown source"),
        source_url=item.get("source_url", ""),
        collection_method=item.get("collection_method", "manual"),
        economic_signal=item.get("economic_signal", "neutral"),
        interpretation=item.get("interpretation", ""),
        active=bool(item.get("active", True)),
        transform_rules=item.get("transform_rules", {}),
        display_priority=int(item.get("display_priority", 100)),
        source_params=item.get("source_params", {}),
        phase=item.get("phase", "phase_1"),
    )


def load_indicator_registry(registry_path: Path | None = None) -> List[IndicatorDefinition]:
    path = registry_path or DEFAULT_REGISTRY_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    indicators = [_as_indicator_definition(item) for item in payload.get("indicators", [])]
    return sorted(indicators, key=lambda item: (item.display_priority, item.id))


def list_active_indicators(indicators: List[IndicatorDefinition]) -> List[IndicatorDefinition]:
    return [item for item in indicators if item.active]
