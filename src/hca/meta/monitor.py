"""Meta monitoring component for assessing workspace state."""

from typing import List, Optional
from hca.common.types import WorkspaceItem, MetaAssessment, MemoryRecord
from hca.common.enums import ControlSignal

def assess(workspace_items: List[WorkspaceItem]) -> MetaAssessment:
    """Inspect the workspace and return a meta assessment."""
    
    contradictions = []
    missing = []
    self_limits = []
    signal = ControlSignal.proceed
    explanation = "No anomalies detected. Proceeding."
    confidence = 1.0
    
    # 1. Detect contradictions in action suggestions
    actions = [item for item in workspace_items if item.kind == "action_suggestion"]
    if len(actions) > 1:
        action_names = {a.content.get("action") for a in actions}
        if len(action_names) > 1:
            contradictions.append(f"Conflicting action suggestions: {list(action_names)}")

    # 2. Detect contradictory or stale memory retrieval
    memory_items = [item for item in workspace_items if item.kind == "memory_retrieval"]
    for item in memory_items:
        records = item.content if isinstance(item.content, list) else []
        for rec in records:
            if isinstance(rec, dict):
                is_contradictory = rec.get("contradiction_status", False)
                staleness = rec.get("staleness", 0.0)
                subject = rec.get("subject", "unknown")
            elif isinstance(rec, MemoryRecord):
                is_contradictory = rec.contradiction_status
                staleness = rec.staleness
                subject = rec.subject
            else:
                continue

            if is_contradictory:
                contradictions.append(f"Contradictory memory for subject: {subject}")
            if staleness > 0.8:
                self_limits.append(f"Stale memory detected (staleness={staleness:.2f})")

    # 3. Detect missing required action inputs
    for action in actions:
        kind = action.content.get("action")
        args = action.content.get("args", {})
        if kind == "store_note" and not args.get("note"):
            missing.append("Missing 'note' for store_note action")
            
    # 4. Detect no-actionable workspace state
    if not actions and not memory_items:
        self_limits.append("No actionable items in workspace")

    # 5. Determine control signal and confidence
    if contradictions:
        signal = ControlSignal.replan
        explanation = f"Contradictions detected in workspace: {', '.join(contradictions)}"
        confidence = 0.5
    elif missing:
        signal = ControlSignal.ask_user
        explanation = f"Missing required information: {', '.join(missing)}"
        confidence = 0.7
    elif self_limits:
        if "No actionable items" in self_limits[0]:
            signal = ControlSignal.replan
            explanation = "No actionable items in workspace. Attempting replan/retrieval."
        else:
            signal = ControlSignal.ask_user
            explanation = f"Self-limitations detected: {', '.join(self_limits)}"
        confidence = 0.6
    else:
        signal = ControlSignal.proceed
        explanation = "No anomalies detected. Proceeding."
        confidence = 0.9

    return MetaAssessment(
        overall_confidence=confidence,
        contradiction_flags=contradictions,
        missing_information=missing,
        self_limitations=self_limits,
        recommended_transition=signal,
        explanation=explanation,
    )
