"""Simple planner module for proposing strategies."""

from typing import List, Union
from hca.common.types import ModuleProposal, WorkspaceItem

class Planner:
    name = "planner"

    def update(self, items: List[WorkspaceItem]) -> None:
        """Update internal state based on workspace content."""
        pass

    def propose(self, input_data: Union[str, List[WorkspaceItem]]) -> ModuleProposal:
        """Build a small plan from actual intent or broadcast items."""
        
        # 1. Handle string input (run_id or goal) or list input (broadcast)
        current_items = input_data if isinstance(input_data, list) else []
        
        # 2. Look for perceived intent in broadcast
        perceived_intent = None
        for item in current_items:
            if item.kind == "perceived_intent":
                perceived_intent = item.content.get("intent")
                break
        
        # 3. Formulate strategy based on intent
        strategy = "single_action_dispatch"
        if perceived_intent == "store":
            strategy = "memory_persistence_strategy"
        elif perceived_intent == "retrieve":
            strategy = "information_retrieval_strategy"
            
        item = WorkspaceItem(
            source_module=self.name,
            kind="task_plan",
            content={"strategy": strategy, "perceived_intent": perceived_intent},
            salience=0.6,
            confidence=1.0
        )
        
        return ModuleProposal(
            source_module=self.name,
            candidate_items=[item],
            rationale=f"Plan to dispatch action with strategy: {strategy}.",
            confidence=1.0
        )
