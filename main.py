# backend/main.py
import os
import logging
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables (OPENAI_API_KEY, etc.)
load_dotenv()

# Import agents
try:
    from backend.agents.planner_agent import PlannerAgent
    from backend.agents.ranker_agent import RankerAgent
    from backend.agents.orchestrator_agent import OrchestratorAgent
    from backend.agents.analyzer_agent import AnalyzerAgent
except Exception as e:
    print("⚠️ Agent import failed:", e)
    PlannerAgent = None
    RankerAgent = None
    OrchestratorAgent = None
    AnalyzerAgent = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multi-agent-game-tester")

app = FastAPI(title="Multi-Agent Game Tester POC")

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Request / Response Models
# ----------------------------
class PlanRequest(BaseModel):
    target_url: str
    seeds: Optional[List[str]] = None
    n_candidates: Optional[int] = 20


class PlanResponse(BaseModel):
    candidates: List[Dict[str, Any]]


class RankRequest(BaseModel):
    candidates: List[Dict[str, Any]]
    top_k: Optional[int] = 10


class RankResponse(BaseModel):
    top_candidates: List[Dict[str, Any]]


class ExecuteRequest(BaseModel):
    tests: List[Dict[str, Any]]
    parallelism: Optional[int] = 3


class ExecuteResponse(BaseModel):
    run_id: str
    results: List[Dict[str, Any]]


class AnalyzeRequest(BaseModel):
    run_id: str
    results: List[Dict[str, Any]]


class AnalyzeResponse(BaseModel):
    report_path: str
    report: Dict[str, Any]


# ----------------------------
# Routes
# ----------------------------
@app.get("/")
async def root():
    return {
        "message": "✅ Multi-Agent Game Tester API is running. Endpoints: /plan, /rank, /execute, /analyze, /report/{run_id}"
    }


@app.post("/plan", response_model=PlanResponse)
async def plan(request: PlanRequest):
    logger.info("📋 Plan request received for: %s", request.target_url)

    if PlannerAgent is None:
        candidates = [
            {
                "id": f"cand_{i+1}",
                "description": f"Placeholder test #{i+1}",
                "steps": ["Step 1", "Step 2"],
                "expected_result": "N/A",
            }
            for i in range(request.n_candidates or 20)
        ]
    else:
        try:
            planner = PlannerAgent()
            candidates = await planner.generate(
                request.target_url, seeds=request.seeds, n=request.n_candidates
            )
        except Exception as e:
            logger.error("❌ PlannerAgent failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return {"candidates": candidates}


@app.post("/rank", response_model=RankResponse)
async def rank(request: RankRequest):
    logger.info("📊 Ranking %d candidates (top %d)", len(request.candidates), request.top_k)
    if RankerAgent is None:
        top = request.candidates[: request.top_k]
    else:
        try:
            ranker = RankerAgent()
            top = await ranker.rank_and_select(request.candidates, top_k=request.top_k)
        except Exception as e:
            logger.error("❌ RankerAgent failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"top_candidates": top}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    run_id = f"run_{os.urandom(4).hex()}"
    logger.info("🚀 Executing %d tests (parallelism=%s) run_id=%s",
                len(request.tests), request.parallelism, run_id)

    if OrchestratorAgent is None:
        results = [
            {
                "test_id": t.get("id"),
                "status": "completed",
                "verdict": "unknown",
                "artifacts": {
                    "screenshots": [],
                    "dom_snapshot": None,
                    "console_logs": [],
                    "network_log": None,
                },
            }
            for t in request.tests
        ]
    else:
        try:
            orchestrator = OrchestratorAgent()
            results = await orchestrator.execute_tests(
                run_id, request.tests, parallelism=request.parallelism
            )
        except Exception as e:
            logger.error("❌ OrchestratorAgent failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    os.makedirs("reports", exist_ok=True)
    raw_path = f"reports/{run_id}_raw.json"
    import json
    with open(raw_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    return {"run_id": run_id, "results": results}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    logger.info("🔎 Analyzing run %s with %d results",
                request.run_id, len(request.results))

    if AnalyzerAgent is None:
        report = {
            "run_id": request.run_id,
            "summary": {
                "total": len(request.results),
                "passed": 0,
                "failed": 0,
                "flaky": len(request.results),
            },
            "tests": [
                {
                    "test_id": r.get("test_id"),
                    "verdict": "flaky",
                    "artifacts": r.get("artifacts", {}),
                    "notes": "Placeholder analysis. Implement AnalyzerAgent for real validation.",
                }
                for r in request.results
            ],
        }
        report_path = f"reports/{request.run_id}_report.json"
        os.makedirs("reports", exist_ok=True)
        import json
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    else:
        try:
            analyzer = AnalyzerAgent()
            report_path, report = await analyzer.analyze_and_write_report(
                request.run_id, request.results
            )
        except Exception as e:
            logger.error("❌ AnalyzerAgent failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return {"report_path": report_path, "report": report}


@app.get("/report/{run_id}")
async def get_report(run_id: str):
    path = f"reports/{run_id}_report.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    import json
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
