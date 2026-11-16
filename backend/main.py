import time
from pathlib import Path
from fastapi import FastAPI, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from backend.ai import write_answer
from backend.database import add_notice, get_all_notices, init_db
from backend.search import find_best_notice

# Initialize SQLite database and tables
init_db()

# Create FastAPI application
app = FastAPI(title="CampusFlow AI")

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend"))


@app.get("/", response_class=HTMLResponse)
async def role_chooser(request: Request):
    """Step 1: Role chooser page."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "role": None, "error": None},
    )


@app.get("/login/student", response_class=HTMLResponse)
async def student_login_form(request: Request):
    """Step 2: Student login form."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "role": "student", "error": None},
    )


@app.get("/login/admin", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    """Step 2: Admin login form."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "role": "admin", "error": None},
    )


@app.post("/login/student", response_class=HTMLResponse)
async def student_login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
):
    """Process student login credentials."""
    if username == "student1" and password == "student123":
        return RedirectResponse(url="/student", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "role": "student",
            "error": "Wrong student username or password.",
        },
    )


@app.post("/login/admin", response_class=HTMLResponse)
async def admin_login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
):
    """Process admin login credentials."""
    if username == "admin1" and password == "admin123":
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "role": "admin",
            "error": "Wrong admin username or password.",
        },
    )


@app.get("/student", response_class=HTMLResponse)
async def student_area(request: Request):
    """Render the student area page with recent notices."""
    notices = get_all_notices(limit=6)
    return templates.TemplateResponse(
        request=request,
        name="student.html",
        context={
            "request": request,
            "has_asked": False,
            "question": "",
            "answer": "",
            "matched_notice": None,
            "confidence": 0,
            "is_verified": False,
            "recent_notices": notices,
        },
    )


@app.post("/ask", response_class=HTMLResponse)
async def ask_question(
    request: Request,
    question: str = Form(""),
):
    """Process student questions against approved campus notices."""
    all_notices = get_all_notices()
    matched_notice, confidence = find_best_notice(question, all_notices)
    is_verified = bool(matched_notice and confidence >= 30)

    answer = ""
    if is_verified and matched_notice:
        answer = write_answer(
            question=question,
            notice_title=matched_notice.get("title", ""),
            notice_text=matched_notice.get("text", ""),
        )

    return templates.TemplateResponse(
        request=request,
        name="student.html",
        context={
            "request": request,
            "has_asked": True,
            "question": question,
            "answer": answer,
            "matched_notice": matched_notice,
            "confidence": confidence,
            "is_verified": is_verified,
            "recent_notices": all_notices[:6],
        },
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_area(request: Request):
    """Render the admin dashboard page."""
    notices = get_all_notices(limit=10)
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "request": request,
            "error": None,
            "success": None,
            "title": "",
            "category": "",
            "date": "",
            "notice_text": "",
            "notices": notices,
        },
    )


@app.post("/admin/read-image", response_class=HTMLResponse)
async def admin_read_image(
    request: Request,
    title: str = Form(""),
    category: str = Form(""),
    date: str = Form(""),
    image: UploadFile = File(None),
):
    """Read and extract text from an uploaded notice image."""
    notices = get_all_notices(limit=10)

    if not image or not image.filename:
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "request": request,
                "error": "Please select a JPG or PNG notice image to read.",
                "success": None,
                "title": title,
                "category": category,
                "date": date,
                "notice_text": "",
                "notices": notices,
            },
        )

    image_bytes = await image.read()
    if not image_bytes:
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "request": request,
                "error": "The selected image file was empty. Please select a valid file.",
                "success": None,
                "title": title,
                "category": category,
                "date": date,
                "notice_text": "",
                "notices": notices,
            },
        )

    mime_type = image.content_type or "image/jpeg"

    try:
        from backend.vision import extract_text_from_image

        extracted_text = extract_text_from_image(image_bytes, mime_type=mime_type)
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "request": request,
                "success": "Notice text extracted! Review or edit the text below, then save.",
                "error": None,
                "title": title,
                "category": category,
                "date": date,
                "notice_text": extracted_text,
                "notices": notices,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "request": request,
                "error": f"Could not read image: {str(e)}",
                "success": None,
                "title": title,
                "category": category,
                "date": date,
                "notice_text": "",
                "notices": notices,
            },
        )


@app.post("/admin/upload", response_class=HTMLResponse)
async def admin_upload(
    request: Request,
    title: str = Form(""),
    category: str = Form(""),
    date: str = Form(""),
    image: UploadFile = File(None),
    notice_text: str = Form(""),
):
    """Process notice upload, save to SQLite database, and enforce either-or rule."""
    has_image = image is not None and bool(image.filename)
    has_text = bool(notice_text.strip())
    existing_notices = get_all_notices(limit=10)

    if not has_image and not has_text:
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "request": request,
                "error": "Please upload an image or type the notice text.",
                "success": None,
                "title": title,
                "category": category,
                "date": date,
                "notice_text": notice_text,
                "notices": existing_notices,
            },
        )

    saved_image_name = None
    if has_image:
        image_bytes = await image.read()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{int(time.time())}_{Path(image.filename).name}"
        file_dest = UPLOAD_DIR / safe_filename
        file_dest.write_bytes(image_bytes)
        saved_image_name = safe_filename

        # If text wasn't manually typed, attempt extraction or use title description
        if not has_text:
            try:
                from backend.vision import extract_text_from_image

                notice_text = extract_text_from_image(
                    image_bytes, mime_type=image.content_type or "image/jpeg"
                )
            except Exception:
                notice_text = f"Official campus notice image: {title} ({category})"

    # Save notice to SQLite database
    add_notice(
        title=title,
        category=category,
        notice_date=date,
        text=notice_text,
        source_image=saved_image_name,
    )

    updated_notices = get_all_notices(limit=10)
    success_msg = f"Notice '{title}' saved to database successfully!"

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "request": request,
            "success": success_msg,
            "error": None,
            "title": "",
            "category": "",
            "date": "",
            "notice_text": "",
            "notices": updated_notices,
        },
    )
