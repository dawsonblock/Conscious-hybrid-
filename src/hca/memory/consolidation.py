"""Memory consolidation logic for migrating episodic to semantic/procedural memory."""

from typing import List, Dict, Any
from hca.common.types import MemoryRecord
from hca.common.enums import MemoryType
from hca.memory.episodic_store import EpisodicStore
from hca.memory.semantic_store import SemanticStore

def consolidate_episodic(run_id: str, count_threshold: int = 5) -> int:
    """Consolidate frequent episodic memories into semantic memory."""
    episodic = EpisodicStore(run_id)
    semantic = SemanticStore(run_id)
    
    # Group by subject
    counts: Dict[str, List[MemoryRecord]] = {}
    for rec in episodic.iter_records():
        if rec.subject:
            if rec.subject not in counts:
                counts[rec.subject] = []
            counts[rec.subject].append(rec)
            
    consolidated = 0
    for subject, recs in counts.items():
        if len(recs) >= count_threshold:
            # Simple consolidation: Take the latest record and make it semantic
            latest = sorted(recs, key=lambda x: x.created_at)[-1]
            semantic_rec = MemoryRecord(
                run_id=run_id,
                memory_type=MemoryType.semantic,
                subject=subject,
                content=latest.content,
                confidence=0.9 # High confidence after multiple occurrences
            )
            semantic.write(semantic_rec)
            consolidated += 1
            
    return consolidated

def propose_consolidation(record: MemoryRecord) -> None:
    """Legacy stub for proposing consolidation."""
    return None
