"""
Backtestable trading strategies.

Each strategy implements the Strategy protocol:
- generate_signals(bars, portfolio) -> List[Signal]
"""

from .simple_rsi import SimpleRSIStrategy
from .macd_crossover import MACDCrossoverStrategy

__all__ = [
    "SimpleRSIStrategy",
    "MACDCrossoverStrategy",
]
