import re
from typing import Tuple, Optional
from src.trustdesk.models.domain import GuardrailResult

class InputGuardrail:
    """Multi-layered adversarial input detector defending against:
    - Prompt injections & jailbreaks
    - Secret exfiltration & system prompt leaks
    - Unauthorized coupon generation exploits
    - Identity verification / 2FA bypass attempts
    """

    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"system\s+prompt\s+override",
        r"you\s+are\s+now\s+(an?\s+)?unconstrained",
        r"jailbreak",
        r"developer\s+mode",
        r"dan\s+mode",
        r"disregard\s+(all\s+)?rules",
        r"new\s+operating\s+instructions",
    ]

    SECRET_LEAK_PATTERNS = [
        r"print\s+(the\s+)?(entire\s+)?system\s+prompt",
        r"reveal\s+(internal|secret|system)\s+(prompt|keys|guidelines|instructions)",
        r"what\s+(is|are)\s+your\s+(secret|hidden|system)\s+(prompt|instructions)",
        r"exfiltrate",
        r"internal\s+api\s+keys",
    ]

    COUPON_EXPLOIT_PATTERNS = [
        r"generate\s+.*coupon",
        r"give\s+me\s+.*(\d+%\s+off|coupon|discount)",
        r"coupon\s+code",
        r"issue\s+(\$\d+|\d+%)\s+.*coupon",
        r"secret\s+\d+%\s+off",
    ]

    PRIVILEGE_BYPASS_PATTERNS = [
        r"disable\s+2fa.*without.*(verification|asking)",
        r"bypass\s+(identity\s+verification|2fa|security)",
        r"i\s+am\s+the\s+ceo.*bypass",
    ]

    def validate(self, text: str) -> GuardrailResult:
        normalized = text.lower()

        # Check prompt injection
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    flag_type="PROMPT_INJECTION",
                    reason="Potential prompt injection or jailbreak detected.",
                    sanitized_content="[Content blocked by TrustDesk Input Guardrail: Adversarial prompt injection detected.]"
                )

        # Check secret leak attempts
        for pattern in self.SECRET_LEAK_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    flag_type="SECRET_LEAK_ATTEMPT",
                    reason="Attempt to extract system prompt or internal secrets detected.",
                    sanitized_content="[Content blocked by TrustDesk Input Guardrail: Unauthorized secret exfiltration attempt.]"
                )

        # Check coupon exploits
        for pattern in self.COUPON_EXPLOIT_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    flag_type="COUPON_EXPLOIT",
                    reason="Unauthorized coupon or discount generation exploit detected.",
                    sanitized_content="[Content blocked by TrustDesk Input Guardrail: Unauthorized coupon generation request.]"
                )

        # Check privilege / 2FA bypass
        for pattern in self.PRIVILEGE_BYPASS_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    flag_type="PRIVILEGE_BYPASS_ATTEMPT",
                    reason="Unauthorized attempt to bypass security authentication or 2FA.",
                    sanitized_content="[Content blocked by TrustDesk Input Guardrail: Security verification bypass attempt.]"
                )

        return GuardrailResult(is_safe=True, sanitized_content=text)
