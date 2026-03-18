"""
StockScout v4 — Main Entry Point

Usage:
    # Single ticker analysis
    python -m stockscout4.main --ticker NVDA
    
    # Morning brief for watchlist
    python -m stockscout4.main --mode morning-brief
    
    # Custom watchlist
    python -m stockscout4.main --mode morning-brief --tickers NVDA,AAPL,MSFT
"""

import argparse
import asyncio
import json
from datetime import datetime

try:
    from .config import DEFAULT_CONFIG
except ImportError:
    from config import DEFAULT_CONFIG
try:
    from .pipeline import StockScoutPipeline
except ImportError:
    from pipeline import StockScoutPipeline


async def run_single_analysis(ticker: str, output_file: str = None):
    """Run analysis for a single ticker."""
    pipeline = StockScoutPipeline()
    
    print(f"\n{'='*60}")
    print(f"StockScout v4 Analysis: {ticker}")
    print(f"{'='*60}\n")
    
    result = await pipeline.analyze(ticker)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"RESULTS: {ticker}")
    print(f"{'='*60}")
    
    decision = result.get("final_decision", {})
    synthesis = result.get("debate_synthesis", {})
    
    print(f"\n📊 Analyst Scores:")
    for analyst, scores in result.get("analyst_scores", {}).items():
        print(f"   {analyst}: {scores['score']}/10 (confidence: {scores['confidence']:.0%})")
    
    print(f"\n🎯 Debate Synthesis:")
    print(f"   Net Score: {synthesis.get('net_score')}/10")
    print(f"   Conviction: {synthesis.get('conviction')}")
    print(f"   Recommended: {synthesis.get('recommended_action')}")
    
    print(f"\n💼 Final Decision: {decision.get('decision')}")
    if decision.get("decision") == "EXECUTE":
        print(f"   Size: {decision.get('size_pct')}%")
        print(f"   Entry: {decision.get('entry')}")
        print(f"   Stop: ${decision.get('stop_loss')}")
        print(f"   Targets: {decision.get('targets')}")
    elif decision.get("reject_reason"):
        print(f"   Reason: {decision.get('reject_reason')}")
    
    print(f"\n⏱️  Duration: {result.get('duration_seconds'):.1f}s")
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Full results saved to: {output_file}")
    
    return result


async def run_morning_brief(tickers: list = None, output_file: str = None):
    """Run morning brief for watchlist."""
    pipeline = StockScoutPipeline()
    
    print(f"\n{'='*60}")
    print(f"StockScout v4 Morning Brief")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    
    result = await pipeline.morning_brief(watchlist=tickers)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"MORNING BRIEF SUMMARY")
    print(f"{'='*60}")
    
    print(f"\n{result.get('summary')}")
    
    print(f"\n🔥 Top Opportunities:")
    for i, opp in enumerate(result.get("top_opportunities", [])[:5], 1):
        ticker = opp.get("ticker")
        score = opp.get("debate_synthesis", {}).get("net_score", "?")
        decision = opp.get("final_decision", {}).get("decision", "?")
        print(f"   {i}. {ticker}: Score {score}/10 → {decision}")
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Full brief saved to: {output_file}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="StockScout v4 - AI Trading Desk")
    parser.add_argument("--ticker", type=str, help="Single ticker to analyze")
    parser.add_argument("--tickers", type=str, help="Comma-separated list of tickers")
    parser.add_argument("--mode", type=str, default="single", 
                       choices=["single", "morning-brief"],
                       help="Analysis mode")
    parser.add_argument("--output", type=str, help="Output file path (JSON)")
    parser.add_argument("--date", type=str, help="Analysis date (default: today)")
    
    args = parser.parse_args()
    
    if args.mode == "single":
        if not args.ticker:
            parser.error("--ticker required for single mode")
        asyncio.run(run_single_analysis(args.ticker, args.output))
    
    elif args.mode == "morning-brief":
        tickers = None
        if args.tickers:
            tickers = [t.strip() for t in args.tickers.split(",")]
        asyncio.run(run_morning_brief(tickers, args.output))


if __name__ == "__main__":
    main()
