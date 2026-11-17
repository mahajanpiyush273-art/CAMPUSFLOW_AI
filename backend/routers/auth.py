"""
CampusFlow AI - Authentication & Profile Router
Handles login, logout, current session inspection, and student profile retrieval/update.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.database import get_connection
from backend.security import get_current_user, require_role, verify_password

router = APIRouter(prefix="/api", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    roll_no: Optional[str] = None
    enrollment_no: Optional[str] = None
    programme: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[str] = None
    section: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    hostel_block: Optional[str] = None
    room_no: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None


@router.post("/auth/login")
async def login(request: Request, payload: Optional[LoginRequest] = None):
    """Authenticate student or admin and establish a secure session."""
    # Support both JSON payload and Form data
    if payload:
        username = payload.username.strip()
        password = payload.password
        req_role = payload.role
    else:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        req_role = form.get("role")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required."
        )

    with get_connection() as conn:
        cursor = conn.cursor()
        user_row = cursor.execute(
            "SELECT id, username, password_hash, role, full_name, email FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if not user_row or not verify_password(password, user_row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Please check your credentials."
        )

    user_role = user_row["role"]
    if req_role and req_role != user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account '{username}' does not have the '{req_role}' role."
        )

    # Establish session
    request.session["user_id"] = user_row["id"]
    request.session["username"] = user_row["username"]
    request.session["role"] = user_role
    request.session["full_name"] = user_row["full_name"]

    return {
        "ok": True,
        "user": {
            "id": user_row["id"],
            "username": user_row["username"],
            "role": user_role,
            "full_name": user_row["full_name"],
            "email": user_row["email"]
        }
    }


@router.post("/auth/logout")
async def logout(request: Request):
    """Clear session cookies."""
    request.session.clear()
    return {"ok": True, "message": "Successfully logged out."}


@router.get("/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Return currently authenticated user identity and profile."""
    profile_data = None
    if user["role"] == "student":
        with get_connection() as conn:
            cursor = conn.cursor()
            p_row = cursor.execute(
                "SELECT * FROM student_profiles WHERE user_id = ?",
                (user["id"],)
            ).fetchone()
            if p_row:
                profile_data = dict(p_row)

    return {
        "user": user,
        "profile": profile_data
    }


@router.get("/student/profile")
async def get_student_profile(user: Dict[str, Any] = Depends(require_role("student"))):
    """Retrieve full profile information for the authenticated student."""
    with get_connection() as conn:
        cursor = conn.cursor()
        p_row = cursor.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (user["id"],)
        ).fetchone()

    return {
        "user": user,
        "profile": dict(p_row) if p_row else {}
    }


@router.put("/student/profile")
async def update_student_profile(
    payload: ProfileUpdateRequest,
    user: Dict[str, Any] = Depends(require_role("student"))
):
    """Update student profile details used for form autofill."""
    data = payload.model_dump(exclude_unset=True)

    with get_connection() as conn:
        cursor = conn.cursor()
        exists = cursor.execute(
            "SELECT user_id FROM student_profiles WHERE user_id = ?",
            (user["id"],)
        ).fetchone()

        if not exists:
            cursor.execute("INSERT INTO student_profiles (user_id) VALUES (?)", (user["id"],))

        if data:
            set_clauses = [f"{col} = ?" for col in data.keys()]
            values = list(data.values()) + [user["id"]]
            cursor.execute(
                f"UPDATE student_profiles SET {', '.join(set_clauses)} WHERE user_id = ?",
                values
            )
        conn.commit()

        updated = cursor.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (user["id"],)
        ).fetchone()

    return {
        "ok": True,
        "message": "Profile updated successfully.",
        "profile": dict(updated) if updated else {}
    }
