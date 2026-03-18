#!/usr/bin/env python3
"""Quick test of StockScout v4 pipeline."""

import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from utils.llm_client import LLMClient
from agents.analysts import AnalystTeam
from agents.researchers import DebateEngine
from agents.traders import TradingDesk

async def test_single_ticker(ticker: str = "NVDA"):
    """Run a simplified test of the pipeline."""
    
    print(f"\n{'='*60}")
    print(f"StockScout v4 Test Run: {ticker}")
    print(f"{'='*60}\n")
    
    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set!")
        return
    
    print("✅ API key found")
    
    # Initialize LLM client
    print("Initializing LLM client...")
    llm = LLMClient(DEFAULT_CONFIG)
    
    # Test LLM connection with a simple prompt
    print("Testing LLM connection...")
    try:
        test_response = await llm.complete(
            prompt="Reply with just 'OK' if you can hear me.",
            temperature=0,
            max_tokens=10
        )
        print(f"✅ LLM response: {test_response.strip()}")
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return
    
    # Create mock intel data (would come from real APIs in production)
    print("\nUsing mock intel data for test...")
    mock_intel = {
        "fundamentals": {
            "overview": {
                "market_cap": "3.2T",
                "pe_ratio": "65",
                "revenue_growth": "122%",
                "profit_margin": "55%",
                "sector": "Technology",
                "industry": "Semiconductors"
            }
        },
        "technical": {
            "prices": [{"close": 950, "date": "2026-03-17"}],
            "rsi": 62,
            "macd": {"histogram": 2.5, "signal": "bullish"},
            "trend": "uptrend"
        },
        "macro": {
            "fed_rate": 5.25,
            "vix": 15,
            "market_regime": "risk-on"
        },
        "sentiment": {
            "overall_sentiment": "bullish",
            "sentiment_score": 0.75
        },
        "trump_signals": {
            "relevance_score": 0.3,
            "overall_signal": "slightly_bullish"
        }
    }
    
    # Run Analyst Team
    print("\n📊 Running Analyst Team...")
    analysts = AnalystTeam(llm, DEFAULT_CONFIG)
    
    try:
        reports = await analysts.analyze(ticker, mock_intel)
        summary = analysts.summarize_reports(reports)
        
        print("\nAnalyst Scores:")
        for name, report in reports.items():
            print(f"  {name}: {report.score}/10 (conf: {report.confidence:.0%})")
            print(f"    → {report.reasoning[:100]}...")
        
        print(f"\n  Average: {summary['average_score']:.1f}/10")
        
    except Exception as e:
        print(f"❌ Analyst error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run Debate
    print("\n🎭 Running Bull/Bear Debate...")
    debate = DebateEngine(llm, DEFAULT_CONFIG)
    
    try:
        synthesis = await debate.debate(ticker, summary)
        
        print(f"\nDebate Results:")
        print(f"  Bull strength: {synthesis.bull_strength:.0%}")
        print(f"  Bear strength: {synthesis.bear_strength:.0%}")
        print(f"  Net score: {synthesis.net_score}/10")
        print(f"  Conviction: {synthesis.conviction}")
        print(f"  Recommended: {synthesis.recommended_action}")
        print(f"  Reasoning: {synthesis.reasoning[:150]}...")
        
    except Exception as e:
        print(f"❌ Debate error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run Trading Desk
    print("\n💼 Running Trading Desk...")
    desk = TradingDesk(llm, DEFAULT_CONFIG)
    
    mock_portfolio = {
        "cash": 100000,
        "positions": {"AAPL": 5000},
        "sector_exposure": {"Technology": 5},
        "strategy": {"style": "growth", "risk_tolerance": "moderate"}
    }
    
    synthesis_dict = {
        "ticker": synthesis.ticker,
        "net_score": synthesis.net_score,
        "conviction": synthesis.conviction,
        "recommended_action": synthesis.recommended_action,
        "bull_strength": synthesis.bull_strength,
        "bear_strength": synthesis.bear_strength,
        "reasoning": synthesis.reasoning
    }
    
    try:
        decision = await desk.process_trade(ticker, synthesis_dict, mock_portfolio)
        
        print(f"\n{'='*60}")
        print(f"FINAL DECISION: {decision.decision.value}")
        print(f"{'='*60}")
        
        if decision.decision.value == "EXECUTE":
            print(f"  Size: {decision.final_size_pct}%")
            print(f"  Entry: {decision.entry_type}")
            print(f"  Stop: {decision.stop_loss}")
            print(f"  Targets: {decision.targets}")
        elif decision.reject_reason:
            print(f"  Reason: {decision.reject_reason}")
        
        print(f"  PM Notes: {decision.pm_notes}")
        
    except Exception as e:
        print(f"❌ Trading desk error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n✅ Test complete!")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    asyncio.run(test_single_ticker(ticker))
