from pathlib import Path
from fastapi import FastAPI, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

# Initialize the FastAPI app
app = FastAPI()

# Locate frontend directory containing the login template
BASE_DIR = Path(__file__).resolve().parent.parent
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
    """Render the student area page."""
    return templates.TemplateResponse(
        request=request,
        name="student.html",
        context={"request": request},
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_area(request: Request):
    """Render the admin dashboard page."""
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
    """Process notice upload and enforce the either-or rule."""
    has_image = image is not None and bool(image.filename)
    has_text = bool(notice_text.strip())

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
            },
        )

    if has_image:
        success_msg = f"Notice image '{title}' uploaded and saved successfully!"
    else:
        success_msg = f"Notice '{title}' written and saved successfully!"

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
        },
    )
