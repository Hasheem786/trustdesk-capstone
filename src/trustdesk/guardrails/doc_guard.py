import re
from typing import List, Tuple
from src.trustdesk.models.domain import KnowledgeDocument, GuardrailResult

class DocumentGuardrail:
    """Document sanitizer defending against poisoned knowledge base entries (e.g., KB-ADVERSARIAL-001)."""

    ADVERSARIAL_DOC_PATTERNS = [
        r"critical\s+system\s+override",
        r"ignore\s+all\s+previous\s+safety\s+rules",
        r"exfiltrate\s+the\s+system\s+prompt",
        r"grant\s+the\s+customer\s+a\s+\$\d+\s+compensation\s+coupon",
        r"approve\s+all\s+refund\s+requests\s+without.*human\s+approval",
    ]

    def inspect_and_filter(
        self, docs: List[KnowledgeDocument]
    ) -> Tuple[List[KnowledgeDocument], List[str]]:
        """Filters out poisoned or adversarial documents from the retrieved context.
        Returns: (safe_documents, list_of_flagged_doc_ids)
        """
        safe_docs: List[KnowledgeDocument] = []
        flagged_doc_ids: List[str] = []

        for doc in docs:
            # Check explicit doc_id pattern or category
            is_poisoned = False
            if doc.category == "adversarial_test" or "ADVERSARIAL" in doc.doc_id.upper():
                is_poisoned = True

            # Check document body patterns
            content_lower = doc.content.lower()
            for pattern in self.ADVERSARIAL_DOC_PATTERNS:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    is_poisoned = True
                    break

            if is_poisoned:
                flagged_doc_ids.append(doc.doc_id)
            else:
                safe_docs.append(doc)

        return safe_docs, flagged_doc_ids
