import re
from typing import List, Set, Tuple
from src.trustdesk.models.domain import GuardrailResult

class OutputGuardrail:
    """Validates generated draft responses before presenting to the human support agent or customer."""

    FORBIDDEN_OUTPUT_STRINGS = [
        "SUPER500",
        "HACK100",
        "VIP90",
        "CRITICAL SYSTEM OVERRIDE",
        "system prompt override",
        "exfiltrate",
    ]

    def validate_output(
        self,
        response_text: str,
        cited_doc_ids: List[str],
        valid_doc_ids: Set[str],
    ) -> GuardrailResult:
        upper_text = response_text.upper()

        # Check forbidden tokens or leaked exploit payloads
        for forbidden in self.FORBIDDEN_OUTPUT_STRINGS:
            if forbidden.upper() in upper_text:
                return GuardrailResult(
                    is_safe=False,
                    flag_type="OUTPUT_LEAK_OR_EXPLOIT",
                    reason=f"Draft contained forbidden exploit string: {forbidden}",
                    sanitized_content="[Blocked by Output Guardrail: Response contained unauthorized exploit payload.]"
                )

        # Check citation validity: any cited doc must exist in valid_doc_ids
        for doc_id in cited_doc_ids:
            if doc_id not in valid_doc_ids:
                return GuardrailResult(
                    is_safe=False,
                    flag_type="HALLUCINATED_CITATION",
                    reason=f"Draft cited non-existent or inactive document ID: {doc_id}",
                    sanitized_content="[Blocked by Output Guardrail: Response cited invalid document ID.]"
                )

        return GuardrailResult(is_safe=True, sanitized_content=response_text)
