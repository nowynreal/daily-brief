from __future__ import annotations

from typing import Dict, List

from daily_brief.models import IndicatorSnapshot, WarningFlag


def build_warning_flags(snapshots: List[IndicatorSnapshot]) -> List[WarningFlag]:
    by_name: Dict[str, IndicatorSnapshot] = {s.name: s for s in snapshots}
    flags: List[WarningFlag] = []

    tn_ur = by_name.get("Tennessee Unemployment Rate")
    if tn_ur and tn_ur.abs_change is not None and tn_ur.abs_change > 0.2:
        flags.append(WarningFlag("watch", 2, "Tennessee unemployment increased by more than 0.2 points."))

    claims = by_name.get("US Initial Jobless Claims")
    if claims and claims.pct_change is not None and claims.pct_change > 10:
        flags.append(WarningFlag("watch", 2, "US initial claims jumped more than 10%."))

    mortgage = by_name.get("30Y Mortgage Rate")
    if mortgage and mortgage.abs_change is not None and mortgage.abs_change > 0.15:
        flags.append(WarningFlag("signal", 1, "Mortgage rates moved up noticeably this period."))

    cpi = by_name.get("US CPI")
    if cpi and cpi.pct_change is not None and cpi.pct_change > 0.6:
        flags.append(WarningFlag("signal", 1, "Monthly CPI move is elevated."))

    if not flags:
        flags.append(WarningFlag("stable", 0, "No major warning flags triggered."))

    return sorted(flags, key=lambda item: item.score, reverse=True)


def signal_score(flags: List[WarningFlag]) -> int:
    return sum(flag.score for flag in flags)


def signal_environment(flags: List[WarningFlag]) -> str:
    score = signal_score(flags)
    if score >= 5:
        return "Elevated risk watch"
    if score >= 2:
        return "Moderate watch"
    return "Stable to mixed"
