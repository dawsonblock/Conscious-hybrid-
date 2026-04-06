"""Missing information detector for the workspace."""

from typing import List, Dict, Any, Optional
from hca.common.types import WorkspaceItem

def detect_missing_information(items: List[WorkspaceItem]) -> List[str]:
    """Identify items in the workspace that are missing required information."""
    missing = []
    
    # Check action suggestions for required args
    actions = [i for i in items if i.kind == "action_suggestion"]
    for action in actions:
        kind = action.content.get("action")
        args = action.content.get("args", {})
        
        # Simple schema-based check
        if kind == "store_note" and not args.get("note"):
            missing.append(action.item_id)
            
    return missing
