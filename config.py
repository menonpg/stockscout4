"""
StockScout v4 Configuration
"""

import os
from typing import Optional

class Config:
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("SS4_LLM_PROVIDER", "anthropic")
    DEEP_THINK_MODEL: str = os.getenv("SS4_DEEP_MODEL", "claude-sonnet-4-20250514")
    QUICK_THINK_MODEL: str = os.getenv("SS4_QUICK_MODEL", "claude-sonnet-4-20250514")
    
    # API Keys (from environment)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    # Intel Sources
    PI_WORKSPACE_URL: str = os.getenv("PI_WORKSPACE_URL", "http://localhost:8080")
    TRUMP_V3_ENABLED: bool = os.getenv("SS4_TRUMP_V3", "true").lower() == "true"
    
    # Pipeline Settings
    MAX_DEBATE_ROUNDS: int = int(os.getenv("SS4_DEBATE_ROUNDS", "2"))
    ANALYST_TEMPERATURE: float = float(os.getenv("SS4_ANALYST_TEMP", "0.3"))
    DEBATE_TEMPERATURE: float = float(os.getenv("SS4_DEBATE_TEMP", "0.7"))
    
    # Risk Management
    MAX_POSITION_SIZE_PCT: float = 5.0  # Max 5% of portfolio per position
    MAX_SECTOR_EXPOSURE_PCT: float = 25.0  # Max 25% in any sector
    MIN_CONFIDENCE_THRESHOLD: float = 0.6  # Min 60% confidence to trade
    
    # Output
    OUTPUT_DIR: str = os.getenv("SS4_OUTPUT_DIR", "./output")
    SIGNALS_BLOG_PATH: str = os.getenv("SS4_SIGNALS_PATH", "")
    
    # SoulMate Integration
    SOULMATE_ENABLED: bool = os.getenv("SS4_SOULMATE", "true").lower() == "true"
    SOULMATE_COLLECTION: str = "stockscout4_trades"
    
    # Watchlist
    DEFAULT_WATCHLIST: list = [
        "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "SMCI", "ARM", "AVGO", "PLTR", "SNOW", "AI"
    ]


DEFAULT_CONFIG = Config()
