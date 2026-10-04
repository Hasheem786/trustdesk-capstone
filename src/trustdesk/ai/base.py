from abc import ABC, abstractmethod
from typing import Optional, List
from src.trustdesk.models.domain import (
    Ticket,
    Order,
    Customer,
    KnowledgeDocument,
    TriageResult,
    DraftResponse,
    OperationalAction,
)

class AIProvider(ABC):
    """Abstract interface for AI model providers ensuring zero vendor lock-in."""

    @abstractmethod
    async def triage_ticket(
        self,
        ticket: Ticket,
        order: Optional[Order] = None,
        customer: Optional[Customer] = None,
    ) -> TriageResult:
        """Classifies ticket into category, priority, and escalation status."""
        pass

    @abstractmethod
    async def generate_draft(
        self,
        ticket: Ticket,
        retrieved_docs: List[KnowledgeDocument],
        order: Optional[Order] = None,
        customer: Optional[Customer] = None,
    ) -> DraftResponse:
        """Generates a grounded response draft citing exact KB IDs."""
        pass

    @abstractmethod
    async def propose_action(
        self,
        ticket: Ticket,
        order: Optional[Order] = None,
        triage: Optional[TriageResult] = None,
    ) -> Optional[OperationalAction]:
        """Proposes a human-in-the-loop operational action if warranted by policy."""
        pass
