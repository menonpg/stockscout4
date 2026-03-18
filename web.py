"""
StockScout v4 — Web Interface

FastAPI server with simple UI for running analyses.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from .config import DEFAULT_CONFIG
    from .pipeline import StockScoutPipeline
except ImportError:
    from config import DEFAULT_CONFIG
    from pipeline import StockScoutPipeline

app = FastAPI(
    title="StockScout v4",
    description="AI Trading Desk - Multi-agent analysis with debate mechanism",
    version="0.1.0"
)

# Global pipeline instance
pipeline: Optional[StockScoutPipeline] = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = StockScoutPipeline()
    return pipeline


# ============================================================================
# API Models
# ============================================================================

class AnalysisRequest(BaseModel):
    ticker: str
    portfolio_cash: float = 100000
    existing_positions: dict = {}

class BriefRequest(BaseModel):
    tickers: Optional[List[str]] = None


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    """Run full analysis for a single ticker."""
    try:
        pipe = get_pipeline()
        portfolio = {
            "cash": request.portfolio_cash,
            "positions": request.existing_positions,
            "sector_exposure": {},
            "strategy": {"style": "growth", "risk_tolerance": "moderate"}
        }
        result = await pipe.analyze(request.ticker.upper(), portfolio)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/morning-brief")
async def morning_brief(request: BriefRequest):
    """Run morning brief for watchlist."""
    try:
        pipe = get_pipeline()
        result = await pipe.morning_brief(watchlist=request.tickers)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/watchlist")
async def get_watchlist():
    """Get default watchlist."""
    return {"watchlist": DEFAULT_CONFIG.DEFAULT_WATCHLIST}


# ============================================================================
# Web UI
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockScout v4 - AI Trading Desk</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .loading { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .score-bar { transition: width 0.5s ease-out; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-blue-400 mb-2">📊 StockScout v4</h1>
            <p class="text-gray-400">AI Trading Desk — Multi-agent analysis with debate mechanism</p>
        </div>

        <!-- Input Section -->
        <div class="bg-gray-800 rounded-lg p-6 mb-6">
            <div class="flex gap-4 items-end">
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-300 mb-2">Ticker Symbol</label>
                    <input type="text" id="ticker" placeholder="NVDA" 
                           class="w-full px-4 py-3 bg-gray-700 rounded-lg text-white text-xl font-mono uppercase"
                           maxlength="5">
                </div>
                <button onclick="runAnalysis()" id="analyzeBtn"
                        class="px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition">
                    Analyze
                </button>
            </div>
            <p class="text-gray-500 text-sm mt-2">Enter a ticker symbol and click Analyze to run the full AI trading desk pipeline.</p>
        </div>

        <!-- Results Section -->
        <div id="results" class="hidden">
            <!-- Status -->
            <div id="status" class="bg-gray-800 rounded-lg p-4 mb-4">
                <div class="flex items-center gap-3">
                    <div id="statusIcon" class="text-2xl">⏳</div>
                    <div>
                        <div id="statusText" class="font-semibold">Initializing...</div>
                        <div id="statusDetail" class="text-sm text-gray-400"></div>
                    </div>
                </div>
            </div>

            <!-- Analyst Scores -->
            <div id="analysts" class="bg-gray-800 rounded-lg p-6 mb-4 hidden">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                    <span>📊</span> Analyst Team
                </h2>
                <div id="analystScores" class="space-y-3"></div>
            </div>

            <!-- Debate Results -->
            <div id="debate" class="bg-gray-800 rounded-lg p-6 mb-4 hidden">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                    <span>🎭</span> Bull vs Bear Debate
                </h2>
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div class="bg-green-900/30 rounded-lg p-4 text-center">
                        <div class="text-3xl font-bold text-green-400" id="bullStrength">--</div>
                        <div class="text-sm text-gray-400">Bull Strength</div>
                    </div>
                    <div class="bg-red-900/30 rounded-lg p-4 text-center">
                        <div class="text-3xl font-bold text-red-400" id="bearStrength">--</div>
                        <div class="text-sm text-gray-400">Bear Strength</div>
                    </div>
                </div>
                <div class="text-center mb-4">
                    <div class="text-5xl font-bold" id="netScore">--</div>
                    <div class="text-gray-400">Net Score / 10</div>
                </div>
                <div id="debateReasoning" class="text-gray-300 text-sm bg-gray-700/50 rounded p-3"></div>
            </div>

            <!-- Final Decision -->
            <div id="decision" class="bg-gray-800 rounded-lg p-6 hidden">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                    <span>💼</span> Trading Desk Decision
                </h2>
                <div id="decisionContent"></div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center text-gray-500 text-sm mt-8">
            Powered by Claude · Not financial advice · 
            <a href="https://github.com/TauricResearch/TradingAgents" class="text-blue-400 hover:underline">Inspired by TradingAgents</a>
        </div>
    </div>

    <script>
        const tickerInput = document.getElementById('ticker');
        tickerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') runAnalysis();
        });

        async function runAnalysis() {
            const ticker = document.getElementById('ticker').value.toUpperCase();
            if (!ticker) return;

            // Show results section
            document.getElementById('results').classList.remove('hidden');
            document.getElementById('analysts').classList.add('hidden');
            document.getElementById('debate').classList.add('hidden');
            document.getElementById('decision').classList.add('hidden');

            // Update status
            updateStatus('⏳', 'Running Analysis...', `Analyzing ${ticker} through the AI trading desk`);

            // Disable button
            const btn = document.getElementById('analyzeBtn');
            btn.disabled = true;
            btn.classList.add('opacity-50');
            btn.textContent = 'Analyzing...';

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker })
                });

                if (!response.ok) throw new Error('Analysis failed');
                
                const data = await response.json();
                displayResults(data);
                updateStatus('✅', 'Analysis Complete', `Completed in ${data.duration_seconds?.toFixed(1)}s`);

            } catch (error) {
                updateStatus('❌', 'Error', error.message);
            } finally {
                btn.disabled = false;
                btn.classList.remove('opacity-50');
                btn.textContent = 'Analyze';
            }
        }

        function updateStatus(icon, text, detail) {
            document.getElementById('statusIcon').textContent = icon;
            document.getElementById('statusText').textContent = text;
            document.getElementById('statusDetail').textContent = detail || '';
        }

        function displayResults(data) {
            // Analyst Scores
            const analystDiv = document.getElementById('analysts');
            const scoresDiv = document.getElementById('analystScores');
            scoresDiv.innerHTML = '';
            
            if (data.analyst_scores) {
                analystDiv.classList.remove('hidden');
                for (const [name, scores] of Object.entries(data.analyst_scores)) {
                    const pct = (scores.score / 10) * 100;
                    const color = scores.score >= 7 ? 'bg-green-500' : scores.score >= 5 ? 'bg-yellow-500' : 'bg-red-500';
                    scoresDiv.innerHTML += `
                        <div class="flex items-center gap-3">
                            <div class="w-28 text-sm capitalize">${name}</div>
                            <div class="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
                                <div class="score-bar ${color} h-full" style="width: ${pct}%"></div>
                            </div>
                            <div class="w-16 text-right font-mono">${scores.score}/10</div>
                        </div>
                    `;
                }
            }

            // Debate Results
            const debateDiv = document.getElementById('debate');
            if (data.debate_synthesis) {
                debateDiv.classList.remove('hidden');
                const syn = data.debate_synthesis;
                document.getElementById('bullStrength').textContent = `${Math.round((syn.bull_strength || 0) * 100)}%`;
                document.getElementById('bearStrength').textContent = `${Math.round((syn.bear_strength || 0) * 100)}%`;
                document.getElementById('netScore').textContent = syn.net_score || '--';
                document.getElementById('netScore').className = `text-5xl font-bold ${
                    syn.net_score >= 7 ? 'text-green-400' : syn.net_score >= 5 ? 'text-yellow-400' : 'text-red-400'
                }`;
                document.getElementById('debateReasoning').textContent = syn.reasoning || '';
            }

            // Final Decision
            const decisionDiv = document.getElementById('decision');
            if (data.final_decision) {
                decisionDiv.classList.remove('hidden');
                const dec = data.final_decision;
                const isExecute = dec.decision === 'EXECUTE';
                const bgColor = isExecute ? 'bg-green-900/30 border-green-500' : 'bg-gray-700 border-gray-600';
                
                let content = `
                    <div class="${bgColor} border rounded-lg p-4 mb-4">
                        <div class="text-3xl font-bold ${isExecute ? 'text-green-400' : 'text-gray-400'}">${dec.decision}</div>
                    </div>
                `;

                if (isExecute) {
                    content += `
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                            <div class="bg-gray-700 rounded p-3 text-center">
                                <div class="text-xl font-bold text-blue-400">${dec.size_pct}%</div>
                                <div class="text-xs text-gray-400">Position Size</div>
                            </div>
                            <div class="bg-gray-700 rounded p-3 text-center">
                                <div class="text-xl font-bold">${dec.entry || 'Market'}</div>
                                <div class="text-xs text-gray-400">Entry</div>
                            </div>
                            <div class="bg-gray-700 rounded p-3 text-center">
                                <div class="text-xl font-bold text-red-400">$${dec.stop_loss}</div>
                                <div class="text-xs text-gray-400">Stop Loss</div>
                            </div>
                            <div class="bg-gray-700 rounded p-3 text-center">
                                <div class="text-xl font-bold text-green-400">${dec.targets?.map(t => '$' + t).join(' → ') || '--'}</div>
                                <div class="text-xs text-gray-400">Targets</div>
                            </div>
                        </div>
                    `;
                }

                if (dec.pm_notes) {
                    content += `<div class="text-sm text-gray-300 bg-gray-700/50 rounded p-3">${dec.pm_notes}</div>`;
                }
                if (dec.reject_reason) {
                    content += `<div class="text-sm text-gray-300 bg-gray-700/50 rounded p-3">${dec.reject_reason}</div>`;
                }

                document.getElementById('decisionContent').innerHTML = content;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE


# ============================================================================
# Run server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
