"""Tool reasoning module for proposing action candidates."""

from typing import List, Union
from hca.common.types import ModuleProposal, WorkspaceItem
from hca.storage import load_run

class ToolReasoner:
    name = "tool_reasoner"

    def update(self, items: List[WorkspaceItem]) -> None:
        """Update internal state based on workspace content."""
        pass

    def propose(self, input_data: Union[str, List[WorkspaceItem]]) -> ModuleProposal:
        """Select tools based on intent and plan strategy."""
        
        current_items = input_data if isinstance(input_data, list) else []
        
        # 1. Look for plan and intent in broadcast
        strategy = None
        intent_class = None
        args = {}
        for item in current_items:
            if item.kind == "task_plan":
                strategy = item.content.get("strategy")
            elif item.kind == "perceived_intent":
                intent_class = item.content.get("intent_class")
                args = item.content.get("arguments", {})
        
        # 2. If no broadcast info, we're in first pass - use raw goal
        if not intent_class and isinstance(input_data, str):
            run = load_run(input_data)
            goal = run.goal if run else ""
            goal_lower = goal.lower()
            if "note" in goal_lower or "remember" in goal_lower:
                intent_class = "store_note"
                args = {"note": goal}
            else:
                intent_class = "general"
                args = {"text": goal}

        # 3. Select action based on intent_class and strategy
        action = "echo"
        final_args = {}
        
        if intent_class == "store_note":
            action = "store_note"
            final_args = {"note": args.get("text", args.get("note", ""))}
        elif intent_class == "retrieve_memory":
            action = "echo" # For now, retrieval is internal, but we can echo the intent
            final_args = {"text": f"Searching for: {args.get('query')}"}
        elif intent_class == "write_artifact":
            action = "write_artifact"
            final_args = args
        else:
            action = "echo"
            final_args = {"text": args.get("text", "hello")}

        # 4. If we have a strategy, we can refine the confidence
        confidence = 1.0
        if strategy == "single_action_dispatch":
            confidence = 1.0
        elif strategy is None:
            confidence = 0.8 # Less confident if no plan yet
            
        item = WorkspaceItem(
            source_module=self.name,
            kind="action_suggestion",
            content={"action": action, "args": final_args},
            salience=0.9,
            confidence=confidence
        )
        
        return ModuleProposal(
            source_module=self.name,
            candidate_items=[item],
            rationale=f"Selected {action} with confidence {confidence} based on strategy {strategy}.",
            confidence=confidence
        )
