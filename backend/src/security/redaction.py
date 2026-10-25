"""
Sensitive attribute redaction engine.
Recursively inspects span attributes, events, and tags, masking or dropping sensitive keys
before attributes ever reach persistence or query responses.
"""

import re
from typing import Any, Dict, List, Optional, Set

DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "authorization",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
    "private_key",
    "client_secret"
}

class AttributeRedactor:
    def __init__(
        self,
        sensitive_keys: Optional[Set[str]] = None,
        mask: str = "[REDACTED]"
    ):
        self.sensitive_keys = {k.lower() for k in (sensitive_keys or DEFAULT_SENSITIVE_KEYS)}
        self.mask = mask

    def is_sensitive_key(self, key: str) -> bool:
        lower_key = key.lower()
        # Direct match or pattern match (e.g. user.password, db.password)
        if lower_key in self.sensitive_keys:
            return True
        for sens in self.sensitive_keys:
            if lower_key.endswith(f".{sens}") or lower_key.endswith(f"_{sens}") or lower_key == sens:
                return True
        return False

    def redact(self, obj: Any) -> Any:
        """
        Recursively redact dictionary or list structures.
        """
        if isinstance(obj, dict):
            redacted_dict: Dict[str, Any] = {}
            for k, v in obj.items():
                if self.is_sensitive_key(str(k)):
                    redacted_dict[k] = self.mask
                else:
                    redacted_dict[k] = self.redact(v)
            return redacted_dict
        elif isinstance(obj, list):
            return [self.redact(item) for item in obj]
        return obj

    def redact_span_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact span attributes prior to storage insertion.
        """
        return self.redact(attributes)
