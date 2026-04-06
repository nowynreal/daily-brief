from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class IndicatorDefinition:
    id: str
    title: str
    category: str
    geography: str
    frequency: str
    units: str
    source_type: str
    source_name: str
    source_url: str
    collection_method: str
    economic_signal: str
    interpretation: str
    active: bool
    transform_rules: Dict[str, Any] = field(default_factory=dict)
    display_priority: int = 100
    source_params: Dict[str, Any] = field(default_factory=dict)
    phase: str = "phase_1"


@dataclass
class ConnectorFetchResult:
    indicator_id: str
    status: str
    note: str
    fetched_at: str
    raw_observations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class NormalizedObservation:
    indicator_id: str
    observation_date: str
    value: Optional[float]
    units: str
    frequency: str
    geography: str
    source_type: str
    source_name: str
    source_url: str
    collection_method: str
    collected_at: str
    status: str = "ok"
    note: str = ""


@dataclass
class IndicatorSnapshot:
    indicator_id: str
    title: str
    category: str
    geography: str
    frequency: str
    units: str
    latest_date: str
    latest_value: Optional[float]
    previous_value: Optional[float]
    abs_change: Optional[float]
    pct_change: Optional[float]
    change_arrow: str = "->"
    change_label: str = "flat"
    trend_dates: List[str] = field(default_factory=list)
    trend_values: List[float] = field(default_factory=list)
    status: str = "ok"
    note: str = ""
    source_type: str = ""
    source_name: str = ""
    source_url: str = ""
    collection_method: str = ""
    economic_signal: str = "neutral"
    interpretation: str = ""
    display_priority: int = 100
    signal_direction: str = "unknown"
    signal_strength: str = "stable"
    signal_score: int = 0
    normalized_signal: float = 0.0
    reliability: str = "medium"
