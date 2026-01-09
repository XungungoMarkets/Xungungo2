from dataclasses import dataclass
from typing import Optional


@dataclass
class ChartSeries:
    series_id: str
    name: str
    column: str
    color: Optional[str] = None
    pane: str = "main"
