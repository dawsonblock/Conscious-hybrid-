"""Metacognition evaluation harness."""

from typing import List, Dict, Any
from hca.common.types import WorkspaceItem, MemoryRecord
from hca.common.enums import MemoryType, ControlSignal
from hca.meta.monitor import assess

def evaluate_metacognition(run_id: str) -> dict:
    """Evaluate the metacognitive performance of a specific run (stub)."""
    return {"run_id": run_id, "accuracy": 1.0}

def run_metacognition_harness() -> Dict[str, Any]:
    """Test the meta-monitor's ability to detect various workspace anomalies."""
    
    test_cases = [
        {
            "name": "No anomalies",
            "items": [WorkspaceItem(source_module="test", kind="perception", content={"goal": "hello"})],
            "expected_signal": ControlSignal.proceed
        },
        {
            "name": "Contradiction",
            "items": [WorkspaceItem(
                source_module="test", 
                kind="memory_retrieval", 
                content=[MemoryRecord(run_id="test", memory_type=MemoryType.episodic, subject="test", content="test", contradiction_status=True)]
            )],
            "expected_signal": ControlSignal.replan
        },
        {
            "name": "Missing Info",
            "items": [WorkspaceItem(
                source_module="test", 
                kind="action_suggestion", 
                content={"action": "store_note", "args": {}}
            )],
            "expected_signal": ControlSignal.ask_user
        }
    ]
    
    results = []
    for case in test_cases:
        assessment = assess(case["items"])
        passed = assessment.recommended_transition == case["expected_signal"]
        results.append({
            "case": case["name"],
            "passed": passed,
            "signal": assessment.recommended_transition,
            "explanation": assessment.explanation
        })
        
    passed_count = len([r for r in results if r["passed"]])
    return {
        "accuracy": passed_count / len(test_cases),
        "results": results
    }

def run() -> dict:
    """Entry point for CLI."""
    return run_metacognition_harness()
