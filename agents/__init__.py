"""
StockScout v4 Agents
"""

try:
    from .analysts import AnalystTeam
except ImportError:
    from analysts import AnalystTeam
try:
    from .researchers import DebateEngine
except ImportError:
    from researchers import DebateEngine
try:
    from .traders import TradingDesk
except ImportError:
    from traders import TradingDesk

__all__ = ["AnalystTeam", "DebateEngine", "TradingDesk"]
