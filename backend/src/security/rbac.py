"""
Role-based access control (RBAC) service enforcing deny-by-default server-side authorization.
Maps roles (admin, ingest, query, readonly) to granular permissions.
"""

from enum import Enum
from typing import Collection, Dict, Set

class AccessDeniedError(Exception):
    pass

class Permission(str, Enum):
    INGEST_SPANS = "spans:ingest"
    QUERY_SPANS = "spans:query"
    QUERY_TRACES = "traces:query"
    DELETE_SPANS = "spans:delete"
    MANAGE_API_KEYS = "api_keys:manage"
    MANAGE_TENANTS = "tenants:manage"
    VIEW_METRICS = "metrics:view"

class Role(str, Enum):
    ADMIN = "admin"
    INGEST = "ingest"
    QUERY = "query"
    READONLY = "readonly"

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.INGEST_SPANS,
        Permission.QUERY_SPANS,
        Permission.QUERY_TRACES,
        Permission.DELETE_SPANS,
        Permission.MANAGE_API_KEYS,
        Permission.MANAGE_TENANTS,
        Permission.VIEW_METRICS,
    },
    Role.INGEST: {
        Permission.INGEST_SPANS,
    },
    Role.QUERY: {
        Permission.QUERY_SPANS,
        Permission.QUERY_TRACES,
        Permission.VIEW_METRICS,
    },
    Role.READONLY: {
        Permission.QUERY_SPANS,
        Permission.QUERY_TRACES,
        Permission.VIEW_METRICS,
    }
}

class RbacService:
    @staticmethod
    def has_permission(roles: Collection[str], permission: Permission) -> bool:
        """
        Check if any of the provided roles grant the specified permission.
        Deny by default if roles are empty or unrecognized.
        """
        for r_str in roles:
            try:
                role_enum = Role(r_str)
                allowed = ROLE_PERMISSIONS.get(role_enum, set())
                if permission in allowed:
                    return True
            except ValueError:
                # Unrecognized role string, ignore and continue
                continue
        return False

    @staticmethod
    def enforce_permission(roles: Collection[str], permission: Permission) -> None:
        """
        Enforce that caller possesses the specified permission; raises AccessDeniedError otherwise.
        """
        if not RbacService.has_permission(roles, permission):
            roles_repr = ", ".join(roles) if roles else "none"
            raise AccessDeniedError(
                f"Access denied: permission '{permission.value}' requires higher privilege. Current roles: [{roles_repr}]"
            )
