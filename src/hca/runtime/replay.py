"""Richer state reconstruction from event logs and snapshots."""

from typing import Dict, Any, List, Optional
from hca.storage.event_log import iter_events
from hca.storage.snapshots import load_latest_snapshot
from hca.storage.approvals import resolve_status, get_latest_decision, get_grant, get_consumption, iter_records
from hca.common.enums import EventType, RuntimeState

def reconstruct_state(run_id: str) -> Dict[str, Any]:
    """Reconstruct the run state by replaying events and optionally using snapshots."""
    events = list(iter_events(run_id))
    snapshot = load_latest_snapshot(run_id)
    
    state = {
        "run_id": run_id,
        "state": RuntimeState.created.value,
        "transition_history": [],
        "selected_action": None,
        "workspace_summary": {"item_count": 0, "kinds": {}},
        "pending_approval_id": None,
        "latest_receipt_id": None,
        "artifacts_count": 0,
        "memory_counts": {"episodic": 0, "semantic": 0, "procedural": 0, "identity": 0},
        "event_count": len(events),
        "meta_signals_seen": [],
        "discrepancies": [],
        "approval": None
    }

    # 1. Replay events
    for event in events:
        etype = event.get("event_type")
        payload = event.get("payload", {})
        
        if etype == EventType.state_transition.value:
            next_state = event.get("next_state")
            if next_state:
                state["state"] = next_state
                state["transition_history"].append(next_state)
        
        elif etype == EventType.action_selected.value:
            state["selected_action"] = payload
            state["pending_approval_id"] = None
            
        elif etype == EventType.approval_requested.value:
            state["pending_approval_id"] = payload.get("approval_id")
            
        elif etype == EventType.execution_finished.value:
            state["latest_receipt_id"] = payload.get("receipt_id")
            state["pending_approval_id"] = None
            artifacts = payload.get("artifacts", [])
            state["artifacts_count"] += len(artifacts)
            
        elif etype == EventType.meta_assessed.value:
            signal = payload.get("recommended_transition")
            if signal:
                state["meta_signals_seen"].append(signal)
                
        elif etype == EventType.memory_written.value:
            mtype = payload.get("memory_type")
            if mtype in state["memory_counts"]:
                state["memory_counts"][mtype] += 1

    # 2. Approval Summary
    # Find all approval IDs mentioned in events or storage
    approval_ids = set()
    if state["pending_approval_id"]:
        approval_ids.add(state["pending_approval_id"])
    
    for event in events:
        if event.get("event_type") == EventType.approval_requested.value:
            aid = event.get("payload", {}).get("approval_id")
            if aid:
                approval_ids.add(aid)
                
    # Also check storage records
    for record in iter_records(run_id):
        aid = record.get("approval_id")
        if aid:
            approval_ids.add(aid)
            
    if approval_ids:
        # Pick the most relevant one (latest if possible, or pending)
        # For simplicity, pick any if multiple exist for now
        target_aid = state["pending_approval_id"] or sorted(list(approval_ids))[-1]
        status = resolve_status(run_id, target_aid)
        decision = get_latest_decision(run_id, target_aid)
        state["approval"] = {
            "approval_id": target_aid,
            "status": status,
            "decision": decision.model_dump(mode="json") if decision else None
        }

    # 3. Snapshot Discrepancy Check
    if snapshot:
        snap_state = snapshot.get("state")
        if snap_state and snap_state != state["state"]:
            state["discrepancies"].append(f"State mismatch: event={state['state']}, snapshot={snap_state}")
            
        snap_mem = snapshot.get("memory_summary", {})
        for k, v in snap_mem.items():
            if state["memory_counts"].get(k) != v:
                state["discrepancies"].append(f"Memory mismatch ({k}): event={state['memory_counts'].get(k)}, snapshot={v}")

    return state
