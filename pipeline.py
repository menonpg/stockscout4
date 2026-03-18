"""
StockScout v4 — Main Pipeline Orchestrator

Coordinates the full analysis flow:
Intel → Analysts → Debate → Decision → Output
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict

try:
    from .config import Config, DEFAULT_CONFIG
    from .agents.analysts import AnalystTeam
    from .agents.researchers import DebateEngine
    from .agents.traders import TradingDesk, FinalDecision
    from .intel.market_data import MarketDataFetcher
    from .intel.pi_scanner import PiScanner
    from .intel.trump_v3 import TrumpSignals
    from .utils.llm_client import LLMClient
    from .utils.soulmate import SoulMateMemory
except ImportError:
    from config import Config, DEFAULT_CONFIG
    from agents.analysts import AnalystTeam
    from agents.researchers import DebateEngine
    from agents.traders import TradingDesk, FinalDecision
    from intel.market_data import MarketDataFetcher
    from intel.pi_scanner import PiScanner
    from intel.trump_v3 import TrumpSignals
    from utils.llm_client import LLMClient
    from utils.soulmate import SoulMateMemory


class StockScoutPipeline:
    """
    Main orchestrator for StockScout v4 analysis.
    
    Flow:
    1. Gather intel (market data, Pi OSINT, Trump signals)
    2. Run analyst team (4 specialized analysts)
    3. Run debate (bull vs bear)
    4. Get trade decision (trader → risk → PM)
    5. Output results and store in SoulMate
    """
    
    def __init__(self, config: Config = None):
        self.config = config or DEFAULT_CONFIG
        
        # Initialize components
        self.llm = LLMClient(self.config)
        self.market_data = MarketDataFetcher(self.config)
        self.pi_scanner = PiScanner(self.config)
        self.trump_signals = TrumpSignals(self.config)
        
        # Initialize agent teams
        self.analysts = AnalystTeam(self.llm, self.config)
        self.debate = DebateEngine(self.llm, self.config)
        self.trading_desk = TradingDesk(self.llm, self.config)
        
        # Memory
        if self.config.SOULMATE_ENABLED:
            self.memory = SoulMateMemory(self.config)
        else:
            self.memory = None
    
    async def analyze(
        self,
        ticker: str,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run full analysis pipeline for a single ticker.
        
        Args:
            ticker: Stock symbol (e.g., "NVDA")
            portfolio_state: Current portfolio for position sizing
        
        Returns:
            Complete analysis with decision
        """
        start_time = datetime.utcnow()
        
        # Default portfolio state if not provided
        if portfolio_state is None:
            portfolio_state = {
                "cash": 100000,
                "positions": {},
                "sector_exposure": {},
                "strategy": {
                    "style": "growth",
                    "risk_tolerance": "moderate",
                    "time_horizon": "medium-term"
                }
            }
        
        # Step 1: Gather Intel
        print(f"[{ticker}] Gathering intel...")
        intel = await self._gather_intel(ticker)
        
        # Step 2: Run Analysts
        print(f"[{ticker}] Running analyst team...")
        analyst_reports = await self.analysts.analyze(ticker, intel)
        analyst_summary = self.analysts.summarize_reports(analyst_reports)
        
        # Step 3: Run Debate
        print(f"[{ticker}] Running bull/bear debate...")
        synthesis = await self.debate.debate(ticker, analyst_summary)
        
        # Step 4: Get Trade Decision
        print(f"[{ticker}] Processing through trading desk...")
        synthesis_dict = {
            "ticker": synthesis.ticker,
            "net_score": synthesis.net_score,
            "conviction": synthesis.conviction,
            "recommended_action": synthesis.recommended_action,
            "bull_strength": synthesis.bull_strength,
            "bear_strength": synthesis.bear_strength,
            "key_agreements": synthesis.key_agreements,
            "key_disagreements": synthesis.key_disagreements,
            "reasoning": synthesis.reasoning
        }
        decision = await self.trading_desk.process_trade(
            ticker=ticker,
            synthesis=synthesis_dict,
            portfolio_state=portfolio_state
        )
        
        # Build result
        result = {
            "ticker": ticker,
            "timestamp": start_time.isoformat(),
            "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
            "intel_summary": self._summarize_intel(intel),
            "analyst_scores": {
                name: {"score": r.score, "confidence": r.confidence}
                for name, r in analyst_reports.items()
            },
            "debate_synthesis": synthesis_dict,
            "final_decision": {
                "decision": decision.decision.value,
                "size_pct": decision.final_size_pct,
                "entry": decision.entry_type,
                "stop_loss": decision.stop_loss,
                "targets": decision.targets,
                "reject_reason": decision.reject_reason,
                "defer_until": decision.defer_until,
                "pm_notes": decision.pm_notes
            }
        }
        
        # Store in SoulMate
        if self.memory:
            await self.memory.store_analysis(result)
        
        return result
    
    async def morning_brief(
        self,
        watchlist: Optional[List[str]] = None,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate morning market brief for watchlist.
        
        Args:
            watchlist: List of tickers to analyze
            portfolio_state: Current portfolio
        
        Returns:
            Combined brief with all analyses
        """
        if watchlist is None:
            watchlist = self.config.DEFAULT_WATCHLIST
        
        print(f"Running morning brief for {len(watchlist)} tickers...")
        
        results = []
        for ticker in watchlist:
            try:
                result = await self.analyze(ticker, portfolio_state)
                results.append(result)
            except Exception as e:
                results.append({
                    "ticker": ticker,
                    "error": str(e)
                })
        
        # Sort by conviction/score
        actionable = [
            r for r in results 
            if "final_decision" in r and r["final_decision"]["decision"] != "REJECT"
        ]
        actionable.sort(
            key=lambda x: x.get("debate_synthesis", {}).get("net_score", 5),
            reverse=True
        )
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "watchlist_size": len(watchlist),
            "analyses": results,
            "top_opportunities": actionable[:5],
            "summary": self._generate_brief_summary(results)
        }
    
    async def _gather_intel(self, ticker: str) -> Dict[str, Any]:
        """Gather all intel for a ticker."""
        # Run data fetches in parallel
        market_task = self.market_data.get_all_data(ticker)
        pi_task = self.pi_scanner.get_all_intel(ticker)
        trump_task = self.trump_signals.get_signals(ticker)
        
        market, pi_intel, trump = await asyncio.gather(
            market_task, pi_task, trump_task
        )
        
        return {
            "fundamentals": market.get("fundamentals", {}),
            "technical": market.get("technical", {}),
            "macro": market.get("macro", {}),
            "quote": market.get("quote", {}),
            "sentiment": pi_intel.get("sentiment", {}),
            "social_mentions": pi_intel.get("mentions", {}),
            "options_flow": pi_intel.get("options_flow", {}),
            "trump_signals": trump
        }
    
    def _summarize_intel(self, intel: Dict[str, Any]) -> Dict[str, Any]:
        """Create a compact summary of intel for output."""
        quote = intel.get("quote", {})
        return {
            "current_price": quote.get("price"),
            "change_pct": quote.get("change_pct"),
            "sentiment": intel.get("sentiment", {}).get("overall_sentiment"),
            "trump_relevance": intel.get("trump_signals", {}).get("relevance_score", 0)
        }
    
    def _generate_brief_summary(self, results: List[Dict]) -> str:
        """Generate text summary for morning brief."""
        bullish = [r["ticker"] for r in results 
                   if r.get("debate_synthesis", {}).get("net_score", 5) >= 7]
        bearish = [r["ticker"] for r in results 
                   if r.get("debate_synthesis", {}).get("net_score", 5) <= 3]
        
        lines = [
            f"Analyzed {len(results)} tickers.",
            f"Bullish signals (score >= 7): {', '.join(bullish) if bullish else 'None'}",
            f"Bearish signals (score <= 3): {', '.join(bearish) if bearish else 'None'}"
        ]
        
        return " ".join(lines)
