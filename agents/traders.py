"""
StockScout v4 — Trading Desk

Trader Agent → Risk Manager → Portfolio Manager decision chain.
"""

import json
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from .prompts import TRADER_AGENT, RISK_MANAGER, PORTFOLIO_MANAGER
except ImportError:
    from prompts import TRADER_AGENT, RISK_MANAGER, PORTFOLIO_MANAGER


class TradeAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    SHORT = "SHORT"
    COVER = "COVER"


class FinalDecision(Enum):
    EXECUTE = "EXECUTE"
    REJECT = "REJECT"
    DEFER = "DEFER"


@dataclass
class TradeProposal:
    """Proposal from the Trader Agent."""
    ticker: str
    action: TradeAction
    entry_price: float | str  # float or "market"
    position_size_pct: float
    stop_loss: float
    take_profit: list
    timeframe: str
    rationale: str
    confidence: float


@dataclass
class RiskAssessment:
    """Assessment from the Risk Manager."""
    ticker: str
    position_size_decision: str  # approved/reduce/reject
    concentration_status: str  # ok/warning/reject
    correlation_level: str  # low/medium/high
    max_loss_dollars: float
    timing_concerns: list
    decision: str  # APPROVE/MODIFY/REJECT
    modifications: Optional[str]
    reasoning: str


@dataclass 
class FinalTradeDecision:
    """Final decision from Portfolio Manager."""
    ticker: str
    decision: FinalDecision
    # If EXECUTE
    final_size_pct: Optional[float]
    entry_type: Optional[str]  # "market" or "limit at $X"
    stop_loss: Optional[float]
    targets: Optional[list]
    # If REJECT
    reject_reason: Optional[str]
    # If DEFER
    defer_until: Optional[str]
    # Notes
    pm_notes: str


