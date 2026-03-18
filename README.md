# StockScout v4

**The AI Trading Desk** — Multi-agent trading analysis with debate mechanism and risk gates.

## Architecture

```
Intel Layer (Pi OSINT + Trump v3 + News)
    ↓
Analyst Team (Fundamentals, Sentiment, Technical, Macro)
    ↓
Debate Layer (Bull vs Bear researchers)
    ↓
Decision Layer (Trader → Risk Manager → Portfolio Manager)
    ↓
Output (signals.themenonlab.com + SoulMate learning)
```

## What's Different from TradingAgents

| Feature | TradingAgents | StockScout v4 |
|---------|---------------|---------------|
| Intel source | Alpha Vantage API only | Pi OSINT + Trump v3 + APIs |
| Memory | Stateless | SoulMate (learns from outcomes) |
| Trump signals | ❌ | ✅ Integrated |
| Output | JSON | signals.themenonlab.com |
| Backtesting | Manual | Replay with SoulMate history |

## Quick Start

```bash
# Set API keys
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export ALPHA_VANTAGE_API_KEY=...

# Run analysis for a ticker
python -m stockscout4.main --ticker NVDA --date 2026-03-18

# Run full morning brief
python -m stockscout4.main --mode morning-brief
```

## Directory Structure

```
stockscout4/
├── agents/           # LLM agent definitions
│   ├── analysts.py   # Fundamentals, Sentiment, Technical, Macro
│   ├── researchers.py # Bull/Bear debate
│   ├── traders.py    # Trader, Risk Manager, Portfolio Manager
│   └── prompts.py    # All system prompts
├── intel/            # Data ingestion
│   ├── pi_scanner.py # Social OSINT from Pi
│   ├── trump_v3.py   # Trump signal decoder
│   ├── news.py       # News/macro crawler
│   └── market_data.py # Price/volume/fundamentals
├── utils/            # Helpers
│   ├── soulmate.py   # Memory integration
│   └── formatters.py # Output formatting
├── templates/        # Report templates
├── config.py         # Configuration
├── pipeline.py       # Main orchestrator
└── main.py           # Entry point
```

## Deployment

Target: `stockscout4.thinkcreate.ai`
Linked to: Monica's workspace (`~/clawd/stockscout4`)

## Credits

- Architecture inspired by [TradingAgents](https://github.com/TauricResearch/TradingAgents)
- Intel layer powered by Pi scanner + StockScout v3
- Memory by SoulMate
