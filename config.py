"""
StockScout v4 Configuration — ALL values from env vars, nothing hardcoded.
"""

import os
from typing import Optional


class Config:
    # ── LLM Provider ─────────────────────────────────────────────────────────
    # Options: "azure_openai" | "anthropic" | "openai" | "ollama"
    LLM_PROVIDER: str       = os.getenv("SS4_LLM_PROVIDER", "azure_openai")
    DEEP_THINK_MODEL: str   = os.getenv("SS4_DEEP_MODEL",   "gpt-4o")
    QUICK_THINK_MODEL: str  = os.getenv("SS4_QUICK_MODEL",  "gpt-4o")

    # ── LLM API Keys ─────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY:    Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY:    Optional[str] = os.getenv("GEMINI_API_KEY")

    # ── Azure OpenAI (default provider) ──────────────────────────────────────
    # Accepts both AZURE_OPENAI_API_KEY and AZURE_OPENAI_KEY (Railway convention)
    AZURE_OPENAI_API_KEY:     Optional[str] = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_ENDPOINT:    Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION: str           = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    AZURE_OPENAI_DEPLOYMENT:  str           = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-chat")

    # ── Market Data API Keys ──────────────────────────────────────────────────
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    FINNHUB_API_KEY:       Optional[str] = os.getenv("FINNHUB_API_KEY")
    FRED_API_KEY:          Optional[str] = os.getenv("FRED_API_KEY")

    # ── Pipeline Settings ─────────────────────────────────────────────────────
    MAX_DEBATE_ROUNDS:    int   = int(os.getenv("SS4_DEBATE_ROUNDS",  "2"))
    ANALYST_TEMPERATURE:  float = float(os.getenv("SS4_ANALYST_TEMP", "0.3"))
    DEBATE_TEMPERATURE:   float = float(os.getenv("SS4_DEBATE_TEMP",  "0.7"))

    # ── Risk Management ───────────────────────────────────────────────────────
    MAX_POSITION_SIZE_PCT:    float = 5.0
    MAX_SECTOR_EXPOSURE_PCT:  float = 25.0
    MIN_CONFIDENCE_THRESHOLD: float = 0.6

    # ── Intel Sources ─────────────────────────────────────────────────────────
    PI_WORKSPACE_URL:  str  = os.getenv("PI_WORKSPACE_URL", "http://localhost:8080")
    TRUMP_V3_ENABLED:  bool = os.getenv("SS4_TRUMP_V3", "true").lower() == "true"

    # ── Output / Memory ───────────────────────────────────────────────────────
    OUTPUT_DIR:          str  = os.getenv("SS4_OUTPUT_DIR", "./output")
    SIGNALS_BLOG_PATH:   str  = os.getenv("SS4_SIGNALS_PATH", "")
    SOULMATE_ENABLED:    bool = os.getenv("SS4_SOULMATE", "false").lower() == "true"
    SOULMATE_COLLECTION: str  = "stockscout4_trades"

    # ── Default Watchlist ─────────────────────────────────────────────────────
    DEFAULT_WATCHLIST: list = [
        "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
        "AMD",  "SMCI", "ARM",  "AVGO",  "PLTR", "SNOW", "AI"
    ]


DEFAULT_CONFIG = Config()
