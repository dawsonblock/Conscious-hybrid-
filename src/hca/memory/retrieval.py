"""Memory retrieval logic with staleness and contradiction scoring."""

from typing import List, Dict, Any, Optional
from hca.common.types import MemoryRecord
from hca.common.time import utc_now
from hca.memory.episodic_store import EpisodicStore
from hca.memory.semantic_store import SemanticStore
from hca.memory.procedural_store import ProceduralStore
from hca.memory.identity_store import IdentityStore

def calculate_staleness(record: MemoryRecord) -> float:
    """Calculate staleness score (0.0 fresh to 1.0 very stale)."""
    now = utc_now()
    # Use updated_at if available, otherwise created_at
    ref_time = record.updated_at or record.created_at
    
    # Ensure both are offset-aware for subtraction
    if ref_time.tzinfo is None:
        from datetime import timezone
        ref_time = ref_time.replace(tzinfo=timezone.utc)
        
    age = now - ref_time
    age_days = age.total_seconds() / (24 * 3600)
    # Simple linear staleness up to 1.0 at 30 days
    return min(1.0, age_days / 30.0)

def check_contradictions(records: List[MemoryRecord]) -> List[MemoryRecord]:
    """Mark contradictions within a set of retrieved records for the same subject."""
    # Group by subject
    by_subject: Dict[str, List[MemoryRecord]] = {}
    for rec in records:
        if rec.subject:
            if rec.subject not in by_subject:
                by_subject[rec.subject] = []
            by_subject[rec.subject].append(rec)
    
    # Check for disagreements in content within each subject
    for subject, recs in by_subject.items():
        if len(recs) < 2:
            continue
        
        # Simple string-based disagreement for now
        base_content = str(recs[0].content)
        for i in range(1, len(recs)):
            if str(recs[i].content) != base_content:
                # Mark all records for this subject as contradictory
                for r in recs:
                    r.contradiction_status = True
                break
    return records

def retrieve(run_id: str, query: str, limit: int = 5) -> List[MemoryRecord]:
    """Retrieve memories relevant to a query with contradiction and staleness metadata."""
    results = []
    
    # Search all stores
    for store_cls in (EpisodicStore, SemanticStore, ProceduralStore, IdentityStore):
        store = store_cls(run_id)
        for record in store.iter_records():
            subject = (record.subject or "").lower()
            content = str(record.content or "").lower()
            query_lower = (query or "").lower()
            
            if query_lower in subject or query_lower in content:
                record.staleness = calculate_staleness(record)
                results.append(record)
            
    # Mark contradictions
    results = check_contradictions(results)
            
    # Sort by confidence and recency (lower staleness), then limit
    results.sort(key=lambda x: (x.confidence, -x.staleness), reverse=True)
    return results[:limit]

def retrieve_all(run_id: str, subject: str) -> List[MemoryRecord]:
    """Retrieve records across all memory stores by subject."""
    records: List[MemoryRecord] = []
    for store_cls in (EpisodicStore, SemanticStore, ProceduralStore, IdentityStore):
        store = store_cls(run_id)
        records.extend(store.retrieve_by_subject(subject))
    
    for r in records:
        r.staleness = calculate_staleness(r)
    
    return check_contradictions(records)
