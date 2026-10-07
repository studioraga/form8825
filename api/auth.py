from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
ROLE_LEVEL = {"viewer": 10, "reviewer": 20, "admin": 30}


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


def _key_map() -> dict[str, Principal]:
    raw = os.getenv("FORM8825_API_KEYS", "")
    out: dict[str, Principal] = {}
    for entry in filter(None, (part.strip() for part in raw.split(","))):
        pieces = entry.split(":", 2)
        if len(pieces) == 2:
            key, role = pieces
            subject = role
        else:
            key, role, subject = pieces
        if role not in ROLE_LEVEL:
            raise RuntimeError(f"Unsupported RBAC role: {role}")
        out[key] = Principal(subject=subject or role, role=role)
    return out


def current_principal(api_key: str | None = Depends(api_key_header)) -> Principal:
    if os.getenv("AUTH_MODE", "disabled").lower() != "enabled":
        return Principal(subject="development", role="admin")
    if not api_key:
        raise HTTPException(401, "Missing X-API-Key")
    principal = _key_map().get(api_key)
    if principal is None:
        raise HTTPException(401, "Invalid API key")
    return principal


def require_role(min_role: str) -> Callable:
    if min_role not in ROLE_LEVEL:
        raise ValueError(min_role)

    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if ROLE_LEVEL[principal.role] < ROLE_LEVEL[min_role]:
            raise HTTPException(403, f"Role {min_role} or higher required")
        return principal

    return dependency
