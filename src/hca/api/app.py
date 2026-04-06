"""FastAPI application exposing runtime operations."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from hca.runtime.runtime import Runtime
from hca.runtime.replay import reconstruct_state
from hca.storage.event_log import iter_events
from hca.storage.approvals import get_pending_requests, append_grant, append_denial

app = FastAPI(title="Hybrid Cognitive Agent API")
runtime_engine = Runtime()

class RunRequest(BaseModel):
    goal: str
    user_id: Optional[str] = None

class RunResponse(BaseModel):
    run_id: str

class ApprovalDecisionRequest(BaseModel):
    decision: str # "grant" or "deny"
    token: Optional[str] = None
    reason: Optional[str] = None

@app.post("/runs", response_model=RunResponse)
def create_run(req: RunRequest) -> RunResponse:
    run_id = runtime_engine.run(req.goal, req.user_id)
    return RunResponse(run_id=run_id)

@app.get("/runs/{run_id}/state")
def get_run_state(run_id: str):
    try:
        return reconstruct_state(run_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/runs/{run_id}/events", response_model=List[Dict[str, Any]])
def get_events(run_id: str) -> List[Dict[str, Any]]:
    return [e.model_dump(mode="json") for e in iter_events(run_id)]

@app.get("/runs/{run_id}/approvals/pending", response_model=List[Dict[str, Any]])
def get_pending_approvals(run_id: str):
    pending = get_pending_requests(run_id)
    return [p.model_dump(mode="json") for p in pending]

@app.post("/runs/{run_id}/approvals/{approval_id}/decide")
def decide_approval(run_id: str, approval_id: str, req: ApprovalDecisionRequest):
    if req.decision == "grant":
        from hca.common.types import ApprovalGrant
        grant = ApprovalGrant(approval_id=approval_id, status="granted", token=req.token or "default-token")
        append_grant(run_id, grant)
        # Attempt to resume
        try:
            runtime_engine.resume(run_id, approval_id, grant.token)
        except Exception:
            pass
        return {"status": "granted"}
    elif req.decision == "deny":
        append_denial(run_id, approval_id, reason=req.reason or "User denied via API")
        # Attempt to resume (which will handle the denial)
        try:
            runtime_engine.resume(run_id, approval_id, "no-token")
        except Exception:
            pass
        return {"status": "denied"}
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")

@app.get("/memory/search")
def search_memory(run_id: str, query: str, limit: int = 5):
    from hca.memory.retrieval import retrieve
    results = retrieve(run_id, query, limit)
    return [r.model_dump(mode="json") for r in results]
