"""
StockScout v4 — Web Interface

FastAPI server with UI for running analyses.
Shows: Intel → Analyst Team → Bull/Bear Debate → Trading Desk Decision
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, List, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
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


class AnalysisRequest(BaseModel):
    ticker: str
    portfolio_cash: float = 100000
    existing_positions: dict = {}

class BriefRequest(BaseModel):
    tickers: Optional[List[str]] = None


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
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


@app.get("/api/analyze/stream/{ticker}")
async def analyze_stream(ticker: str):
    """Stream analysis progress via Server-Sent Events."""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        pipe = get_pipeline()
        ticker_upper = ticker.upper()
        
        steps = [
            ("intel",        "🔍 Gathering market intel...",            10),
            ("fundamentals", "📊 Fundamentals analyst working...",       20),
            ("sentiment",    "💭 Sentiment analyst working...",          30),
            ("technical",    "📈 Technical analyst working...",          40),
            ("macro",        "🌍 Macro analyst working...",              50),
            ("debate_1",     "🎭 Bull vs Bear — Round 1 opening...",     60),
            ("debate_2",     "🎭 Bull vs Bear — Round 2 rebuttal...",    70),
            ("synthesis",    "🔮 Synthesizing debate outcome...",        80),
            ("trader",       "💹 Trader agent formulating proposal...",  85),
            ("risk",         "⚠️ Risk manager checking limits...",       90),
            ("pm",           "👔 Portfolio manager — final call...",     95),
        ]
        
        try:
            yield f"data: {json.dumps({'step': 'start', 'message': f'Starting analysis for {ticker_upper}', 'progress': 0})}\n\n"
            
            portfolio = {
                "cash": 100000,
                "positions": {},
                "sector_exposure": {},
                "strategy": {"style": "growth", "risk_tolerance": "moderate"}
            }
            
            for step_id, message, progress in steps:
                yield f"data: {json.dumps({'step': step_id, 'message': message, 'progress': progress})}\n\n"
                await asyncio.sleep(0.1)
            
            result = await pipe.analyze(ticker_upper, portfolio)
            
            yield f"data: {json.dumps({'step': 'complete', 'message': 'Analysis complete!', 'progress': 100, 'result': result})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': str(e), 'progress': 0})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/morning-brief")
async def morning_brief(request: BriefRequest):
    try:
        pipe = get_pipeline()
        result = await pipe.morning_brief(watchlist=request.tickers)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/watchlist")
async def get_watchlist():
    return {"watchlist": DEFAULT_CONFIG.DEFAULT_WATCHLIST}


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockScout v4 - AI Trading Desk</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .score-bar { transition: width 0.5s ease-out; }
        .debate-round { border-left: 3px solid #4B5563; }
        details > summary { cursor: pointer; list-style: none; }
        details > summary::-webkit-details-marker { display: none; }
        details[open] summary .chevron { transform: rotate(90deg); }
        .chevron { transition: transform 0.2s; display: inline-block; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">

        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-blue-400 mb-2">📊 StockScout v4</h1>
            <p class="text-gray-400">AI Trading Desk — Intel → Analysts → Bull/Bear Debate → Decision</p>
            <button onclick="toggleAbout()" class="mt-2 text-sm text-blue-400 hover:text-blue-300">
                ℹ️ How it works
            </button>
        </div>

        <!-- About Section -->
        <div id="aboutSection" class="hidden bg-gray-800 rounded-lg p-6 mb-6 text-sm">
            <h3 class="text-lg font-semibold text-blue-400 mb-3">🧠 The AI Trading Desk Pipeline</h3>
            <div class="grid md:grid-cols-2 gap-4 mb-4">
                <div class="bg-gray-700/50 rounded p-3">
                    <div class="font-semibold text-green-400 mb-1">1️⃣ Intel Gathering</div>
                    <p class="text-gray-300">Market data, news sentiment, macro indicators, Pi OSINT scanner, Trump signal decoder.</p>
                </div>
                <div class="bg-gray-700/50 rounded p-3">
                    <div class="font-semibold text-yellow-400 mb-1">2️⃣ Analyst Team (4 AIs)</div>
                    <p class="text-gray-300">Fundamentals · Sentiment · Technical · Macro — each produces an independent score 1–10 with rationale.</p>
                </div>
                <div class="bg-gray-700/50 rounded p-3">
                    <div class="font-semibold text-purple-400 mb-1">3️⃣ Bull vs Bear Debate (2 rounds)</div>
                    <p class="text-gray-300">Two AI researchers argue the bull and bear case with rebuttals. A synthesizer adjudicates with a net score and conviction level.</p>
                </div>
                <div class="bg-gray-700/50 rounded p-3">
                    <div class="font-semibold text-blue-400 mb-1">4️⃣ Trading Desk Chain</div>
                    <p class="text-gray-300">Trader proposes → Risk Manager checks limits → Portfolio Manager makes final EXECUTE / REJECT / DEFER call.</p>
                </div>
            </div>
            <div class="text-gray-400 text-xs">
                <strong>~12 AI calls per analysis</strong> · ~60–90 seconds · ~$0.15–0.20 per ticker<br>
                Inspired by <a href="https://github.com/TauricResearch/TradingAgents" class="text-blue-400 hover:underline">TradingAgents</a>
            </div>
        </div>

        <!-- Input -->
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
            <p class="text-gray-500 text-sm mt-2">Runs the full AI trading desk pipeline — intel, debate, decision.</p>
        </div>

        <!-- Results -->
        <div id="results" class="hidden space-y-4">

            <!-- Status bar -->
            <div id="status" class="bg-gray-800 rounded-lg p-4">
                <div class="flex items-center gap-3">
                    <div id="statusIcon" class="text-2xl">⏳</div>
                    <div>
                        <div id="statusText" class="font-semibold">Initializing...</div>
                        <div id="statusDetail" class="text-sm text-gray-400"></div>
                    </div>
                    <div id="progressBar" class="ml-auto w-32 bg-gray-700 rounded-full h-2">
                        <div id="progressFill" class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width:0%"></div>
                    </div>
                </div>
            </div>

            <!-- Intel Summary -->
            <div id="intelSection" class="bg-gray-800 rounded-lg p-6 hidden">
                <h2 class="text-xl font-semibold mb-3 flex items-center gap-2">📡 <span>Intel Summary</span></h2>
                <div id="intelContent" class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm"></div>
            </div>

            <!-- Analyst Team -->
            <div id="analysts" class="bg-gray-800 rounded-lg p-6 hidden">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">📊 <span>Analyst Team</span></h2>
                <div id="analystScores" class="space-y-4"></div>
            </div>

            <!-- Bull vs Bear Debate -->
            <div id="debate" class="bg-gray-800 rounded-lg p-6 hidden">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">🎭 <span>Bull vs Bear Debate</span></h2>

                <!-- Score summary -->
                <div class="grid grid-cols-3 gap-4 mb-5">
                    <div class="bg-green-900/30 border border-green-800 rounded-lg p-4 text-center">
                        <div class="text-3xl font-bold text-green-400" id="bullStrength">--</div>
                        <div class="text-sm text-gray-400 mt-1">Bull Strength</div>
                    </div>
                    <div class="bg-gray-700/50 rounded-lg p-4 text-center">
                        <div class="text-5xl font-bold" id="netScore">--</div>
                        <div class="text-sm text-gray-400 mt-1">Net Score / 10</div>
                    </div>
                    <div class="bg-red-900/30 border border-red-800 rounded-lg p-4 text-center">
                        <div class="text-3xl font-bold text-red-400" id="bearStrength">--</div>
                        <div class="text-sm text-gray-400 mt-1">Bear Strength</div>
                    </div>
                </div>

                <!-- Conviction + Recommendation -->
                <div id="convictionBar" class="mb-4"></div>

                <!-- Synthesis reasoning -->
                <div id="synthReasoning" class="text-gray-300 text-sm bg-gray-700/50 rounded p-3 mb-4"></div>

                <!-- Key agreements / disagreements -->
                <div id="debateKeyPoints" class="grid md:grid-cols-2 gap-4 mb-5"></div>

                <!-- Debate rounds — THE ACTUAL ARGUMENTS -->
                <div id="debateRounds" class="space-y-3"></div>
            </div>

            <!-- Trading Desk Decision -->
            <div id="decision" class="bg-gray-800 rounded-lg p-6 hidden">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">💼 <span>Trading Desk Decision</span></h2>
                <div id="decisionContent"></div>
            </div>
        </div>

        <div class="text-center text-gray-600 text-sm mt-8">
            Powered by Claude · Not financial advice ·
            <a href="https://github.com/TauricResearch/TradingAgents" class="text-blue-500 hover:underline">Inspired by TradingAgents</a>
        </div>
    </div>

<script>
    const tickerInput = document.getElementById('ticker');
    tickerInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') runAnalysis(); });
    tickerInput.addEventListener('input', (e) => { e.target.value = e.target.value.toUpperCase(); });

    function toggleAbout() {
        document.getElementById('aboutSection').classList.toggle('hidden');
    }

    function updateStatus(icon, text, detail, progress) {
        document.getElementById('statusIcon').textContent = icon;
        document.getElementById('statusText').textContent = text;
        document.getElementById('statusDetail').textContent = detail || '';
        if (progress !== undefined) {
            document.getElementById('progressFill').style.width = progress + '%';
        }
    }

    function resetButton() {
        const btn = document.getElementById('analyzeBtn');
        btn.disabled = false;
        btn.classList.remove('opacity-50');
        btn.textContent = 'Analyze';
    }

    async function runAnalysis() {
        const ticker = document.getElementById('ticker').value.toUpperCase();
        if (!ticker) return;

        // Show/reset results
        document.getElementById('results').classList.remove('hidden');
        ['analysts', 'debate', 'decision', 'intelSection'].forEach(id => {
            document.getElementById(id).classList.add('hidden');
        });

        const btn = document.getElementById('analyzeBtn');
        btn.disabled = true;
        btn.classList.add('opacity-50');
        btn.textContent = 'Analyzing...';
        updateStatus('⏳', `Analyzing ${ticker}...`, 'Starting pipeline...', 0);

        try {
            const eventSource = new EventSource(`/api/analyze/stream/${ticker}`);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.step === 'error') {
                    updateStatus('❌', 'Error', data.message, 0);
                    eventSource.close();
                    resetButton();
                    return;
                }

                if (data.step === 'complete') {
                    displayResults(data.result);
                    const dur = data.result.duration_seconds;
                    updateStatus('✅', 'Analysis complete', dur ? `Done in ${dur.toFixed(1)}s` : 'Done', 100);
                    eventSource.close();
                    resetButton();
                    return;
                }

                updateStatus('⏳', data.message, `${data.progress}% complete`, data.progress);
            };

            eventSource.onerror = () => {
                updateStatus('❌', 'Connection error', 'Please try again', 0);
                eventSource.close();
                resetButton();
            };

        } catch (error) {
            updateStatus('❌', 'Error', error.message, 0);
            resetButton();
        }
    }

    function displayResults(data) {
        // ── Intel Summary ──────────────────────────────────────────────
        const intel = data.intel_summary || {};
        if (intel.current_price) {
            const intelSec = document.getElementById('intelSection');
            intelSec.classList.remove('hidden');
            const price = intel.current_price ? `$${Number(intel.current_price).toFixed(2)}` : '--';
            const changePct = intel.change_pct || '--';
            const sentiment = intel.sentiment || 'neutral';
            const trumpRel = (intel.trump_relevance || 0).toFixed(1);
            document.getElementById('intelContent').innerHTML = `
                <div class="bg-gray-700/50 rounded p-3 text-center">
                    <div class="text-lg font-bold text-blue-300">${price}</div>
                    <div class="text-xs text-gray-400">Current Price</div>
                </div>
                <div class="bg-gray-700/50 rounded p-3 text-center">
                    <div class="text-lg font-bold">${changePct}</div>
                    <div class="text-xs text-gray-400">Change</div>
                </div>
                <div class="bg-gray-700/50 rounded p-3 text-center">
                    <div class="text-lg font-bold capitalize">${sentiment}</div>
                    <div class="text-xs text-gray-400">Sentiment</div>
                </div>
                <div class="bg-gray-700/50 rounded p-3 text-center">
                    <div class="text-lg font-bold">${trumpRel}</div>
                    <div class="text-xs text-gray-400">Trump Signal</div>
                </div>
            `;
        }

        // ── Analyst Team ───────────────────────────────────────────────
        const analystDiv = document.getElementById('analysts');
        const scoresDiv = document.getElementById('analystScores');
        scoresDiv.innerHTML = '';

        if (data.analyst_scores) {
            analystDiv.classList.remove('hidden');
            const names = { fundamentals: '📈 Fundamentals', sentiment: '💭 Sentiment', technical: '🕯️ Technical', macro: '🌍 Macro' };
            for (const [name, a] of Object.entries(data.analyst_scores)) {
                const score = a.score || 5;
                const pct = (score / 10) * 100;
                const color = score >= 7 ? 'bg-green-500' : score >= 5 ? 'bg-yellow-500' : 'bg-red-500';
                const label = names[name] || name;
                const keyPoints = (a.key_points || []).map(p => `<li class="text-gray-300">${p}</li>`).join('');
                const risks = (a.risks || []).map(r => `<li class="text-red-300">${r}</li>`).join('');
                scoresDiv.innerHTML += `
                    <div class="bg-gray-700/30 rounded-lg p-3">
                        <div class="flex items-center gap-3 mb-2">
                            <div class="w-32 text-sm font-medium">${label}</div>
                            <div class="flex-1 bg-gray-700 rounded-full h-3 overflow-hidden">
                                <div class="score-bar ${color} h-full" style="width:${pct}%"></div>
                            </div>
                            <div class="w-16 text-right font-mono font-bold">${score}/10</div>
                            <div class="text-xs text-gray-400">${Math.round((a.confidence||0.5)*100)}% conf</div>
                        </div>
                        ${a.reasoning ? `<p class="text-gray-400 text-xs mb-2 italic">${a.reasoning}</p>` : ''}
                        ${keyPoints ? `<ul class="text-xs list-disc list-inside space-y-0.5 mb-1">${keyPoints}</ul>` : ''}
                        ${risks ? `<ul class="text-xs list-disc list-inside space-y-0.5 text-red-400 mt-1">Risks: ${risks}</ul>` : ''}
                    </div>
                `;
            }
        }

        // ── Bull vs Bear Debate ────────────────────────────────────────
        const debateDiv = document.getElementById('debate');
        if (data.debate_synthesis) {
            debateDiv.classList.remove('hidden');
            const syn = data.debate_synthesis;

            // Scores
            document.getElementById('bullStrength').textContent = `${Math.round((syn.bull_strength||0)*100)}%`;
            document.getElementById('bearStrength').textContent = `${Math.round((syn.bear_strength||0)*100)}%`;
            const ns = syn.net_score || 5;
            const nsEl = document.getElementById('netScore');
            nsEl.textContent = ns;
            nsEl.className = `text-5xl font-bold ${ns >= 7 ? 'text-green-400' : ns >= 5 ? 'text-yellow-400' : 'text-red-400'}`;

            // Conviction badge
            const conv = syn.conviction || 'medium';
            const convColor = conv === 'high' ? 'bg-green-700 text-green-200' : conv === 'low' ? 'bg-red-700 text-red-200' : 'bg-yellow-700 text-yellow-200';
            const rec = syn.recommended_action || '';
            document.getElementById('convictionBar').innerHTML = `
                <div class="flex items-center gap-3">
                    <span class="${convColor} px-3 py-1 rounded-full text-sm font-semibold capitalize">${conv} conviction</span>
                    ${rec ? `<span class="text-gray-300 text-sm">Recommended: <strong class="text-white">${rec.toUpperCase()}</strong></span>` : ''}
                </div>
            `;

            // Synthesis reasoning
            document.getElementById('synthReasoning').textContent = syn.reasoning || '';

            // Key agreements / disagreements
            const kpDiv = document.getElementById('debateKeyPoints');
            kpDiv.innerHTML = '';
            if ((syn.key_agreements||[]).length || (syn.key_disagreements||[]).length) {
                const agrees = (syn.key_agreements||[]).map(a => `<li>${a}</li>`).join('');
                const disagrees = (syn.key_disagreements||[]).map(d => `<li>${d}</li>`).join('');
                const questions = (syn.unresolved_questions||[]).map(q => `<li>${q}</li>`).join('');
                kpDiv.innerHTML = `
                    ${agrees ? `<div class="bg-green-900/20 rounded p-3"><div class="text-xs font-semibold text-green-400 mb-1">✅ Key Agreements</div><ul class="text-xs text-gray-300 list-disc list-inside space-y-0.5">${agrees}</ul></div>` : ''}
                    ${disagrees ? `<div class="bg-red-900/20 rounded p-3"><div class="text-xs font-semibold text-red-400 mb-1">⚡ Key Disagreements</div><ul class="text-xs text-gray-300 list-disc list-inside space-y-0.5">${disagrees}</ul></div>` : ''}
                    ${questions ? `<div class="bg-yellow-900/20 rounded p-3 md:col-span-2"><div class="text-xs font-semibold text-yellow-400 mb-1">❓ Unresolved Questions</div><ul class="text-xs text-gray-300 list-disc list-inside space-y-0.5">${questions}</ul></div>` : ''}
                `;
            }

            // Debate rounds — the actual bull/bear arguments
            const roundsDiv = document.getElementById('debateRounds');
            roundsDiv.innerHTML = '';
            const rounds = syn.rounds || [];
            if (rounds.length) {
                roundsDiv.innerHTML = `<div class="text-sm font-semibold text-gray-300 mb-2">📜 Debate Transcript</div>`;
                rounds.forEach(r => {
                    const bull = r.bull || {};
                    const bear = r.bear || {};
                    const roundLabel = r.round === 1 ? 'Opening Arguments' : `Round ${r.round} — Rebuttals`;
                    roundsDiv.innerHTML += `
                        <details class="debate-round bg-gray-700/30 rounded-lg overflow-hidden">
                            <summary class="flex items-center gap-2 p-3 font-medium text-sm select-none hover:bg-gray-700/50 transition">
                                <span class="chevron text-gray-400">▶</span>
                                <span>Round ${r.round}: ${roundLabel}</span>
                            </summary>
                            <div class="p-3 pt-0 grid md:grid-cols-2 gap-3 mt-3">
                                <div class="bg-green-900/20 border border-green-800/50 rounded-lg p-3">
                                    <div class="text-xs font-bold text-green-400 mb-2">🐂 BULL CASE</div>
                                    ${renderArgument(bull)}
                                </div>
                                <div class="bg-red-900/20 border border-red-800/50 rounded-lg p-3">
                                    <div class="text-xs font-bold text-red-400 mb-2">🐻 BEAR CASE</div>
                                    ${renderArgument(bear)}
                                </div>
                            </div>
                        </details>
                    `;
                });
                // Auto-open round 1
                setTimeout(() => {
                    const first = roundsDiv.querySelector('details');
                    if (first) first.open = true;
                }, 100);
            }
        }

        // ── Trading Desk Decision ──────────────────────────────────────
        const decisionDiv = document.getElementById('decision');
        if (data.final_decision) {
            decisionDiv.classList.remove('hidden');
            const dec = data.final_decision;
            const isExecute = dec.decision === 'EXECUTE';
            const isDefer = dec.decision === 'DEFER';

            const headerColor = isExecute
                ? 'bg-green-900/40 border-green-600'
                : isDefer ? 'bg-yellow-900/40 border-yellow-600'
                : 'bg-gray-700 border-gray-600';

            const decLabel = isExecute ? '✅ EXECUTE' : isDefer ? '⏳ DEFER' : '❌ REJECT / HOLD';
            const decColor = isExecute ? 'text-green-400' : isDefer ? 'text-yellow-400' : 'text-gray-400';

            let content = `<div class="${headerColor} border rounded-lg p-4 mb-4">
                <div class="text-3xl font-bold ${decColor}">${decLabel}</div>
            </div>`;

            if (isExecute && dec.size_pct) {
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
                            <div class="text-xl font-bold text-red-400">${dec.stop_loss ? '$' + dec.stop_loss : '--'}</div>
                            <div class="text-xs text-gray-400">Stop Loss</div>
                        </div>
                        <div class="bg-gray-700 rounded p-3 text-center">
                            <div class="text-xl font-bold text-green-400">${(dec.targets||[]).map(t => '$' + t).join(' → ') || '--'}</div>
                            <div class="text-xs text-gray-400">Targets</div>
                        </div>
                    </div>
                `;
            }

            if (dec.pm_notes) content += `<div class="text-sm text-gray-300 bg-gray-700/50 rounded p-3 mb-2">📝 ${dec.pm_notes}</div>`;
            if (dec.reject_reason) content += `<div class="text-sm text-gray-400 bg-gray-700/30 rounded p-3 mb-2">Reason: ${dec.reject_reason}</div>`;
            if (dec.defer_until) content += `<div class="text-sm text-yellow-300 bg-yellow-900/20 rounded p-3">Defer until: ${dec.defer_until}</div>`;

            document.getElementById('decisionContent').innerHTML = content;
        }
    }

    function renderArgument(arg) {
        if (!arg || arg.parse_error) {
            return `<p class="text-xs text-gray-500 italic">${arg.thesis || 'No argument data'}</p>`;
        }
        const thesis = arg.thesis || arg.position || '';
        const args = arg.arguments || [];
        const conf = arg.confidence ? Math.round(arg.confidence * 100) : null;
        return `
            ${thesis ? `<p class="text-xs text-gray-200 font-medium mb-2">${thesis}</p>` : ''}
            ${args.length ? `<ul class="text-xs text-gray-300 list-disc list-inside space-y-0.5">${args.map(a => `<li>${typeof a === 'string' ? a : JSON.stringify(a)}</li>`).join('')}</ul>` : ''}
            ${conf ? `<div class="text-xs text-gray-500 mt-2">Confidence: ${conf}%</div>` : ''}
        `;
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
