"""
StockScout v4 — Analyst Team

Four specialized analysts that evaluate different aspects of a trade.
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    from .prompts import (
        FUNDAMENTALS_ANALYST,
        SENTIMENT_ANALYST, 
        TECHNICAL_ANALYST,
        MACRO_ANALYST
    )
except ImportError:
    from prompts import (
        FUNDAMENTALS_ANALYST,
        SENTIMENT_ANALYST, 
        TECHNICAL_ANALYST,
        MACRO_ANALYST
    )


@dataclass
class AnalystReport:
    """Output from a single analyst."""
    ticker: str
    analyst: str
    score: float  # 1-10, 10 = extremely bullish
    confidence: float  # 0-1
    key_points: list
    risks: list
    reasoning: str
    raw_data: Dict[str, Any]


class AnalystTeam:
    """
    Coordinates four specialized analysts:
    - Fundamentals: Financial health, valuation
    - Sentiment: Social buzz, positioning, Trump signals
    - Technical: Price action, patterns, indicators
    - Macro: Fed, economy, sector dynamics
    """
    
    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
        self.analysts = {
            "fundamentals": FUNDAMENTALS_ANALYST,
            "sentiment": SENTIMENT_ANALYST,
            "technical": TECHNICAL_ANALYST,
            "macro": MACRO_ANALYST
        }
    
    async def analyze(
        self,
        ticker: str,
        intel_data: Dict[str, Any]
    ) -> Dict[str, AnalystReport]:
        """
        Run all four analysts in parallel and collect reports.
        
        Args:
            ticker: Stock symbol
            intel_data: Dict containing data for each analyst type
                - fundamentals_data
                - sentiment_data
                - trump_signals
                - technical_data
                - macro_data
        
        Returns:
            Dict mapping analyst name to AnalystReport
        """
        reports = {}
        
        # Run analysts (could parallelize with asyncio.gather)
        for analyst_name, prompt_template in self.analysts.items():
            report = await self._run_analyst(
                ticker=ticker,
                analyst_name=analyst_name,
                prompt_template=prompt_template,
                intel_data=intel_data
            )
            reports[analyst_name] = report
        
        return reports
    

    async def analyze_single(
        self,
        analyst_name: str,
        ticker: str,
        intel_data: Dict[str, Any]
    ) -> "AnalystReport":
        """Run a single named analyst — used for streaming pipeline."""
        prompt_template = self.analysts.get(analyst_name)
        if not prompt_template:
            raise ValueError(f"Unknown analyst: {analyst_name}")
        return await self._run_analyst(
            ticker=ticker,
            analyst_name=analyst_name,
            prompt_template=prompt_template,
            intel_data=intel_data
        )

    async def _run_analyst(
        self,
        ticker: str,
        analyst_name: str,
        prompt_template: str,
        intel_data: Dict[str, Any]
    ) -> AnalystReport:
        """Run a single analyst and parse response."""
        
        # Build prompt with relevant data
        # Build context dict — includes real data from yfinance, FRED, Intel, SS2
        news_summary = [
            {"title": n.get("title"), "publisher": n.get("publisher")}
            for n in (intel_data.get("news") or [])[:5]
        ]
        prompt = prompt_template.format(
            ticker=ticker,
            fundamentals_data=json.dumps(intel_data.get("fundamentals", {}), indent=2),
            sentiment_data=json.dumps(intel_data.get("sentiment", {}), indent=2),
            trump_signals=json.dumps(intel_data.get("trump_signals", {}), indent=2),
            technical_data=json.dumps(intel_data.get("technical", {}), indent=2),
            macro_data=json.dumps(intel_data.get("macro", {}), indent=2),
            news_data=json.dumps(news_summary, indent=2),
            intel_data=json.dumps(intel_data.get("intel", {}), indent=2),
            ss2_score=json.dumps(intel_data.get("ss2_score", {}), indent=2),
        )
        
        # Call LLM
        response = await self.llm.complete(
            prompt=prompt,
            temperature=self.config.ANALYST_TEMPERATURE,
            model=self.config.QUICK_THINK_MODEL
        )
        
        # Parse JSON response
        try:
            data = self._extract_json(response)
            return AnalystReport(
                ticker=ticker,
                analyst=analyst_name,
                score=data.get("score", 5),
                confidence=data.get("confidence", 0.5),
                key_points=data.get("key_points", []),
                risks=data.get("risks", []),
                reasoning=data.get("reasoning", ""),
                raw_data=data
            )
        except Exception as e:
            # Return neutral report on parse failure
            return AnalystReport(
                ticker=ticker,
                analyst=analyst_name,
                score=5,
                confidence=0.3,
                key_points=[f"Analysis failed: {str(e)}"],
                risks=["Unable to complete analysis"],
                reasoning="Error parsing analyst response",
                raw_data={"error": str(e), "raw": response}
            )
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Try to find JSON in code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        return json.loads(text)
    
    def summarize_reports(self, reports: Dict[str, AnalystReport]) -> Dict[str, Any]:
        """Create a summary of all analyst reports for the debate layer."""
        summary = {
            "ticker": list(reports.values())[0].ticker if reports else "",
            "average_score": sum(r.score for r in reports.values()) / len(reports) if reports else 5,
            "average_confidence": sum(r.confidence for r in reports.values()) / len(reports) if reports else 0.5,
            "analysts": {}
        }
        
        for name, report in reports.items():
            summary["analysts"][name] = {
                "score": report.score,
                "confidence": report.confidence,
                "key_points": report.key_points,
                "risks": report.risks,
                "reasoning": report.reasoning
            }
        
        return summary
