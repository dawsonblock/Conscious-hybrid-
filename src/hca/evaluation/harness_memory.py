"""Memory evaluation harness."""

from typing import Dict, Any
from hca.common.types import MemoryRecord
from hca.common.enums import MemoryType
from hca.memory.episodic_store import EpisodicStore
from hca.memory.retrieval import retrieve

def run_memory_harness() -> Dict[str, Any]:
    """Test memory retrieval and contradiction detection."""
    run_id = "test_memory_harness"
    store = EpisodicStore(run_id)
    
    # 1. Store a record
    record = MemoryRecord(run_id=run_id, memory_type=MemoryType.episodic, subject="keys", content="kitchen")
    store.add(record)
    
    # 2. Retrieve it
    results = retrieve(run_id, "keys")
    retrieval_passed = len(results) > 0 and results[0].content == "kitchen"
    
    # 3. Add a contradictory record
    contradictory = MemoryRecord(run_id=run_id, memory_type=MemoryType.episodic, subject="keys", content="car")
    store.add(contradictory)
    
    # 4. Retrieve again and check for contradiction flag
    results = retrieve(run_id, "keys")
    contradiction_passed = any(r.contradiction_status for r in results)
    
    return {
        "retrieval_passed": retrieval_passed,
        "contradiction_passed": contradiction_passed,
        "overall": retrieval_passed and contradiction_passed
    }

def run() -> dict:
    """Entry point for CLI."""
    return run_memory_harness()
