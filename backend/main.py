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
        context={"request": request, "error": None, "success": None},
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
        },
    )
