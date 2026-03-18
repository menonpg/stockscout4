"""
StockScout v4 — Debate Engine

Bull vs Bear researchers debate the trade thesis.
"""

import json
from typing import Dict, Any, List
from dataclasses import dataclass

try:
    from .prompts import BULL_RESEARCHER, BEAR_RESEARCHER, DEBATE_SYNTHESIZER
except ImportError:
    from prompts import BULL_RESEARCHER, BEAR_RESEARCHER, DEBATE_SYNTHESIZER


@dataclass
class DebateRound:
    """A single round of the bull/bear debate."""
    round_number: int
    bull_argument: Dict[str, Any]
    bear_argument: Dict[str, Any]


@dataclass
class DebateSynthesis:
    """Final synthesis after debate concludes."""
    ticker: str
    bull_strength: float
    bear_strength: float
    net_score: float  # 1-10
    conviction: str  # high/medium/low
    recommended_action: str
    key_agreements: List[str]
    key_disagreements: List[str]
    unresolved_questions: List[str]
    reasoning: str


class DebateEngine:
    """
    Orchestrates bull vs bear debate with multiple rounds.
    
    The debate structure:
    1. Bull makes opening argument
    2. Bear makes opening argument  
    3. Bull rebuts (if multiple rounds)
    4. Bear rebuts (if multiple rounds)
    5. Synthesizer produces final thesis
    """
    
    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
    
    async def debate(
        self,
        ticker: str,
        analyst_reports: Dict[str, Any]
    ) -> DebateSynthesis:
        """
        Run the full bull/bear debate.
        
        Args:
            ticker: Stock symbol
            analyst_reports: Summary from AnalystTeam.summarize_reports()
        
        Returns:
            DebateSynthesis with final recommendation
        """
        rounds: List[DebateRound] = []
        debate_history = []
        
        analyst_summary = json.dumps(analyst_reports, indent=2)
        
        for round_num in range(1, self.config.MAX_DEBATE_ROUNDS + 1):
            is_opening = round_num == 1
            round_type = "opening" if is_opening else "rebuttal"
            
            # Format previous debate for context
            previous_debate = ""
            if debate_history:
                previous_debate = "Previous debate:\n" + "\n".join(debate_history)
            
            # Bull argument
            bull_response = await self._run_researcher(
                ticker=ticker,
                role="bull",
                prompt_template=BULL_RESEARCHER,
                analyst_reports=analyst_summary,
                round_number=round_num,
                round_type=round_type,
                previous_debate=previous_debate
            )
            debate_history.append(f"BULL (Round {round_num}): {json.dumps(bull_response)}")
            
            # Bear argument (sees bull's argument in same round)
            previous_debate = "Previous debate:\n" + "\n".join(debate_history)
            bear_response = await self._run_researcher(
                ticker=ticker,
                role="bear", 
                prompt_template=BEAR_RESEARCHER,
                analyst_reports=analyst_summary,
                round_number=round_num,
                round_type=round_type,
                previous_debate=previous_debate
            )
            debate_history.append(f"BEAR (Round {round_num}): {json.dumps(bear_response)}")
            
            rounds.append(DebateRound(
                round_number=round_num,
                bull_argument=bull_response,
                bear_argument=bear_response
            ))
        
        # Synthesize debate
        synthesis = await self._synthesize(
            ticker=ticker,
            analyst_reports=analyst_summary,
            debate_transcript="\n".join(debate_history)
        )
        
        return synthesis
    
    async def _run_researcher(
        self,
        ticker: str,
        role: str,
        prompt_template: str,
        analyst_reports: str,
        round_number: int,
        round_type: str,
        previous_debate: str
    ) -> Dict[str, Any]:
        """Run bull or bear researcher."""
        
        prompt = prompt_template.format(
            ticker=ticker,
            analyst_reports=analyst_reports,
            debate_rounds=self.config.MAX_DEBATE_ROUNDS,
            round_number=round_number,
            round_type=round_type,
            previous_debate=previous_debate
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            temperature=self.config.DEBATE_TEMPERATURE,
            model=self.config.DEEP_THINK_MODEL
        )
        
        return self._extract_json(response)
    
    async def _synthesize(
        self,
        ticker: str,
        analyst_reports: str,
        debate_transcript: str
    ) -> DebateSynthesis:
        """Synthesize the debate into a final recommendation."""
        
        prompt = DEBATE_SYNTHESIZER.format(
            ticker=ticker,
            analyst_reports=analyst_reports,
            debate_transcript=debate_transcript
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            temperature=0.3,  # Lower temp for synthesis
            model=self.config.DEEP_THINK_MODEL
        )
        
        data = self._extract_json(response)
        synthesis = data.get("synthesis", {})
        
        return DebateSynthesis(
            ticker=ticker,
            bull_strength=synthesis.get("bull_strength", 0.5),
            bear_strength=synthesis.get("bear_strength", 0.5),
            net_score=synthesis.get("net_score", 5),
            conviction=synthesis.get("conviction", "medium"),
            recommended_action=data.get("recommended_action", "hold"),
            key_agreements=synthesis.get("key_agreements", []),
            key_disagreements=synthesis.get("key_disagreements", []),
            unresolved_questions=synthesis.get("unresolved_questions", []),
            reasoning=data.get("reasoning", "")
        )
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response with robust parsing."""
        import re
        
        # Try to find JSON in code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try to fix common issues: unescaped quotes in strings
        try:
            # Replace problematic characters
            cleaned = text.replace('\n', ' ').replace('\r', '')
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # Return a default structure if all parsing fails
        return {
            "position": "unknown",
            "round": 1,
            "thesis": "Unable to parse response",
            "arguments": [],
            "confidence": 0.5,
            "parse_error": True,
            "raw_text": text[:500]
        }
