"""Conflict detector for identifying overlaps and disagreements in the workspace."""

from typing import List, Dict, Any, Optional
from hca.common.types import WorkspaceItem

def detect_conflicts(items: List[WorkspaceItem]) -> List[str]:
    """Return list of item IDs that conflict."""
    conflicts = []
    
    # 1. Action conflicts
    actions = [i for i in items if i.kind == "action_suggestion"]
    if len(actions) > 1:
        # Check for multiple actions targeting same goal
        action_kinds = [a.content.get("action") for a in actions]
        if len(set(action_kinds)) > 1:
            conflicts.extend([a.item_id for a in actions])
            
    # 2. Memory conflicts
    contradictions = [i for i in items if i.contradiction_status]
    if contradictions:
        conflicts.extend([i.item_id for i in contradictions])
        
    return sorted(list(set(conflicts)))
