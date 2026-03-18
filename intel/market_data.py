"""
StockScout v4 — Market Data Fetcher

Pulls fundamentals, technicals, and macro data from various APIs.
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp


class MarketDataFetcher:
    """
    Fetches market data from multiple sources:
    - Alpha Vantage: Fundamentals, technicals
    - Yahoo Finance: Quick quotes (backup)
    - FRED: Macro indicators
    """
    
    def __init__(self, config):
        self.config = config
        self.av_key = config.ALPHA_VANTAGE_API_KEY
        self.base_urls = {
            "alpha_vantage": "https://www.alphavantage.co/query",
            "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart",
            "fred": "https://api.stlouisfed.org/fred/series/observations"
        }
    
    async def get_all_data(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch all data needed for analysis.
        
        Returns dict with keys:
        - fundamentals
        - technical
        - macro
        - quote (current price)
        """
        async with aiohttp.ClientSession() as session:
            fundamentals = await self._get_fundamentals(session, ticker)
            technical = await self._get_technical(session, ticker)
            macro = await self._get_macro(session)
            quote = await self._get_quote(session, ticker)
        
        return {
            "fundamentals": fundamentals,
            "technical": technical,
            "macro": macro,
            "quote": quote,
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    async def _get_fundamentals(
        self, 
        session: aiohttp.ClientSession, 
        ticker: str
    ) -> Dict[str, Any]:
        """Fetch fundamental data from Alpha Vantage."""
        if not self.av_key:
            return {"error": "No Alpha Vantage API key configured"}
        
        try:
            # Company overview
            overview_url = f"{self.base_urls['alpha_vantage']}?function=OVERVIEW&symbol={ticker}&apikey={self.av_key}"
            async with session.get(overview_url) as resp:
                overview = await resp.json()
            
            # Income statement (last 4 quarters)
            income_url = f"{self.base_urls['alpha_vantage']}?function=INCOME_STATEMENT&symbol={ticker}&apikey={self.av_key}"
            async with session.get(income_url) as resp:
                income = await resp.json()
            
            return {
                "overview": {
                    "market_cap": overview.get("MarketCapitalization"),
                    "pe_ratio": overview.get("PERatio"),
                    "ps_ratio": overview.get("PriceToSalesRatioTTM"),
                    "pb_ratio": overview.get("PriceToBookRatio"),
                    "ev_ebitda": overview.get("EVToEBITDA"),
                    "profit_margin": overview.get("ProfitMargin"),
                    "operating_margin": overview.get("OperatingMarginTTM"),
                    "roe": overview.get("ReturnOnEquityTTM"),
                    "revenue_growth": overview.get("QuarterlyRevenueGrowthYOY"),
                    "eps_growth": overview.get("QuarterlyEarningsGrowthYOY"),
                    "dividend_yield": overview.get("DividendYield"),
                    "beta": overview.get("Beta"),
                    "52_week_high": overview.get("52WeekHigh"),
                    "52_week_low": overview.get("52WeekLow"),
                    "analyst_target": overview.get("AnalystTargetPrice"),
                    "sector": overview.get("Sector"),
                    "industry": overview.get("Industry")
                },
                "recent_earnings": income.get("quarterlyReports", [])[:4]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_technical(
        self,
        session: aiohttp.ClientSession,
        ticker: str
    ) -> Dict[str, Any]:
        """Fetch technical indicators."""
        if not self.av_key:
            return {"error": "No Alpha Vantage API key configured"}
        
        try:
            # Daily prices
            daily_url = f"{self.base_urls['alpha_vantage']}?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=compact&apikey={self.av_key}"
            async with session.get(daily_url) as resp:
                daily = await resp.json()
            
            # RSI
            rsi_url = f"{self.base_urls['alpha_vantage']}?function=RSI&symbol={ticker}&interval=daily&time_period=14&series_type=close&apikey={self.av_key}"
            async with session.get(rsi_url) as resp:
                rsi_data = await resp.json()
            
            # MACD
            macd_url = f"{self.base_urls['alpha_vantage']}?function=MACD&symbol={ticker}&interval=daily&series_type=close&apikey={self.av_key}"
            async with session.get(macd_url) as resp:
                macd_data = await resp.json()
            
            # Parse latest values
            time_series = daily.get("Time Series (Daily)", {})
            dates = sorted(time_series.keys(), reverse=True)[:20]
            
            prices = []
            for date in dates:
                prices.append({
                    "date": date,
                    "open": float(time_series[date]["1. open"]),
                    "high": float(time_series[date]["2. high"]),
                    "low": float(time_series[date]["3. low"]),
                    "close": float(time_series[date]["4. close"]),
                    "volume": int(time_series[date]["5. volume"])
                })
            
            # Get latest RSI
            rsi_series = rsi_data.get("Technical Analysis: RSI", {})
            latest_rsi = None
            if rsi_series:
                latest_date = sorted(rsi_series.keys(), reverse=True)[0]
                latest_rsi = float(rsi_series[latest_date]["RSI"])
            
            # Get latest MACD
            macd_series = macd_data.get("Technical Analysis: MACD", {})
            latest_macd = None
            if macd_series:
                latest_date = sorted(macd_series.keys(), reverse=True)[0]
                latest_macd = {
                    "macd": float(macd_series[latest_date]["MACD"]),
                    "signal": float(macd_series[latest_date]["MACD_Signal"]),
                    "histogram": float(macd_series[latest_date]["MACD_Hist"])
                }
            
            return {
                "prices": prices,
                "rsi": latest_rsi,
                "macd": latest_macd,
                "sma_20": self._calculate_sma(prices, 20),
                "sma_50": self._calculate_sma(prices, 50) if len(prices) >= 50 else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_macro(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Fetch macro indicators."""
        # Simplified - in production would hit FRED API
        return {
            "fed_rate": 5.25,  # Would fetch from FRED
            "cpi_yoy": 3.2,
            "unemployment": 4.1,
            "vix": 15.5,
            "ten_year_yield": 4.35,
            "market_regime": "risk-on",  # Would calculate from multiple indicators
            "note": "Macro data placeholder - integrate FRED API for production"
        }
    
    async def _get_quote(
        self,
        session: aiohttp.ClientSession,
        ticker: str
    ) -> Dict[str, Any]:
        """Get current quote."""
        if not self.av_key:
            return {"error": "No API key"}
        
        try:
            url = f"{self.base_urls['alpha_vantage']}?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.av_key}"
            async with session.get(url) as resp:
                data = await resp.json()
            
            quote = data.get("Global Quote", {})
            return {
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_pct": quote.get("10. change percent", "0%"),
                "volume": int(quote.get("06. volume", 0)),
                "previous_close": float(quote.get("08. previous close", 0))
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_sma(self, prices: list, period: int) -> Optional[float]:
        """Calculate simple moving average."""
        if len(prices) < period:
            return None
        closes = [p["close"] for p in prices[:period]]
        return sum(closes) / period
