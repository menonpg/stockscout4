"""
StockScout v4 - The AI Trading Desk

Multi-agent trading analysis with debate mechanism and risk gates.
"""

__version__ = "0.1.0"

try:
    from .config import Config, DEFAULT_CONFIG
except ImportError:
    from config import Config, DEFAULT_CONFIG
try:
    from .pipeline import StockScoutPipeline
except ImportError:
    from pipeline import StockScoutPipeline

__all__ = ["Config", "DEFAULT_CONFIG", "StockScoutPipeline"]
