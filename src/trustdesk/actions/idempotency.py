import hashlib
import json
from typing import Dict, Any

def generate_idempotency_key(ticket_id: str, action_type: str, parameters: Dict[str, Any]) -> str:
    """Generates a deterministic SHA256 idempotency key:
    ticket_id + action_type + sorted_params_json
    Guarantees no duplicate execution on retries or concurrent clicks.
    """
    params_str = json.dumps(parameters, sort_keys=True)
    payload = f"{ticket_id}:{action_type}:{params_str}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
