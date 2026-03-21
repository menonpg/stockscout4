"""
StockScout v4 — Trump / Policy Signal Analyzer

Analyzes recent news for {ticker} to detect:
- Trump/presidential mentions
- Tariff/trade policy signals
- Sector-specific political catalysts

Uses Yahoo Finance news (via yfinance) + keyword analysis.
No fake API endpoints. No hardcoded data.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime


# Keywords that indicate strong political/policy signal
TRUMP_KEYWORDS = [
    "trump", "tariff", "trade war", "executive order", "white house",
    "president", "administration", "commerce department", "sec investigation",
    "doge", "doge cut", "federal contract", "defense contract", "export ban",
    "chip ban", "china tariff", "sanctions", "deregulation", "energy policy",
]

SECTOR_POLICY_MAP = {
    # Sectors that are highly politically sensitive
    "Technology":        ["chip ban", "export control", "huawei", "tiktok", "antitrust"],
    "Energy":            ["pipeline", "lng", "energy dominance", "drill", "epa", "paris accord"],
    "Defense":           ["defense budget", "nato", "ukraine", "military", "lockheed", "raytheon"],
    "Financial Services":["deregulation", "cfpb", "dodd-frank", "fed appointment"],
    "Healthcare":        ["drug price", "medicare", "obamacare", "fda", "insulin"],
    "Consumer Cyclical": ["tariff", "china goods", "trade deal", "usmca"],
    "Industrials":       ["infrastructure", "steel tariff", "buy american"],
}


class TrumpSignals:
    """
    Analyzes Trump/policy signals for a ticker using real news.
    
    Sources:
    - yfinance news (ticker-specific headlines)
    - Keyword pattern matching (no LLM call — fast, cheap)
    """

    def __init__(self, config):
        self.config = config
        self.enabled = config.TRUMP_V3_ENABLED

    async def get_signals(self, ticker: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "note": "Trump signals disabled"}

        return await asyncio.to_thread(self._analyze_sync, ticker)

    def _analyze_sync(self, ticker: str) -> Dict[str, Any]:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info  = t.info or {}
            news  = t.news  or []
            sector = info.get("sector", "")

            # Analyze headlines for Trump/policy keywords
            mentions = []
            for item in news[:20]:
                title   = (item.get("title", "") or "").lower()
                summary = (item.get("summary", "") or "").lower()
                text    = title + " " + summary

                matched_kw = [kw for kw in TRUMP_KEYWORDS if kw in text]
                sector_kw  = [kw for kw in SECTOR_POLICY_MAP.get(sector, []) if kw in text]

                if matched_kw or sector_kw:
                    mentions.append({
                        "headline":     item.get("title", ""),
                        "publisher":    item.get("publisher", ""),
                        "trump_kw":     matched_kw,
                        "sector_kw":    sector_kw,
                    })

            relevance_score = min(len(mentions) / 5.0, 1.0)

            # Determine directional signal
            positive_kw = ["deregulation", "defense contract", "federal contract",
                           "infrastructure", "buy american", "energy dominance"]
            negative_kw = ["tariff", "ban", "sanction", "antitrust", "investigation",
                           "chip ban", "export ban"]

            all_matched = " ".join(
                " ".join(m["trump_kw"] + m["sector_kw"]) for m in mentions
            )
            positive_hits = sum(1 for kw in positive_kw if kw in all_matched)
            negative_hits = sum(1 for kw in negative_kw if kw in all_matched)

            if positive_hits > negative_hits:
                overall_signal = "bullish"
            elif negative_hits > positive_hits:
                overall_signal = "bearish"
            else:
                overall_signal = "neutral"

            return {
                "ticker":          ticker,
                "enabled":         True,
                "relevance_score": round(relevance_score, 2),
                "mention_count":   len(mentions),
                "overall_signal":  overall_signal,
                "direct_mentions": mentions[:5],
                "sector":          sector,
                "sector_sensitive": sector in SECTOR_POLICY_MAP,
                "note":            f"Analyzed {len(news)} recent headlines via yfinance",
                "fetched_at":      datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "ticker":          ticker,
                "enabled":         True,
                "relevance_score": 0.0,
                "overall_signal":  "neutral",
                "error":           str(e),
                "note":            "Signal analysis failed — neutral assumed",
            }
