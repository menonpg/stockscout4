"""
StockScout v4 — SoulMate Memory Integration

Stores analyses and learns from outcomes.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp


class SoulMateMemory:
    """
    Integration with SoulMate for persistent memory.
    
    Stores:
    - Analysis results
    - Trade decisions
    - Actual outcomes (for learning)
    
    Enables:
    - Pattern recognition over time
    - Accuracy tracking per analyst
    - Strategy optimization
    """
    
    def __init__(self, config):
        self.config = config
        self.collection = config.SOULMATE_COLLECTION
        # SoulMate API endpoint
        self.api_url = "https://soulmate-api-production.up.railway.app"
    
    async def store_analysis(self, analysis: Dict[str, Any]) -> bool:
        """
        Store analysis result in SoulMate.
        
        Args:
            analysis: Complete analysis from pipeline
        
        Returns:
            Success status
        """
        try:
            document = {
                "type": "stockscout4_analysis",
                "ticker": analysis.get("ticker"),
                "timestamp": analysis.get("timestamp"),
                "analyst_scores": analysis.get("analyst_scores"),
                "debate_synthesis": analysis.get("debate_synthesis"),
                "decision": analysis.get("final_decision"),
                "outcome": None,  # Filled in later
                "metadata": {
                    "version": "v4",
                    "duration": analysis.get("duration_seconds")
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/memories",
                    json={
                        "collection": self.collection,
                        "document": document,
                        "text": self._create_searchable_text(analysis)
                    }
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"SoulMate store failed: {e}")
            return False
    
    async def record_outcome(
        self,
        ticker: str,
        analysis_timestamp: str,
        outcome: Dict[str, Any]
    ) -> bool:
        """
        Record actual outcome for an analysis.
        
        Args:
            ticker: Stock symbol
            analysis_timestamp: When the analysis was made
            outcome: Actual result (price change, hit targets, etc.)
        
        Returns:
            Success status
        """
        # Would update the stored analysis with actual outcomes
        # This enables learning from results
        pass
    
    async def get_accuracy_stats(
        self,
        analyst: Optional[str] = None,
        ticker: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get accuracy statistics for analysts/tickers.
        
        Returns:
            Stats on prediction accuracy
        """
        # Would query SoulMate for analyses with outcomes
        # Calculate accuracy metrics
        return {
            "note": "Implement accuracy tracking after outcomes are recorded",
            "analyst": analyst,
            "ticker": ticker,
            "days": days
        }
    
    async def get_similar_setups(
        self,
        ticker: str,
        current_analysis: Dict[str, Any],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find historically similar setups.
        
        Uses SoulMate's semantic search to find past analyses
        with similar characteristics.
        
        Returns:
            List of similar historical analyses with outcomes
        """
        query = f"""
        {ticker} analysis with similar setup:
        - Net score: {current_analysis.get('debate_synthesis', {}).get('net_score')}
        - Conviction: {current_analysis.get('debate_synthesis', {}).get('conviction')}
        - Action: {current_analysis.get('final_decision', {}).get('decision')}
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/search",
                    json={
                        "collection": self.collection,
                        "query": query,
                        "limit": limit
                    }
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception:
            return []
    
    def _create_searchable_text(self, analysis: Dict[str, Any]) -> str:
        """Create searchable text representation of analysis."""
        parts = [
            f"StockScout v4 analysis for {analysis.get('ticker')}",
            f"Date: {analysis.get('timestamp')}",
            f"Decision: {analysis.get('final_decision', {}).get('decision')}",
            f"Net score: {analysis.get('debate_synthesis', {}).get('net_score')}",
            f"Conviction: {analysis.get('debate_synthesis', {}).get('conviction')}",
            f"Reasoning: {analysis.get('debate_synthesis', {}).get('reasoning')}"
        ]
        return "\n".join(parts)
