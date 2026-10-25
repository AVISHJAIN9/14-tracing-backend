"""
Fine-grained trace-level authorization service.
Enforces service-level ownership scopes and classification tags (e.g. restricted, pci, confidential)
on individual traces within a tenant boundary.
"""

from typing import Collection, Optional, Set
from storage.models import TraceRecord, SpanRecord

class TraceAccessDeniedError(Exception):
    pass

class TraceAuthorizationService:
    @staticmethod
    def is_service_allowed(user_services: Optional[Collection[str]], trace_root_service: str) -> bool:
        """
        Check if user's authorized service scopes include the trace root service.
        None or '*' wildcard allows all services.
        """
        if user_services is None:
            return True
        if "*" in user_services:
            return True
        return trace_root_service in user_services

    @staticmethod
    def check_classification_tags(
        user_scopes: Collection[str],
        trace_attributes: dict
    ) -> bool:
        """
        If trace has a 'classification' or 'confidentiality' attribute,
        verify caller holds corresponding permission scope.
        """
        classification = trace_attributes.get("classification") or trace_attributes.get("security.classification")
        if not classification:
            return True # Standard trace, no special tag required

        required_scope = f"classification:{classification.lower()}"
        if "classification:*" in user_scopes or required_scope in user_scopes or "admin" in user_scopes:
            return True
        return False

    @staticmethod
    def enforce_trace_access(
        user_services: Optional[Collection[str]],
        user_scopes: Collection[str],
        trace: TraceRecord,
        root_span_attributes: Optional[dict] = None
    ) -> None:
        """
        Authorize access to a specific trace. Raises TraceAccessDeniedError if scope requirements are not met.
        """
        # 1. Service ownership scope check
        if not TraceAuthorizationService.is_service_allowed(user_services, trace.root_service_name):
            raise TraceAccessDeniedError(
                f"Unauthorized service scope: user not permitted to view traces from '{trace.root_service_name}'"
            )

        # 2. Classification tags check
        attrs = root_span_attributes or {}
        if not TraceAuthorizationService.check_classification_tags(user_scopes, attrs):
            classification = attrs.get("classification") or attrs.get("security.classification")
            raise TraceAccessDeniedError(
                f"Unauthorized classification: trace requires scope 'classification:{classification}'"
            )
