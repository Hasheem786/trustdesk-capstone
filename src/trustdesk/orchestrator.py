import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from src.trustdesk.models.domain import (
    Ticket,
    TriageResult,
    DraftResponse,
    OperationalAction,
    GuardrailResult,
    AuditTrace,
)
from src.trustdesk.storage.repository import Repository
from src.trustdesk.triage.engine import TriageEngine
from src.trustdesk.rag.retriever import KnowledgeRetriever
from src.trustdesk.rag.grounder import CitationGrounder
from src.trustdesk.guardrails.doc_guard import DocumentGuardrail
from src.trustdesk.guardrails.output_guard import OutputGuardrail
from src.trustdesk.actions.executor import ActionExecutor
from src.trustdesk.ai.base import AIProvider

class SupportOperationsOrchestrator:
    """End-to-End Orchestrator for TrustDesk Support Operations."""

    def __init__(self, ai_provider: AIProvider, repo: Repository):
        self.ai_provider = ai_provider
        self.repo = repo
        self.triage_engine = TriageEngine(ai_provider, repo)
        self.doc_guard = DocumentGuardrail()
        self.output_guard = OutputGuardrail()
        self.grounder = CitationGrounder()
        self.action_executor = ActionExecutor(ai_provider, repo)

    async def process_ticket(
        self,
        ticket: Ticket,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs complete support operations workflow:
        1. Input Guardrail & Triage
        2. Policy Retrieval (RAG)
        3. Poisoned Document Filtering
        4. Grounded Response Draft Generation
        5. Output Guardrail & Citation Verification
        6. Operational Action Proposal (HITL)
        7. Full Audit Logging
        """
        if not trace_id:
            trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"

        # 1. Triage & Input Guardrail
        triage_res, input_guard_res = await self.triage_engine.triage(ticket, trace_id=trace_id)

        # 2. Knowledge Retrieval (RAG)
        all_docs = self.repo.list_kb_documents(active_only=True)
        retriever = KnowledgeRetriever(all_docs)
        raw_retrieved_docs = retriever.retrieve(f"{ticket.subject} {ticket.description}", top_k=3)

        # 3. Document Guardrail (filter out poisoned docs like KB-ADVERSARIAL-001)
        safe_docs, flagged_doc_ids = self.doc_guard.inspect_and_filter(raw_retrieved_docs)

        if flagged_doc_ids:
            self.repo.add_audit_trace(AuditTrace(
                trace_id=trace_id,
                ticket_id=ticket.id,
                step_name="doc_guardrail",
                input_data={"retrieved_doc_ids": [d.doc_id for d in raw_retrieved_docs]},
                guardrail_flags=["POISONED_DOC_INJECTION"],
                output_data={"flagged_docs": flagged_doc_ids},
                created_at=datetime.utcnow().isoformat() + "Z",
            ))

        # 4. Grounded Draft Generation
        customer = self.repo.get_customer(ticket.customer_id) if ticket.customer_id else None
        order = self.repo.get_order(ticket.order_id) if ticket.order_id else None

        draft = await self.ai_provider.generate_draft(ticket, safe_docs, order, customer)

        # 5. Output Guardrail & Citation Grounding Check
        valid_doc_ids = {d.doc_id for d in all_docs if not d.category == "adversarial_test"}
        output_guard_res = self.output_guard.validate_output(
            draft.response_text,
            draft.cited_doc_ids,
            valid_doc_ids,
        )

        if not output_guard_res.is_safe:
            draft.response_text = output_guard_res.sanitized_content or "[Sanitized by Output Guardrail]"
            draft.is_grounded = False
            draft.needs_escalation = True

        # Save draft to repository
        saved_draft = self.repo.save_draft(draft)

        # 6. Operational Action Proposal (HITL)
        proposed_action = None
        if input_guard_res.is_safe and not flagged_doc_ids:
            proposed_action = await self.action_executor.propose_operational_action(
                ticket, triage_res, trace_id=trace_id
            )

        # 7. Audit Trace for generation
        self.repo.add_audit_trace(AuditTrace(
            trace_id=trace_id,
            ticket_id=ticket.id,
            step_name="orchestration_complete",
            input_data={"ticket_id": ticket.id},
            retrieved_docs=[d.doc_id for d in safe_docs],
            guardrail_flags=[f for f in [input_guard_res.flag_type] if f] + (["POISONED_DOC_INJECTION"] if flagged_doc_ids else []),
            output_data={
                "category": triage_res.category.value,
                "priority": triage_res.priority.value,
                "escalate": triage_res.escalate,
                "cited_doc_ids": saved_draft.cited_doc_ids,
                "proposed_action_id": proposed_action.id if proposed_action else None,
            },
            created_at=datetime.utcnow().isoformat() + "Z",
        ))

        return {
            "ticket": self.repo.get_ticket(ticket.id),
            "triage": triage_res,
            "draft": saved_draft,
            "proposed_action": proposed_action,
            "guardrail_flags": [f for f in [input_guard_res.flag_type] if f] + (["POISONED_DOC_INJECTION"] if flagged_doc_ids else []),
            "retrieved_docs": safe_docs,
            "trace_id": trace_id,
        }