class TradingDesk:
    """
    Three-stage decision process:
    1. Trader Agent: Formulates trade proposal
    2. Risk Manager: Evaluates risk, may modify
    3. Portfolio Manager: Final approve/reject
    """
    
    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
    
    async def process_trade(
        self,
        ticker: str,
        synthesis: Dict[str, Any],
        portfolio_state: Dict[str, Any]
    ) -> FinalTradeDecision:
        """
        Run the full trading desk decision process.
        """
        # Step 1: Trader formulates proposal
        proposal = await self._trader_propose(ticker, synthesis, portfolio_state)
        
        # If HOLD, skip risk check
        if proposal.action == TradeAction.HOLD:
            return FinalTradeDecision(
                ticker=ticker,
                decision=FinalDecision.REJECT,
                final_size_pct=None,
                entry_type=None,
                stop_loss=None,
                targets=None,
                reject_reason="Trader recommended HOLD - no action needed",
                defer_until=None,
                pm_notes="Analysis complete, maintaining current position"
            )
        
        # Step 2: Risk Manager evaluates
        risk_assessment = await self._risk_evaluate(proposal, portfolio_state)
        
        # If Risk rejects outright
        if risk_assessment.decision == "REJECT":
            return FinalTradeDecision(
                ticker=ticker,
                decision=FinalDecision.REJECT,
                final_size_pct=None,
                entry_type=None,
                stop_loss=None,
                targets=None,
                reject_reason=f"Risk Manager: {risk_assessment.reasoning}",
                defer_until=None,
                pm_notes=f"Risk concerns: {risk_assessment.timing_concerns}"
            )
        
        # Step 3: Portfolio Manager final decision
        final_decision = await self._pm_decide(proposal, risk_assessment, portfolio_state)
        
        return final_decision
    
    async def _trader_propose(
        self,
        ticker: str,
        synthesis: Dict[str, Any],
        portfolio_state: Dict[str, Any]
    ) -> TradeProposal:
        """Trader Agent creates trade proposal."""
        
        prompt = TRADER_AGENT.format(
            ticker=ticker,
            synthesis=json.dumps(synthesis, indent=2),
            portfolio_context=json.dumps(portfolio_state, indent=2)
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            temperature=0.3,
            model=self.config.DEEP_THINK_MODEL
        )
        
        data = self._extract_json(response)
        
        return TradeProposal(
            ticker=ticker,
            action=TradeAction(data.get("action", "HOLD")),
            entry_price=data.get("entry_price", "market"),
            position_size_pct=data.get("position_size_pct", 0),
            stop_loss=data.get("stop_loss", 0),
            take_profit=data.get("take_profit", []),
            timeframe=data.get("timeframe", ""),
            rationale=data.get("rationale", ""),
            confidence=data.get("confidence", 0.5)
        )
    
    async def _risk_evaluate(
        self,
        proposal: TradeProposal,
        portfolio_state: Dict[str, Any]
    ) -> RiskAssessment:
        """Risk Manager evaluates the proposal."""
        
        prompt = RISK_MANAGER.format(
            trade_proposal=json.dumps({
                "ticker": proposal.ticker,
                "action": proposal.action.value,
                "entry_price": proposal.entry_price,
                "position_size_pct": proposal.position_size_pct,
                "stop_loss": proposal.stop_loss,
                "take_profit": proposal.take_profit,
                "confidence": proposal.confidence
            }, indent=2),
            portfolio_state=json.dumps(portfolio_state, indent=2),
            max_position_pct=self.config.MAX_POSITION_SIZE_PCT,
            max_sector_pct=self.config.MAX_SECTOR_EXPOSURE_PCT,
            min_confidence=self.config.MIN_CONFIDENCE_THRESHOLD
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            temperature=0.2,
            model=self.config.QUICK_THINK_MODEL
        )
        
        data = self._extract_json(response)
        # null-safety: if risk_assessment key is null/missing, use empty dict
        risk = data.get("risk_assessment") or {}
        
        return RiskAssessment(
            ticker=proposal.ticker,
            position_size_decision=risk.get("position_size", "approved"),
            concentration_status=risk.get("concentration", "ok"),
            correlation_level=risk.get("correlation", "low"),
            max_loss_dollars=risk.get("downside_quantified", 0),
            timing_concerns=risk.get("timing_concerns", []),
            decision=data.get("decision", "APPROVE"),
            modifications=data.get("modifications"),
            reasoning=data.get("reasoning", "")
        )
    
    async def _pm_decide(
        self,
        proposal: TradeProposal,
        risk_assessment: RiskAssessment,
        portfolio_state: Dict[str, Any]
    ) -> FinalTradeDecision:
        """Portfolio Manager makes final decision."""
        
        prompt = PORTFOLIO_MANAGER.format(
            trade_proposal=json.dumps({
                "ticker": proposal.ticker,
                "action": proposal.action.value,
                "entry_price": proposal.entry_price,
                "position_size_pct": proposal.position_size_pct,
                "stop_loss": proposal.stop_loss,
                "take_profit": proposal.take_profit,
                "rationale": proposal.rationale,
                "confidence": proposal.confidence
            }, indent=2),
            risk_assessment=json.dumps({
                "decision": risk_assessment.decision,
                "position_size": risk_assessment.position_size_decision,
                "concentration": risk_assessment.concentration_status,
                "max_loss": risk_assessment.max_loss_dollars,
                "timing_concerns": risk_assessment.timing_concerns,
                "modifications": risk_assessment.modifications,
                "reasoning": risk_assessment.reasoning
            }, indent=2),
            strategy_context=json.dumps(portfolio_state.get("strategy", {}), indent=2)
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            temperature=0.2,
            model=self.config.DEEP_THINK_MODEL
        )
        
        data = self._extract_json(response)
        # null-safety: if if_execute key is null/missing, use empty dict
        exec_data = data.get("if_execute") or {}
        
        return FinalTradeDecision(
            ticker=proposal.ticker,
            decision=FinalDecision(data.get("final_decision", "REJECT")),
            final_size_pct=exec_data.get("size"),
            entry_type=exec_data.get("entry"),
            stop_loss=exec_data.get("stop"),
            targets=exec_data.get("targets"),
            reject_reason=data.get("if_reject_reason"),
            defer_until=data.get("if_defer_until"),
            pm_notes=data.get("pm_notes", "")
        )
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response — robust with fallback (no crashes on null/malformed)."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        # Direct parse
        try:
            result = json.loads(text)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result if isinstance(result, dict) else {}
            except json.JSONDecodeError:
                pass
        
        # Final fallback — never return None
        return {
            "parse_error": True,
            "raw_text": text[:500]
        }
