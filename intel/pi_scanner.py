"""
StockScout v4 — Pi Scanner Integration

Pulls OSINT data from Pi's social media scanning.
"""

import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime


class PiScanner:
    """
    Interface to Pi's OSINT scanning capabilities.
    
    Pi runs on Android and scans:
    - Twitter/X mentions and sentiment
    - LinkedIn posts and engagement
    - Reddit discussions
    - News headlines
    
    This class fetches Pi's processed intel.
    """
    
    def __init__(self, config):
        self.config = config
        self.pi_url = config.PI_WORKSPACE_URL
    
    async def get_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch social sentiment data for a ticker.
        
        Returns:
            Dict with sentiment scores and key mentions
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Try to fetch from Pi's API
                url = f"{self.pi_url}/api/sentiment/{ticker}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return self._fallback_sentiment(ticker)
        except Exception as e:
            # If Pi is not available, return placeholder
            return self._fallback_sentiment(ticker, str(e))
    
    async def get_social_mentions(self, ticker: str) -> Dict[str, Any]:
        """
        Get recent social media mentions.
        
        Returns:
            Dict with mentions from various platforms
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.pi_url}/api/mentions/{ticker}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return self._fallback_mentions(ticker)
        except Exception:
            return self._fallback_mentions(ticker)
    
    async def get_options_flow(self, ticker: str) -> Dict[str, Any]:
        """
        Get unusual options activity signals.
        
        Returns:
            Dict with put/call ratio, unusual activity
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.pi_url}/api/options/{ticker}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return self._fallback_options(ticker)
        except Exception:
            return self._fallback_options(ticker)
    
    async def get_all_intel(self, ticker: str) -> Dict[str, Any]:
        """Fetch all available intel for a ticker."""
        sentiment = await self.get_sentiment(ticker)
        mentions = await self.get_social_mentions(ticker)
        options = await self.get_options_flow(ticker)
        
        return {
            "sentiment": sentiment,
            "mentions": mentions,
            "options_flow": options,
            "source": "pi_scanner",
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _fallback_sentiment(self, ticker: str, error: str = None) -> Dict[str, Any]:
        """Return placeholder when Pi is unavailable."""
        return {
            "ticker": ticker,
            "overall_sentiment": "neutral",
            "sentiment_score": 0.5,
            "twitter_sentiment": "neutral",
            "reddit_sentiment": "neutral",
            "mention_volume": "normal",
            "trending": False,
            "note": "Pi scanner unavailable - using neutral defaults",
            "error": error
        }
    
    def _fallback_mentions(self, ticker: str) -> Dict[str, Any]:
        """Return placeholder mentions."""
        return {
            "ticker": ticker,
            "twitter": {"count": 0, "top_tweets": []},
            "reddit": {"count": 0, "top_posts": []},
            "linkedin": {"count": 0, "top_posts": []},
            "note": "Pi scanner unavailable"
        }
    
    def _fallback_options(self, ticker: str) -> Dict[str, Any]:
        """Return placeholder options data."""
        return {
            "ticker": ticker,
            "put_call_ratio": 1.0,
            "unusual_activity": [],
            "max_pain": None,
            "note": "Pi scanner unavailable"
        }
