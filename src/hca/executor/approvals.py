"""Centralized approval validation for execution."""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from hca.common.time import utc_now
from hca.storage.approvals import resolve_status, get_grant, get_consumption, is_expired

def require_approval(action_class: str) -> bool:
    """Determine if an action class requires approval."""
    return action_class in {"medium", "high"}

def validate_resume_approval(run_id: str, approval_id: str, token: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Validate if an approval is valid for resumption."""
    now = now or utc_now()
    status = resolve_status(run_id, approval_id, now)
    
    result = {
        "ok": False,
        "reason": None,
        "status": status
    }
    
    if status == "missing":
        result["reason"] = "missing_approval"
    elif status == "denied":
        result["reason"] = "denied_approval"
    elif status == "expired":
        result["reason"] = "expired_approval"
    elif status == "consumed":
        result["reason"] = "already_consumed"
    elif status == "pending":
        result["reason"] = "not_yet_granted"
    elif status == "granted":
        grant = get_grant(run_id, approval_id)
        if not grant:
            result["reason"] = "grant_record_missing"
        elif grant.token != token:
            result["reason"] = "token_mismatch"
        else:
            result["ok"] = True
    
    return result
