from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from daily_brief.platform.models import IndicatorDefinition, IndicatorSnapshot


def _metric_value(snapshot: IndicatorSnapshot, metric_name: str):
    if metric_name == "pct_change":
        return snapshot.pct_change
    return snapshot.abs_change


def _worsening_direction(economic_signal: str, metric: float) -> str:
    if economic_signal == "higher_is_worse":
        if metric > 0:
            return "worsening"
        if metric < 0:
            return "improving"
        return "stable"

    if economic_signal == "higher_is_better":
        if metric < 0:
            return "worsening"
        if metric > 0:
            return "improving"
        return "stable"

    if economic_signal == "lower_is_worse":
        if metric < 0:
            return "worsening"
        if metric > 0:
            return "improving"
        return "stable"

    if economic_signal == "lower_is_better":
        if metric > 0:
            return "worsening"
        if metric < 0:
            return "improving"
        return "stable"

    return "mixed"


def apply_indicator_signal(snapshot: IndicatorSnapshot, indicator: IndicatorDefinition) -> IndicatorSnapshot:
    if snapshot.status != "ok":
        snapshot.signal_direction = "unknown"
        snapshot.signal_strength = "stable"
        snapshot.signal_score = 0
        return snapshot

    rules = indicator.transform_rules or {}
    metric_name = str(rules.get("signal_metric", "abs_change"))
    metric = _metric_value(snapshot, metric_name)
    if metric is None:
        snapshot.signal_direction = "unknown"
        snapshot.signal_strength = "stable"
        snapshot.signal_score = 0
        return snapshot

    watch_threshold = float(rules.get("watch_threshold", 0.0))
    alert_threshold = float(rules.get("alert_threshold", watch_threshold * 2 if watch_threshold else 0.0))

    direction = _worsening_direction(indicator.economic_signal, metric)
    magnitude = abs(metric)

    strength = "stable"
    score = 0
    if direction == "worsening":
        if alert_threshold and magnitude >= alert_threshold:
            strength = "elevated"
            score = 2
        elif watch_threshold and magnitude >= watch_threshold:
            strength = "watch"
            score = 1
    elif direction == "mixed":
        if alert_threshold and magnitude >= alert_threshold:
            strength = "watch"
            score = 1

    snapshot.signal_direction = direction
    snapshot.signal_strength = strength
    snapshot.signal_score = score
    return snapshot


def platform_signal_environment(score: int) -> str:
    if score >= 8:
        return "Elevated risk watch"
    if score >= 3:
        return "Moderate watch"
    return "Stable to mixed"


def build_category_summaries(snapshots: List[IndicatorSnapshot]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[IndicatorSnapshot]] = defaultdict(list)
    for item in snapshots:
        grouped[item.category].append(item)

    summaries: List[Dict[str, object]] = []
    for category in sorted(grouped):
        items = sorted(grouped[category], key=lambda value: value.display_priority)
        improving = sum(1 for row in items if row.signal_direction == "improving")
        worsening = sum(1 for row in items if row.signal_direction == "worsening")
        stable = sum(1 for row in items if row.signal_direction == "stable")
        unknown = sum(1 for row in items if row.signal_direction == "unknown" or row.status != "ok")
        score = sum(row.signal_score for row in items)

        signal = "stable"
        if score >= 3:
            signal = "elevated"
        elif score >= 1:
            signal = "watch"

        summaries.append(
            {
                "category": category,
                "signal": signal,
                "score": score,
                "counts": {
                    "improving": improving,
                    "worsening": worsening,
                    "stable": stable,
                    "unknown": unknown,
                },
                "indicator_count": len(items),
                "indicators": [row.__dict__ for row in items],
            }
        )

    return summaries
