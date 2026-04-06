"""Runtime orchestrator for the hybrid cognitive agent."""

from __future__ import annotations

import os
import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from hca.common.types import (
    RunContext, 
    WorkspaceItem, 
    ModuleProposal, 
    ActionCandidate, 
    ExecutionReceipt, 
    MemoryRecord,
    ApprovalRequest,
    ApprovalGrant,
    ApprovalDecisionRecord,
    ApprovalConsumption
)
from hca.common.enums import (
    RuntimeState,
    EventType,
    MemoryType,
    ActionClass,
    ApprovalDecision,
    ControlSignal,
    ReceiptStatus
)
from hca.common.time import utc_now
from hca.storage import (
    save_run,
    append_event,
    append_snapshot,
    append_artifact,
    append_receipt,
    load_run,
    append_request as append_approval_request,
    append_decision as append_approval_decision,
    append_grant as append_approval_grant,
    append_consumption as append_approval_consumption,
    resolve_status
)
from hca.modules import Planner, Critic, TextPerception, ToolReasoner
from hca.workspace.workspace import Workspace
from hca.workspace.broadcast import broadcast
from hca.workspace.recurrence import run_recurrence
from hca.meta.monitor import assess
from hca.prediction.action_scoring import score_actions
from hca.executor.executor import Executor
from hca.executor.approvals import validate_resume_approval
from hca.runtime.state_machine import assert_transition


