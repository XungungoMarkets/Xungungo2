from abc import ABC, abstractmethod
from typing import Dict, List

import pandas as pd

from xungungo.core.models import ChartSeries


class IndicatorBase(ABC):
    id: str
    name: str
    description: str

    @abstractmethod
    def default_config(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def config_schema(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def apply(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def chart_series(self) -> List[ChartSeries]:
        raise NotImplementedError
