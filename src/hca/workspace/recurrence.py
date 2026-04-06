"""Bounded recurrence for the global workspace."""

from typing import List, Optional, Any
from hca.workspace.workspace import Workspace
from hca.common.types import WorkspaceItem, RunContext
from hca.storage.event_log import append_event
from hca.common.enums import EventType

def run_recurrence(workspace: Workspace, context: Optional[RunContext] = None, depth: int = 1) -> None:
    """Perform a bounded recurrent update where modules can revise proposals."""
    
    # 1. Get modules
    from hca.modules.planner import Planner
    from hca.modules.critic import Critic
    from hca.modules.tool_reasoner import ToolReasoner
    
    modules = [Planner(), Critic(), ToolReasoner()]
    
    for d in range(depth):
        # 2. Broadcast current workspace items
        current_items = workspace.broadcast()
        
        # 3. Allow modules to propose revisions or new items based on broadcast
        new_candidates: List[WorkspaceItem] = []
        for module in modules:
            try:
                # Some modules might expect run_id, some might expect items
                # Let's try to pass items if it supports it
                if hasattr(module, "propose"):
                    # Check signature or just try
                    try:
                        proposal = module.propose(current_items)
                    except TypeError:
                        proposal = module.propose(context.run_id if context else "unknown")
                        
                    if proposal and proposal.candidate_items:
                        for item in proposal.candidate_items:
                            item.provenance.append(f"recurrence_depth_{d}")
                        new_candidates.extend(proposal.candidate_items)
            except Exception:
                pass
        
        # 4. Attempt to admit new candidates
        if new_candidates:
            workspace.admit(new_candidates)

        # 5. Resolution: Resolve action contradictions by keeping the highest confidence
        actions = [item for item in workspace.items if item.kind == "action_suggestion"]
        if len(actions) > 1:
            actions.sort(key=lambda x: x.confidence, reverse=True)
            to_keep = actions[0]
            
            # Keep only the best action suggestion
            new_items = []
            seen_action = False
            for item in workspace.items:
                if item.kind == "action_suggestion":
                    if item.item_id == to_keep.item_id and not seen_action:
                        new_items.append(item)
                        seen_action = True
                else:
                    new_items.append(item)
            workspace.items = new_items
            
            if context:
                append_event(context, EventType.workspace_evicted, "recurrence", {"reason": "Resolved action contradiction via confidence"})