class Runtime:
    def __init__(self, workspace_capacity: int = 7, replan_budget: int = 3) -> None:
        self.workspace_capacity = workspace_capacity
        self.replan_budget = replan_budget
        self._remaining_replan = replan_budget
        self.executor = Executor()
        self.modules = [Planner(), Critic(), TextPerception(), ToolReasoner()]
        self._current_state: RuntimeState = RuntimeState.created
        self._execution_failure_count = 0

    def _set_state(self, context: RunContext, target: RuntimeState, payload: Optional[Dict[str, Any]] = None) -> None:
        """Enforce transition and log event."""
        assert_transition(self._current_state, target)
        prior = self._current_state
        self._current_state = target
        append_event(
            context,
            EventType.state_transition,
            "runtime",
            payload or {"to": target.value},
            prior_state=prior,
            next_state=target
        )

    def create_run(self, goal: str, user_id: str | None = None) -> RunContext:
        context = RunContext(goal=goal, user_id=user_id)
        context.active_environment = "default"
        save_run(context)
        append_event(context, EventType.run_created, actor="runtime", payload={"goal": goal})
        return context

    def run(self, goal: str, user_id: str | None = None) -> str:
        context = self.create_run(goal, user_id)
        self._current_state = RuntimeState.created
        self._remaining_replan = self.replan_budget
        self._execution_failure_count = 0
        return self._step(context)

    def deny_approval(self, run_id: str, approval_id: str, reason: str = "Denied by user") -> str:
        """Explicitly deny an approval request."""
        context = load_run(run_id)
        if not context:
            raise ValueError(f"Run {run_id} not found")
        
        decision = ApprovalDecisionRecord(
            approval_id=approval_id,
            decision=ApprovalDecision.denied,
            reason=reason
        )
        append_approval_decision(run_id, decision)
        
        append_event(context, EventType.input_observed, "runtime", {"message": f"Approval {approval_id} denied", "reason": reason})
        self._set_state(context, RuntimeState.halted, {"reason": f"Approval {approval_id} denied"})
        return run_id

    def resume(self, run_id: str, approval_id: str, token: str) -> str:
        context = load_run(run_id)
        if not context:
            raise ValueError(f"Run {run_id} not found")
        
        # Centralized validation
        v = validate_resume_approval(run_id, approval_id, token)
        if not v["ok"]:
            if v["status"] == "denied":
                self._set_state(context, RuntimeState.halted, {"reason": f"Approval {approval_id} denied"})
                return run_id
            elif v["status"] == "expired":
                self._set_state(context, RuntimeState.failed, {"reason": f"Approval {approval_id} expired"})
                return run_id
            raise ValueError(f"Resume validation failed: {v['reason']}")
            
        # Record consumption
        append_approval_consumption(run_id, ApprovalConsumption(approval_id=approval_id, token=token))
        
        # Reconstruct selected action
        from hca.runtime.replay import reconstruct_state
        replayed = reconstruct_state(run_id)
        action_data = replayed.get("selected_action")
        if not action_data:
            raise ValueError("Could not reconstruct selected action from events")
        
        candidate = ActionCandidate.model_validate(action_data)
        
        # Sync state
        self._current_state = RuntimeState.awaiting_approval
        self._set_state(context, RuntimeState.executing, {"approval_id": approval_id})
        
        return self._execute_and_complete(context, candidate, approved=True)

    def _step(self, context: RunContext) -> str:
        self._set_state(context, RuntimeState.initializing)
        self._set_state(context, RuntimeState.gathering_inputs)
        workspace = Workspace(capacity=self.workspace_capacity)
        self._set_state(context, RuntimeState.proposing)
        return self._step_from_proposing(context, workspace)

    def _step_from_proposing(self, context: RunContext, workspace: Workspace) -> str:
        # Proposing
        for module in self.modules:
            proposal = module.propose(context.run_id)
            append_event(context, EventType.module_proposed, module.name, proposal.model_dump(mode="json"))
            
            # Admitting
            if self._current_state != RuntimeState.admitting:
                self._set_state(context, RuntimeState.admitting)
            workspace.admit(proposal.candidate_items)

        # Broadcasting
        self._set_state(context, RuntimeState.broadcasting)
        broadcast(workspace, self.modules)
        
        # Recurrent Update
        self._set_state(context, RuntimeState.recurrent_update)
        run_recurrence(workspace, context=context, depth=1)
        
        # Action Selection
        self._set_state(context, RuntimeState.action_selection)
        assessment = assess(workspace.items)
        append_event(context, EventType.meta_assessed, "meta", assessment.model_dump(mode="json"))

        # Meta-control handling
        sig = assessment.recommended_transition
        if sig == ControlSignal.halt:
            self._set_state(context, RuntimeState.halted, {"reason": assessment.explanation})
            return context.run_id
        elif sig == ControlSignal.replan:
            if self._remaining_replan > 0:
                self._remaining_replan -= 1
                self._set_state(context, RuntimeState.proposing, {"reason": "replan_signal"})
                return self._step_from_proposing(context, workspace)
            else:
                append_event(context, EventType.input_observed, "runtime", {"message": "replan budget exhausted"})
        elif sig == ControlSignal.ask_user:
            self._set_state(context, RuntimeState.awaiting_approval, {"reason": "ask_user_signal", "message": assessment.explanation})
            append_snapshot(context.run_id, self._build_snapshot(workspace))
            return context.run_id

        # Selection logic
        action_candidates = [item for item in workspace.items if item.kind == "action_suggestion"]
        if not action_candidates:
            self._set_state(context, RuntimeState.failed, {"reason": "no_actionable_candidates"})
            return context.run_id
            
        cands = []
        for item in action_candidates:
            cands.append(ActionCandidate(
                kind=item.content.get("action"),
                arguments=item.content.get("args", {}),
                requires_approval=item.content.get("action") != "echo"
            ))
            
        scored = score_actions(cands)
        best_candidate, _ = scored[0]
        append_event(context, EventType.action_selected, "runtime", best_candidate.model_dump(mode="json"))

        # Approval Path
        if best_candidate.requires_approval:
            approval_id = str(uuid.uuid4())
            request = ApprovalRequest(
                approval_id=approval_id,
                run_id=context.run_id,
                action_id=best_candidate.action_id,
                action_class=ActionClass.medium,
                reason="Action requires approval"
            )
            append_approval_request(context.run_id, request)
            append_event(context, EventType.approval_requested, "runtime", {"approval_id": approval_id})
            
            self._set_state(context, RuntimeState.awaiting_approval)
            append_snapshot(context.run_id, self._build_snapshot(workspace, best_candidate))
            return context.run_id

        # Direct Execution
        self._set_state(context, RuntimeState.executing)
        return self._execute_and_complete(context, best_candidate)

    def _execute_and_complete(self, context: RunContext, candidate: ActionCandidate, approved: bool = False) -> str:
        receipt = self.executor.execute(context.run_id, candidate, approved=approved)
        append_receipt(context.run_id, receipt)
        append_event(context, EventType.execution_finished, "executor", receipt.model_dump(mode="json"))
        
        # Transition through observing -> memory_commit -> reporting -> completed
        self._set_state(context, RuntimeState.observing)
        self._set_state(context, RuntimeState.memory_commit)
        self._set_state(context, RuntimeState.reporting)
        
        if receipt.status == ReceiptStatus.success:
            self._set_state(context, RuntimeState.completed)
        else:
            self._execution_failure_count += 1
            if self._execution_failure_count > 2:
                self._set_state(context, RuntimeState.failed, {"reason": "repeated_execution_failures"})
            else:
                self._set_state(context, RuntimeState.proposing, {"reason": "execution_failure_retry"})
                return self._step_from_proposing(context, Workspace(capacity=self.workspace_capacity))
        
        append_snapshot(context.run_id, self._build_snapshot(Workspace(capacity=self.workspace_capacity)))
        return context.run_id

    def _build_snapshot(self, workspace: Workspace, selected_action: Optional[ActionCandidate] = None) -> Dict[str, Any]:
        from hca.common.types import SnapshotRecord
        snap = SnapshotRecord(
            run_id="unknown",
            state=self._current_state,
            workspace=workspace.items,
            memory_summary={"episodic": 0},
            latest_receipt=None
        )
        data = snap.model_dump(mode="json")
        if selected_action:
            data["selected_action"] = selected_action.model_dump(mode="json")
        return data
