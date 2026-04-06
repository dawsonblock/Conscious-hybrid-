"""Broadcast workspace content to all registered modules."""

from typing import List, Any
from hca.workspace.workspace import Workspace
from hca.common.types import WorkspaceItem

def broadcast(workspace: Workspace, subscribers: List[Any]) -> None:
    """Broadcast current workspace items to subscriber modules.
    This allows modules to update their internal state based on workspace content.
    """
    items = workspace.broadcast()
    for sub in subscribers:
        # Check for both update and on_broadcast for compatibility
        callback = getattr(sub, "on_broadcast", getattr(sub, "update", None))
        if callable(callback):
            callback(items)
