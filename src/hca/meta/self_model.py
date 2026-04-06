"""Runtime self-model tracking agent limitations and capabilities."""

from typing import List, Dict, Any, Optional
from hca.common.types import WorkspaceItem

def describe_capabilities() -> str:
    """Return a human-readable description of current capabilities."""
    return "This MVP agent can echo messages and store notes."

def check_self_limitations(items: List[WorkspaceItem]) -> List[str]:
    """Identify if the current workspace task exceeds the agent's known capabilities."""
    limits = []
    
    # Check for complex tasks that aren't supported
    actions = [i for i in items if i.kind == "action_suggestion"]
    for action in actions:
        kind = action.content.get("action")
        # Agent can't do complex math or external API calls for now
        if kind in ("calculate", "api_call"):
            limits.append(f"Action '{kind}' is beyond current capabilities.")
            
    # Check for empty workspace
    if not items:
        limits.append("No items in workspace to process.")
        
    return limits
