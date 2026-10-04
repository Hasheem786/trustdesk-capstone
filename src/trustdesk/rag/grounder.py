import re
from typing import List, Set, Tuple
from src.trustdesk.models.domain import KnowledgeDocument, DraftResponse

class CitationGrounder:
    """Extracts, validates, and verifies grounding of AI drafts against retrieved knowledge documents."""

    DOC_ID_REGEX = re.compile(r"KB-[A-Z0-9]+-\d+", re.IGNORECASE)

    def extract_citations(self, text: str) -> List[str]:
        raw_matches = self.DOC_ID_REGEX.findall(text)
        # Normalize uppercase and preserve order without duplicates
        seen: Set[str] = set()
        citations: List[str] = []
        for match in raw_matches:
            upper_match = match.upper()
            if upper_match not in seen:
                seen.add(upper_match)
                citations.append(upper_match)
        return citations

    def verify_grounding(
        self,
        draft_text: str,
        retrieved_docs: List[KnowledgeDocument]
    ) -> Tuple[bool, List[str]]:
        """Checks if all cited documents exist in the retrieved context.
        Returns: (is_grounded, cited_doc_ids)
        """
        cited_ids = self.extract_citations(draft_text)
        retrieved_ids = {d.doc_id.upper() for d in retrieved_docs}

        if not cited_ids:
            # If no citations were made, consider whether policy citations were expected
            return False, []

        for cid in cited_ids:
            if cid not in retrieved_ids:
                # Cited a doc that wasn't even in retrieved context -> ungrounded
                return False, cited_ids

        return True, cited_ids
