"""
CampusFlow AI - Main FastAPI Application
Coordinates authentication sessions, API routers, role-protected HTML shells,
and static asset delivery.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.config import BASE_DIR, SECRET_KEY
from backend.database import init_db
from backend.reminders import run_reminder_worker
from backend.routers import admin, auth, student
from backend.security import get_current_user_optional
from backend.seed import seed_database

# 1. Initialize SQLite database tables and seed sample data
init_db()
seed_database(force=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Background tasks manager for reminder dispatching."""
    worker_task = None
    if os.environ.get("TESTING") != "1":
        worker_task = asyncio.create_task(run_reminder_worker())
    try:
        yield
    finally:
        if worker_task:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


# 2. Create FastAPI application
app = FastAPI(title="CampusFlow AI - Ask. Verify. Act.", lifespan=lifespan)

# 3. Mount Session Middleware for signed cookie auth
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="campusflow_session",
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=False,
)

# 4. Mount Static Assets directory
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Disable aggressive browser caching for development and demo accuracy."""
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path in ["/admin", "/student", "/login", "/"]:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 5. Include Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(student.router)


# 6. Protected HTML Shell Endpoints
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing and role chooser page."""
    user = get_current_user_optional(request)
    if user:
        if user["role"] == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        return RedirectResponse(url="/student", status_code=303)

    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    login_html = FRONTEND_DIR / "login.html"
    return FileResponse(login_html)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the role-chooser and login page."""
    user = get_current_user_optional(request)
    if user:
        if user["role"] == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        return RedirectResponse(url="/student", status_code=303)

    login_html = FRONTEND_DIR / "login.html"
    return FileResponse(login_html)


@app.get("/student", response_class=HTMLResponse)
async def student_shell(request: Request):
    """Protected student shell page with role verification."""
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login?role=student", status_code=303)
    if user["role"] != "student":
        return RedirectResponse(url="/admin", status_code=303)

    student_html = FRONTEND_DIR / "student.html"
    return FileResponse(student_html)


@app.get("/admin", response_class=HTMLResponse)
async def admin_shell(request: Request):
    """Protected admin shell page with role verification."""
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login?role=admin", status_code=303)
    if user["role"] != "admin":
        return RedirectResponse(url="/student", status_code=303)

    admin_html = FRONTEND_DIR / "admin.html"
    return FileResponse(admin_html)
