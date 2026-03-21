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
        
        # Build result — include full debate transcript and analyst details
        result = {
            "ticker": ticker,
            "timestamp": start_time.isoformat(),
            "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
            "intel_summary": self._summarize_intel(intel),
            # Full analyst details (score + key_points + reasoning)
            "analyst_scores": {
                name: {
                    "score": r.score,
                    "confidence": r.confidence,
                    "key_points": r.key_points,
                    "risks": r.risks,
                    "reasoning": r.reasoning
                }
                for name, r in analyst_reports.items()
            },
            # Debate synthesis + full round transcripts
            "debate_synthesis": {
                **synthesis_dict,
                "unresolved_questions": synthesis.unresolved_questions,
                "rounds": synthesis.rounds  # full bull/bear arguments per round
            },
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
    

    async def analyze_streaming(
        self,
        ticker: str,
        portfolio_state: Optional[Dict[str, Any]] = None
    ):
        """
        Async generator version of analyze().
        Yields SSE-style dicts at each stage so the UI can update in real-time.
        
        Yields dicts with keys: step, message, progress, [data]
        """
        start_time = datetime.utcnow()

        if portfolio_state is None:
            portfolio_state = {
                "cash": 100000,
                "positions": {},
                "sector_exposure": {},
                "strategy": {"style": "growth", "risk_tolerance": "moderate", "time_horizon": "medium-term"}
            }

        yield {"step": "intel", "message": f"Gathering live intel for {ticker}...", "progress": 5}

        intel = await self._gather_intel(ticker)
        intel_summary = self._summarize_intel(intel)

        yield {"step": "intel_done", "message": "Intel gathered", "progress": 15, "data": intel_summary}

        # Run analysts one by one so each result can stream to the UI
        analyst_names = ["fundamentals", "technical", "sentiment", "macro"]
        analyst_labels = {
            "fundamentals": "Fundamentals analyst",
            "technical":    "Technical analyst",
            "sentiment":    "Sentiment analyst",
            "macro":        "Macro analyst",
        }
        analyst_progress = [25, 38, 51, 64]
        analyst_reports = {}

        for i, name in enumerate(analyst_names):
            yield {
                "step": f"analyst_{name}",
                "message": f"Running {analyst_labels[name]}...",
                "progress": analyst_progress[i] - 5,
            }
            # Run a single analyst by temporarily filtering the analyst team
            single = await self.analysts.analyze_single(name, ticker, intel)
            analyst_reports[name] = single
            yield {
                "step": f"analyst_{name}_done",
                "message": f"{analyst_labels[name]} complete",
                "progress": analyst_progress[i],
                "data": {
                    "name":       name,
                    "score":      single.score,
                    "confidence": single.confidence,
                    "key_points": single.key_points,
                    "risks":      single.risks,
                    "reasoning":  single.reasoning,
                },
            }

        analyst_summary = self.analysts.summarize_reports(analyst_reports)

        # Debate — run as background task with keepalives every 4s
        # (Sonnet 4.5 debate can take 30-60s; SSE dies without keepalives)
        yield {"step": "debate", "message": "Bull vs Bear debate starting...", "progress": 68}

        debate_task = asyncio.create_task(self.debate.debate(ticker, analyst_summary))
        ping = 0
        while not debate_task.done():
            await asyncio.sleep(4)
            ping += 1
            yield {"step": "keepalive", "message": f"Debate in progress ({ping * 4}s)...", "progress": min(68 + ping, 85)}

        synthesis = debate_task.result()

        # Yield each debate round
        if synthesis.rounds:
            for i, rnd in enumerate(synthesis.rounds):
                round_dict = rnd if isinstance(rnd, dict) else (rnd.__dict__ if hasattr(rnd, "__dict__") else {})
                yield {
                    "step": f"debate_round_{i+1}",
                    "message": f"Debate round {i+1} complete",
                    "progress": 86 + i * 2,
                    "data": round_dict,
                }

        yield {"step": "decision", "message": "Trading desk processing decision...", "progress": 90}

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
        decision_task = asyncio.create_task(self.trading_desk.process_trade(
            ticker=ticker,
            synthesis=synthesis_dict,
            portfolio_state=portfolio_state
        ))
        ping2 = 0
        while not decision_task.done():
            await asyncio.sleep(4)
            ping2 += 1
            yield {"step": "keepalive", "message": f"Trading desk deliberating ({ping2 * 4}s)...", "progress": min(91 + ping2, 98)}
        decision = decision_task.result()

        result = {
            "ticker": ticker,
            "timestamp": start_time.isoformat(),
            "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
            "intel_summary": intel_summary,
            "analyst_scores": {
                name: {
                    "score":      r.score,
                    "confidence": r.confidence,
                    "key_points": r.key_points,
                    "risks":      r.risks,
                    "reasoning":  r.reasoning,
                }
                for name, r in analyst_reports.items()
            },
            "debate_synthesis": {
                **synthesis_dict,
                "unresolved_questions": synthesis.unresolved_questions,
                "rounds": synthesis.rounds,
            },
            "final_decision": {
                "decision":      decision.decision.value,
                "size_pct":      decision.final_size_pct,
                "entry":         decision.entry_type,
                "stop_loss":     decision.stop_loss,
                "targets":       decision.targets,
                "reject_reason": decision.reject_reason,
                "defer_until":   decision.defer_until,
                "pm_notes":      decision.pm_notes,
            }
        }

        if self.memory:
            await self.memory.store_analysis(result)

        yield {"step": "complete", "message": "Analysis complete!", "progress": 100, "result": result}

    async def morning_brief(
        self,
        watchlist: Optional[List[str]] = None,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate morning market brief for watchlist."""
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
        market_task = self.market_data.get_all_data(ticker)
        pi_task = self.pi_scanner.get_all_intel(ticker)
        trump_task = self.trump_signals.get_signals(ticker)
        
        market, pi_intel, trump = await asyncio.gather(
            market_task, pi_task, trump_task
        )
        
        return {
            "fundamentals":   (market or {}).get("fundamentals", {}),
            "technical":      (market or {}).get("technical", {}),
            "macro":          (market or {}).get("macro", {}),
            "quote":          (market or {}).get("quote", {}),
            "news":           (market or {}).get("news", []),
            "intel":          (market or {}).get("intel", {}),        # ThinkCreate Intel
            "ss2_score":      (market or {}).get("ss2_score", {}),    # StockScout v2 score
            "sentiment":      (pi_intel or {}).get("sentiment", {}),
            "social_mentions":(pi_intel or {}).get("mentions", {}),
            "options_flow":   (pi_intel or {}).get("options_flow", {}),
            "trump_signals":  trump or {}
        }
    
    def _summarize_intel(self, intel: Dict[str, Any]) -> Dict[str, Any]:
        """Create a compact summary of intel for output."""
        quote = intel.get("quote") or {}
        return {
            "current_price": quote.get("price"),
            "change_pct": quote.get("change_pct"),
            "sentiment": (intel.get("sentiment") or {}).get("overall_sentiment"),
            "trump_relevance": (intel.get("trump_signals") or {}).get("relevance_score", 0)
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
