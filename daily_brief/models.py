from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IndicatorConfig:
    name: str
    series_id: str
    units: str
    frequency: str


@dataclass
class IndicatorSnapshot:
    name: str
    series_id: str
    units: str
    frequency: str
    latest_date: str
    latest_value: Optional[float]
    previous_value: Optional[float]
    abs_change: Optional[float]
    pct_change: Optional[float]
    status: str = "ok"
    note: str = ""


@dataclass
class WarningFlag:
    level: str
    score: int
    message: str
