from __future__ import annotations

from abc import ABC, abstractmethod

from daily_brief.platform.models import ConnectorFetchResult, IndicatorDefinition


class SourceConnector(ABC):
    @abstractmethod
    def fetch(self, indicator: IndicatorDefinition) -> ConnectorFetchResult:
        raise NotImplementedError
