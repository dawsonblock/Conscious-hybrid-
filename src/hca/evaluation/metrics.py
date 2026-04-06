"""Metrics calculation for agent evaluation."""

from typing import List, Dict, Any
from hca.common.enums import EventType, RuntimeState, ControlSignal

def calculate_success_rate(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    completed = [r for r in runs if r.get("state") == RuntimeState.completed.value]
    return len(completed) / len(runs)

def calculate_metacognitive_accuracy(events: List[Dict[str, Any]]) -> float:
    """Assess how often the meta-monitor correctly flagged issues."""
    
    assessments = [e for e in events if e.get("event_type") == EventType.meta_assessed.value]
    if not assessments:
        return 1.0
        
    correct_detections = 0
    for a in assessments:
        payload = a.get("data", a.get("payload", {})) # v5 uses 'data'
        signal = payload.get("recommended_transition")
        has_anomalies = bool(payload.get("contradiction_flags") or payload.get("missing_information") or payload.get("self_limitations"))
        
        if has_anomalies and signal != ControlSignal.proceed.value:
            correct_detections += 1
        elif not has_anomalies and signal == ControlSignal.proceed.value:
            correct_detections += 1
            
    return correct_detections / len(assessments)

def calculate_tool_efficiency(receipts: List[Dict[str, Any]]) -> float:
    """Ratio of successful tool executions."""
    if not receipts:
        return 1.0
    successes = [r for r in receipts if r.get("status") == "success"]
    return len(successes) / len(receipts)

def compute_metrics(result: dict) -> dict:
    """Compute metrics for a given run result."""
    events = result.get("events", [])
    receipts = [e.get("data", e.get("payload")) for e in events if e.get("event_type") == EventType.execution_finished.value]
    
    return {
        "success_rate": 1.0 if result.get("state") == RuntimeState.completed.value else 0.0,
        "tool_efficiency": calculate_tool_efficiency(receipts),
        "metacognitive_accuracy": calculate_metacognitive_accuracy(events)
    }
