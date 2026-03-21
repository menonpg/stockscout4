"""
StockScout v4 — Market Data Fetcher

Real data from:
- yfinance: quotes, fundamentals, technicals, news (no API key)
- FRED: macro indicators — real VIX, 10Y yield, unemployment, Fed rate
- ThinkCreate Intel: geopolitical signals, oil, conflict score
- StockScout v2: existing VST scores from Pi's scorer
"""

import asyncio
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# yfinance — sync calls wrapped in asyncio.to_thread
import yfinance as yf
import numpy as np


# URLs — not secrets, fine as constants
INTEL_API_URL = "https://intel-api.thinkcreateai.com/api/live-data/slow"
SS2_BASE_URL  = "https://stockscout.thinkcreateai.com/stockscout2/data"


class MarketDataFetcher:
    """
    Fetches real market data for StockScout v4 analysis.

    Primary sources (no API key needed):
    - yfinance: quotes, fundamentals, 3-month price history, news
    - FRED: VIX, 10Y yield, unemployment, CPI, Fed rate
    - ThinkCreate Intel: live geopolitical + oil + defense signals
    - StockScout v2: Pi's scored data (VST, RS, RT, signal)
    """

    def __init__(self, config):
        self.config = config
        self.fred_key = getattr(config, "FRED_API_KEY", None)
        if not self.fred_key:
            raise ValueError("FRED_API_KEY env var is required — set it in Railway")

    async def get_all_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch all data in parallel."""
        (quote, fundamentals, technical, news), macro, intel, ss2 = await asyncio.gather(
            self._get_yfinance_data(ticker),
            self._get_macro(),
            self._get_intel(ticker),
            self._get_ss2_score(ticker),
        )
        return {
            "fundamentals": fundamentals,
            "technical":    technical,
            "macro":        macro,
            "quote":        quote,
            "news":         news,
            "intel":        intel,
            "ss2_score":    ss2,
            "fetched_at":   datetime.utcnow().isoformat(),
        }

    # ── yfinance (runs in thread pool — sync lib) ──────────────────────────────

    async def _get_yfinance_data(self, ticker: str):
        """Returns (quote, fundamentals, technical, news) all from yfinance."""
        return await asyncio.to_thread(self._fetch_yfinance_sync, ticker)

    def _fetch_yfinance_sync(self, ticker: str):
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            hist = t.history(period="3mo")

            quote = self._parse_quote(info, hist)
            fundamentals = self._parse_fundamentals(info)
            technical = self._parse_technical(hist, info)
            news = self._parse_news(t)

            return quote, fundamentals, technical, news
        except Exception as e:
            empty = {"error": str(e), "source": "yfinance"}
            return empty, empty, empty, []

    def _parse_quote(self, info: dict, hist) -> Dict[str, Any]:
        price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
        prev  = info.get("regularMarketPreviousClose") or info.get("previousClose", price)
        chg   = price - prev
        chg_p = (chg / prev * 100) if prev else 0
        return {
            "price":          round(float(price), 2),
            "change":         round(float(chg), 2),
            "change_pct":     f"{chg_p:+.2f}%",
            "volume":         info.get("regularMarketVolume", 0),
            "previous_close": round(float(prev), 2),
            "market_cap":     info.get("marketCap"),
            "day_high":       info.get("dayHigh"),
            "day_low":        info.get("dayLow"),
        }

    def _parse_fundamentals(self, info: dict) -> Dict[str, Any]:
        return {
            "overview": {
                "market_cap":       info.get("marketCap"),
                "pe_ratio":         info.get("trailingPE") or info.get("forwardPE"),
                "ps_ratio":         info.get("priceToSalesTrailing12Months"),
                "pb_ratio":         info.get("priceToBook"),
                "ev_ebitda":        info.get("enterpriseToEbitda"),
                "profit_margin":    info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "roe":              info.get("returnOnEquity"),
                "revenue_growth":   info.get("revenueGrowth"),
                "eps_growth":       info.get("earningsGrowth"),
                "dividend_yield":   info.get("dividendYield"),
                "beta":             info.get("beta"),
                "52_week_high":     info.get("fiftyTwoWeekHigh"),
                "52_week_low":      info.get("fiftyTwoWeekLow"),
                "analyst_target":   info.get("targetMeanPrice"),
                "recommendation":   info.get("recommendationKey"),
                "num_analyst_opinions": info.get("numberOfAnalystOpinions"),
                "sector":           info.get("sector"),
                "industry":         info.get("industry"),
                "short_name":       info.get("shortName"),
                "description":      (info.get("longBusinessSummary") or "")[:500],
            }
        }

    def _parse_technical(self, hist, info: dict) -> Dict[str, Any]:
        if hist is None or hist.empty:
            return {"error": "No price history available"}

        closes = hist["Close"].values.tolist()
        volumes = hist["Volume"].values.tolist()
        dates = [str(d)[:10] for d in hist.index.tolist()]

        prices = [
            {
                "date":   dates[i],
                "close":  round(float(closes[i]), 2),
                "volume": int(volumes[i]),
                "high":   round(float(hist["High"].values[i]), 2),
                "low":    round(float(hist["Low"].values[i]), 2),
            }
            for i in range(len(closes))
        ]
        prices.reverse()  # most recent first

        rsi = self._calc_rsi(closes)
        macd, signal, hist_vals = self._calc_macd(closes)
        sma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else None
        sma50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else None

        # Volume momentum: today vs 20-day avg
        vol_today = volumes[-1] if volumes else 0
        vol_avg   = np.mean(volumes[-21:-1]) if len(volumes) > 20 else vol_today
        vol_ratio = round(vol_today / vol_avg, 2) if vol_avg > 0 else None

        # 52-week position
        w52h = info.get("fiftyTwoWeekHigh")
        w52l = info.get("fiftyTwoWeekLow")
        current = closes[-1] if closes else None

        return {
            "prices":       prices[:20],
            "rsi":          round(rsi, 1) if rsi else None,
            "macd":         {"macd": round(macd, 3), "signal": round(signal, 3), "histogram": round(hist_vals, 3)} if macd else None,
            "sma_20":       round(sma20, 2) if sma20 else None,
            "sma_50":       round(sma50, 2) if sma50 else None,
            "vol_ratio":    vol_ratio,
            "above_sma20":  (current > sma20) if (current and sma20) else None,
            "above_sma50":  (current > sma50) if (current and sma50) else None,
            "pct_from_52h": round((current / w52h - 1) * 100, 1) if (current and w52h) else None,
            "pct_from_52l": round((current / w52l - 1) * 100, 1) if (current and w52l) else None,
        }

    def _parse_news(self, ticker_obj) -> List[Dict]:
        try:
            news = ticker_obj.news or []
            return [
                {
                    "title":     n.get("title", ""),
                    "publisher": n.get("publisher", ""),
                    "link":      n.get("link", ""),
                    "published": datetime.utcfromtimestamp(n.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M UTC"),
                }
                for n in news[:8]
            ]
        except Exception:
            return []

    # ── RSI + MACD helpers ─────────────────────────────────────────────────────

    def _calc_rsi(self, closes: list, period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains  = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        if not gains or not losses:
            return None
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calc_macd(self, closes: list):
        if len(closes) < 26:
            return None, None, None

        def ema(data, n):
            k = 2 / (n + 1)
            e = data[0]
            for v in data[1:]:
                e = v * k + e * (1 - k)
            return e

        ema12 = ema(closes[-26:], 12)
        ema26 = ema(closes[-26:], 26)
        macd = ema12 - ema26
        signal = ema([macd], 9)  # simplified — single point
        return macd, signal, macd - signal

    # ── FRED Macro (real data, no placeholders) ────────────────────────────────

    async def _get_macro(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._fetch_macro_sync)

    def _fetch_macro_sync(self) -> Dict[str, Any]:
        def fred(series_id: str, limit: int = 3) -> list:
            try:
                url = (
                    f"https://api.stlouisfed.org/fred/series/observations"
                    f"?series_id={series_id}&api_key={self.fred_key}"
                    f"&sort_order=desc&limit={limit}&file_type=json"
                )
                obs = requests.get(url, timeout=10).json().get("observations", [])
                return [float(o["value"]) for o in obs if o["value"] != "."]
            except Exception:
                return []

        y10    = fred("DGS10")
        unemp  = fred("UNRATE")
        cpi    = fred("CPIAUCSL", 2)
        fed    = fred("FEDFUNDS", 1)
        vix    = fred("VIXCLS", 1)

        ten_y    = y10[0]    if y10    else None
        unemp_v  = unemp[0]  if unemp  else None
        cpi_v    = cpi[0]    if cpi    else None
        fed_v    = fed[0]    if fed    else None
        vix_v    = vix[0]    if vix    else None

        # Regime determination
        risk_off = False
        if ten_y and ten_y > 4.5:
            risk_off = True
        if vix_v and vix_v > 25:
            risk_off = True
        if unemp_v and unemp_v > 4.5 and (len(unemp) >= 2 and unemp[0] > unemp[1]):
            risk_off = True

        return {
            "fed_rate":          fed_v,
            "ten_year_yield":    ten_y,
            "ten_year_rising":   (len(y10) >= 2 and y10[0] > y10[1]) if y10 else None,
            "cpi":               cpi_v,
            "unemployment":      unemp_v,
            "unemployment_rising": (len(unemp) >= 2 and unemp[0] > unemp[1]) if unemp else None,
            "vix":               vix_v,
            "market_regime":     "risk-off" if risk_off else "risk-on",
            "risk_off":          risk_off,
            "note":              "Live FRED data — DGS10, UNRATE, CPIAUCSL, FEDFUNDS, VIXCLS",
        }

    # ── ThinkCreate Intel (geopolitical + oil + defense) ──────────────────────

    async def _get_intel(self, ticker: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._fetch_intel_sync, ticker)

    def _fetch_intel_sync(self, ticker: str) -> Dict[str, Any]:
        """
        Pulls full ThinkCreate Intel data from both /slow and /fast endpoints.
        
        /slow: news, defense stock prices, oil, GDELT, frontlines, earthquakes, space weather
        /fast: military flights, tracked aircraft, GPS jamming, ship movements
        """
        try:
            # Primary: /slow — rich intelligence data
            slow = requests.get(INTEL_API_URL, timeout=20, verify=False).json()

            # Secondary: /fast — real-time tracking counts (lightweight)
            try:
                fast = requests.get(
                    INTEL_API_URL.replace("/slow", "/fast"), timeout=10, verify=False
                ).json()
            except Exception:
                fast = {}

            # ── Oil ──────────────────────────────────────────────────────────
            wti   = (slow.get("oil") or {}).get("WTI Crude", {})
            brent = (slow.get("oil") or {}).get("Brent Crude", {})
            oil_price  = float(wti.get("price", 0) or 0)
            oil_change = float(wti.get("change_percent", 0) or 0)
            oil_spike  = oil_price > 85 and oil_change > 3.0

            # ── Defense stocks (live prices from Intel) ───────────────────────
            defense_stocks = {}
            for sym, data in (slow.get("stocks") or {}).items():
                defense_stocks[sym] = {
                    "price":          data.get("price"),
                    "change_percent": data.get("change_percent"),
                    "up":             data.get("up"),
                }
            # Average defense sector move
            defense_changes = [v["change_percent"] for v in defense_stocks.values()
                                if v["change_percent"] is not None]
            defense_avg_move = round(sum(defense_changes) / len(defense_changes), 2) if defense_changes else None
            defense_sector_down = defense_avg_move is not None and defense_avg_move < -1.5

            # ── News + conflict analysis ──────────────────────────────────────
            news = slow.get("news") or []
            conflict_kw = ["war","strike","attack","conflict","iran","missile","military",
                           "troops","invasion","sanction","nato","nuclear","hormuz",
                           "tariff","escalat","threat","terror"]
            
            top_headlines = []
            conflict_score = 0
            for item in news[:15]:
                title   = (item.get("title") or "").lower()
                summary = (item.get("summary") or "").lower()
                text    = title + " " + summary
                matched = [kw for kw in conflict_kw if kw in text]
                if matched:
                    conflict_score += 1
                top_headlines.append({
                    "title":    item.get("title", ""),
                    "source":   item.get("source", ""),
                    "conflict": matched,
                })

            defense_boost = conflict_score >= 3

            # ── GDELT global incident density ─────────────────────────────────
            gdelt_count = len(slow.get("gdelt") or [])
            geo_stress  = gdelt_count > 800

            # ── Space weather ─────────────────────────────────────────────────
            sw = slow.get("space_weather") or {}
            kp_index   = sw.get("kp_index", 0)
            solar_storm = kp_index >= 5

            # ── Internet outages ──────────────────────────────────────────────
            outages = slow.get("internet_outages") or []
            critical_outages = sum(1 for o in outages if (o.get("level") or "") == "critical")

            # ── Real-time tracking (from /fast) ───────────────────────────────
            military_flights   = len(fast.get("military_flights") or [])
            tracked_aircraft   = len(fast.get("tracked_flights") or [])
            gps_jamming_events = len(fast.get("gps_jamming") or [])
            total_ships        = len(fast.get("ships") or [])

            # ── Frontline status (Ukraine war activity) ───────────────────────
            frontlines = slow.get("frontlines") or {}
            frontline_features = len((frontlines.get("features") or []))
            frontline_active = frontline_features > 0

            # ── Ticker relevance ──────────────────────────────────────────────
            defense_tickers = {"RTX","LMT","NOC","GD","BA","HII","TDG","LDOS","SAIC","PLTR",
                                "KTOS","CACI","MANT","HEICO","HEI","TXT","KRMN","VST","CEG"}
            is_defense = ticker.upper() in defense_tickers

            # ── Analyst-readable summary ──────────────────────────────────────
            regime_summary = []
            if oil_spike:
                regime_summary.append(f"OIL SPIKE: WTI ${oil_price} (+{oil_change}%)")
            if defense_sector_down:
                regime_summary.append(f"DEFENSE SECTOR WEAK: avg {defense_avg_move}%")
            elif defense_boost:
                regime_summary.append(f"DEFENSE TAILWIND: {conflict_score} conflict headlines")
            if geo_stress:
                regime_summary.append(f"ELEVATED GEO STRESS: {gdelt_count} GDELT events")
            if solar_storm:
                regime_summary.append(f"SOLAR STORM: Kp={kp_index}")
            if critical_outages >= 5:
                regime_summary.append(f"INTERNET DISRUPTIONS: {critical_outages} critical outages")
            if military_flights > 60:
                regime_summary.append(f"ELEVATED MILITARY FLIGHTS: {military_flights}")

            return {
                # Oil
                "oil": {
                    "wti_price":    oil_price,
                    "wti_change":   oil_change,
                    "brent_price":  brent.get("price"),
                    "brent_change": brent.get("change_percent"),
                    "oil_spike":    oil_spike,
                },
                # Defense sector (live prices from ThinkCreate Intel)
                "defense_stocks":       defense_stocks,
                "defense_avg_move":     defense_avg_move,
                "defense_sector_down":  defense_sector_down,
                "defense_boost":        defense_boost,
                # News
                "top_headlines":        top_headlines[:10],
                "conflict_score":       conflict_score,
                # Geo stress
                "gdelt_count":          gdelt_count,
                "geo_stress":           geo_stress,
                # Space + cyber
                "kp_index":             kp_index,
                "solar_storm":          solar_storm,
                "critical_outages":     critical_outages,
                # Real-time tracking
                "military_flights":     military_flights,
                "tracked_aircraft":     tracked_aircraft,
                "gps_jamming_events":   gps_jamming_events,
                "total_ships":          total_ships,
                # War
                "frontline_active":     frontline_active,
                # Ticker context
                "is_defense_stock":     is_defense,
                "relevance_score":      min(conflict_score / 10.0, 1.0),
                # One-line analyst summary
                "regime_flags":         regime_summary,
                "source":               "intel-api.thinkcreateai.com (/slow + /fast)",
            }
        except Exception as e:
            return {"error": str(e), "source": "intel-api unavailable"}

    # ── StockScout v2 — Pi's existing scored data ──────────────────────────────

    async def _get_ss2_score(self, ticker: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._fetch_ss2_sync, ticker)

    def _fetch_ss2_sync(self, ticker: str) -> Dict[str, Any]:
        universes = ["default", "tech", "energy", "finance", "healthcare"]
        ticker_up = ticker.upper()
        for universe in universes:
            try:
                url = f"{SS2_BASE_URL}/{universe}.json"
                r = requests.get(url, timeout=10)
                if r.status_code != 200:
                    continue
                data = r.json()
                for score in data.get("scores", []):
                    if score.get("symbol", "").upper() == ticker_up:
                        return {
                            "found":          True,
                            "universe":       universe,
                            "vst":            score.get("vst"),
                            "signal":         score.get("signal"),
                            "v1_signal":      score.get("v1_signal"),
                            "signal_changed": score.get("signal_changed"),
                            "signal_reason":  score.get("signal_reason"),
                            "rs":             score.get("rs"),
                            "rt":             score.get("rt"),
                            "rv":             score.get("rv"),
                            "macro":          score.get("macro"),
                            "vol_ratio":      score.get("vol_ratio"),
                            "top_sectors":    data.get("top_sectors", {}),
                            "updated":        data.get("updated"),
                        }
            except Exception:
                continue
        return {"found": False, "note": f"{ticker_up} not in any StockScout v2 universe"}
