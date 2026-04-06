"""Global Workspace for the hybrid cognitive agent."""

from __future__ import annotations
from typing import List, Tuple, Dict, Any
from hca.workspace.ranking import score_item
from hca.common.types import WorkspaceItem
from hca.common.time import utc_now

class Workspace:
    """A small, capacity-limited workspace for active items."""

    def __init__(self, capacity: int = 7) -> None:
        self.capacity = capacity
        self.items: List[WorkspaceItem] = []

    def admit(self, candidates: List[WorkspaceItem]) -> Tuple[List[WorkspaceItem], List[WorkspaceItem], List[WorkspaceItem]]:
        """Attempt to admit candidate items into the workspace.
        Returns a tuple of (accepted, rejected, evicted).
        """
        accepted: List[WorkspaceItem] = []
        rejected: List[WorkspaceItem] = []
        evicted: List[WorkspaceItem] = []

        # Score candidates
        scored = [(item, score_item(item)) for item in candidates]
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for item, score in scored:
            item.score = score
            if len(self.items) < self.capacity:
                item.admitted_at = item.admitted_at or utc_now()
                self.items.append(item)
                accepted.append(item)
            else:
                # Check if item is better than the worst current item
                # We need to re-score current items as scores might be dynamic
                current_with_scores = [(i, score_item(i)) for i in self.items]
                worst_item, worst_score = min(current_with_scores, key=lambda x: x[1])
                
                if score > worst_score:
                    # Evict the worst and accept the new item
                    self.items.remove(worst_item)
                    evicted.append(worst_item)
                    item.admitted_at = item.admitted_at or utc_now()
                    self.items.append(item)
                    accepted.append(item)
                else:
                    rejected.append(item)
                    
        return accepted, rejected, evicted

    def broadcast(self) -> List[WorkspaceItem]:
        """Return current items for broadcasting to modules."""
        return list(self.items)

    def summary(self) -> Dict[str, Any]:
        """Summarize the current workspace state."""
        counts = {}
        for item in self.items:
            counts[item.kind] = counts.get(item.kind, 0) + 1
            
        return {
            "item_count": len(self.items),
            "kinds": counts,
            "top_score": max([score_item(i) for i in self.items]) if self.items else 0.0
        }
