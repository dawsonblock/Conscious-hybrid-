"""Critic module for validating proposals."""

from typing import List, Union
from hca.common.types import ModuleProposal, WorkspaceItem
from hca.executor.tool_registry import get_tool

class Critic:
    name = "critic"

    def update(self, items: List[WorkspaceItem]) -> None:
        """Update internal state based on workspace content."""
        pass

    def propose(self, input_data: Union[str, List[WorkspaceItem]]) -> ModuleProposal:
        """Validate action candidates in workspace."""
        
        current_items = input_data if isinstance(input_data, list) else []
        critiques = []
        
        # Look for action_suggestion items in broadcast
        for item in current_items:
            if item.kind == "action_suggestion":
                action = item.content.get("action")
                args = item.content.get("args", {})
                
                # 1. Validate tool name
                try:
                    get_tool(action)
                except (ValueError, KeyError):
                    critiques.append(f"Unknown tool: {action}")
                    continue
                
                # 2. Validate required fields
                if action == "store_note" and "note" not in args:
                    critiques.append("Missing required argument 'note' for store_note")
                elif action == "write_artifact" and ("content" not in args or "path" not in args):
                    critiques.append("Missing 'content' or 'path' for write_artifact")
                elif action == "echo" and "text" not in args:
                    critiques.append("Missing 'text' for echo")
        
        if not critiques and current_items:
            critiques = ["No obvious issues detected in proposed actions."]
            
        if not current_items:
            return ModuleProposal(source_module=self.name, candidate_items=[], rationale="No items to critique.")

        item = WorkspaceItem(
            source_module=self.name,
            kind="action_critique",
            content={"critiques": critiques},
            salience=0.7,
            confidence=1.0
        )
        
        return ModuleProposal(
            source_module=self.name,
            candidate_items=[item],
            rationale="Validated action candidates against tool registry.",
            confidence=1.0
        )
