"""Storage for approval requests, decisions, and consumption records."""

import json
import os
from pathlib import Path
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime

from hca.common.types import (
    ApprovalRequest, 
    ApprovalDecisionRecord, 
    ApprovalGrant, 
    ApprovalConsumption
)
from hca.common.enums import ApprovalDecision
from hca.common.time import utc_now

def _path(run_id: str) -> Path:
    """Unified path for approval records."""
    return Path(f"storage/runs/{run_id}/approvals.jsonl")

def append_request(run_id: str, request: ApprovalRequest) -> None:
    path = _path(run_id)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"record_type": "request", **request.model_dump(mode="json")}) + "\n")

def append_decision(run_id: str, decision: ApprovalDecisionRecord) -> None:
    path = _path(run_id)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"record_type": "decision", **decision.model_dump(mode="json")}) + "\n")

def append_grant(run_id: str, grant: ApprovalGrant) -> None:
    path = _path(run_id)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"record_type": "grant", **grant.model_dump(mode="json")}) + "\n")

def append_consumption(run_id: str, consumption: ApprovalConsumption) -> None:
    path = _path(run_id)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"record_type": "consumption", **consumption.model_dump(mode="json")}) + "\n")

def iter_records(run_id: str) -> Iterator[Dict[str, Any]]:
    path = _path(run_id)
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def get_request(run_id: str, approval_id: str) -> Optional[ApprovalRequest]:
    for record in iter_records(run_id):
        if record.get("record_type") == "request" and record.get("approval_id") == approval_id:
            return ApprovalRequest.model_validate(record)
    return None

def get_latest_decision(run_id: str, approval_id: str) -> Optional[ApprovalDecisionRecord]:
    latest = None
    for record in iter_records(run_id):
        if record.get("record_type") == "decision" and record.get("approval_id") == approval_id:
            latest = ApprovalDecisionRecord.model_validate(record)
    return latest

def get_grant(run_id: str, approval_id: str) -> Optional[ApprovalGrant]:
    latest = None
    for record in iter_records(run_id):
        if record.get("record_type") == "grant" and record.get("approval_id") == approval_id:
            latest = ApprovalGrant.model_validate(record)
    return latest

def get_consumption(run_id: str, approval_id: str) -> Optional[ApprovalConsumption]:
    for record in iter_records(run_id):
        if record.get("record_type") == "consumption" and record.get("approval_id") == approval_id:
            return ApprovalConsumption.model_validate(record)
    return None

def is_expired(record: Any, now: Optional[datetime] = None) -> bool:
    if not hasattr(record, "expires_at") or record.expires_at is None:
        return False
    now = now or utc_now()
    return now > record.expires_at

def resolve_status(run_id: str, approval_id: str, now: Optional[datetime] = None) -> str:
    """Resolve approval status: missing, pending, granted, denied, expired, consumed."""
    now = now or utc_now()
    
    dec = get_latest_decision(run_id, approval_id)
    req = get_request(run_id, approval_id)
    
    # Even if request is missing, a decision record might exist (e.g. ad-hoc denial)
    if not req and not dec:
        return "missing"
    
    if req and is_expired(req, now):
        return "expired"
        
    if not dec:
        return "pending"
        
    if dec.decision == ApprovalDecision.denied:
        return "denied"
        
    if dec.decision == ApprovalDecision.granted:
        grant = get_grant(run_id, approval_id)
        if not grant:
            return "granted"
            
        if is_expired(grant, now):
            return "expired"
            
        if get_consumption(run_id, approval_id):
            return "consumed"
            
        return "granted"
        
    return "pending"

def get_pending_requests(run_id: str) -> List[ApprovalRequest]:
    pending = []
    seen_ids = set()
    for record in iter_records(run_id):
        if record.get("record_type") == "request":
            aid = record.get("approval_id")
            if aid not in seen_ids:
                status = resolve_status(run_id, aid)
                if status == "pending":
                    pending.append(ApprovalRequest.model_validate(record))
                seen_ids.add(aid)
    return pending
