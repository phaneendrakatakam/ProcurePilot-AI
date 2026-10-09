from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Controlled Procurement & Accounts-Payable Operations Platform",
)

app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def disable_development_cache(request, call_next):
    response = await call_next(request)
    if settings.app_env == "development" and (
        request.url.path in {"/login", "/app"}
        or request.url.path.startswith("/static/")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=307)


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    return FileResponse(WEB_DIR / "login.html")


@app.get("/app", include_in_schema=False)
def application_page() -> FileResponse:
    return FileResponse(WEB_DIR / "app.html")
