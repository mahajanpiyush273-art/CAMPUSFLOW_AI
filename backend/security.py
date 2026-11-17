"""
CampusFlow AI - Security & Authentication
Password hashing, session handling, current user dependencies, and role guards.
"""

import hashlib
import secrets
from typing import Any, Callable, Dict, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from backend.database import get_connection


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random 16-byte salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored salt and PBKDF2 hash."""
    try:
        if not hashed or "$" not in hashed:
            return False
        salt, key_hex = hashed.split("$")
        check_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(check_key.hex(), key_hex)
    except Exception:
        return False


def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Retrieve current logged in user from session if valid."""
    session = getattr(request, "session", None)
    if not session:
        return None

    user_id = session.get("user_id")
    if not user_id:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute(
            "SELECT id, username, role, full_name, email FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if user:
            return dict(user)
    return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """Dependency that requires an authenticated user for JSON APIs."""
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user


def require_role(role_name: str) -> Callable:
    """Dependency generator that enforces a specific role ('student' or 'admin')."""
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") != role_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role_name}."
            )
        return user
    return role_checker
