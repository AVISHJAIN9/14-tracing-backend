"""
Personally Identifiable Information (PII) filtering and sanitization engine.
Scans string values across span attributes, event descriptions, and status messages,
replacing detected PII (emails, SSNs, credit card numbers, phone numbers, IP addresses)
with secure redaction placeholders before database persistence.
"""

import re
from typing import Any, Dict, List, Pattern, Tuple

# Comprehensive regex patterns for PII detection
EMAIL_REGEX: Pattern = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
)
SSN_REGEX: Pattern = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)
CREDIT_CARD_REGEX: Pattern = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b"
)
PHONE_REGEX: Pattern = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
IPV4_REGEX: Pattern = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
)

PII_REPLACEMENTS: List[Tuple[Pattern, str]] = [
    (EMAIL_REGEX, "[EMAIL_REDACTED]"),
    (SSN_REGEX, "[SSN_REDACTED]"),
    (CREDIT_CARD_REGEX, "[CARD_REDACTED]"),
    (PHONE_REGEX, "[PHONE_REDACTED]"),
    (IPV4_REGEX, "[IP_REDACTED]"),
]

class PiiFilter:
    def __init__(self, mask_ips: bool = True):
        self.mask_ips = mask_ips

    def sanitize_string(self, text: str) -> str:
        """
        Scan a string and replace all matches of PII patterns with placeholders.
        """
        if not text or not isinstance(text, str):
            return text

        result = text
        for pattern, replacement in PII_REPLACEMENTS:
            if not self.mask_ips and pattern == IPV4_REGEX:
                continue
            result = pattern.sub(replacement, result)
        return result

    def sanitize_data(self, data: Any) -> Any:
        """
        Recursively sanitize dictionary values, lists, and nested objects.
        """
        if isinstance(data, str):
            return self.sanitize_string(data)
        elif isinstance(data, dict):
            return {k: self.sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_data(item) for item in data]
        return data
