from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from routers import auth, decode, payments
from services.supabase_client import (
    get_current_user,
    get_user_profile,
    get_user_usage,
    get_user_history
)

app = FastAPI(
    title="DigitalDarling",
    description="AI Relationship Chat Analyst",
    docs_url=None,      # disable /docs in all envs — no API surface exposure
    redoc_url=None,
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# ── Global error handlers ──────────────────────────────────────────────────────

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Take a breath — too many requests."}
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"detail": "Page not found."}
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # Never leak stack traces or internal details to the client
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."}
    )

# ── Static & templates ─────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth.router)
app.include_router(decode.router)
app.include_router(payments.router)

# ── Layout helper ──────────────────────────────────────────────────────────────

def get_base_template(request: Request) -> str:
    if request.headers.get("HX-Request"):
        return "partials/htmx_base.html"
    return "base.html"

# ── Page routes ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "index.html", {
        "base_template": get_base_template(request),
        "user": user
    })

@app.get("/decode", response_class=HTMLResponse)
async def decode_page(request: Request):
    user = get_current_user(request)
    reads_left = 3
    plan = "free"

    if user:
        user_id = user["sub"]
        profile = await get_user_profile(user_id)
        plan = profile.get("plan", "free").lower()

        if plan == "paid":
            reads_left = "Unlimited"
        else:
            usage_count = await get_user_usage(user_id)
            reads_left = max(0, 3 - usage_count)

    return templates.TemplateResponse(request, "decode.html", {
        "base_template": get_base_template(request),
        "user": user,
        "reads_left": reads_left,
        "plan": plan
    })

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    user = get_current_user(request)
    if not user:
        if request.headers.get("HX-Request"):
            return HTMLResponse(content="", status_code=204,
                                headers={"HX-Redirect": "/auth/login"})
        return RedirectResponse(url="/auth/login")

    user_id = user["sub"]
    history = await get_user_history(user_id)

    return templates.TemplateResponse(request, "history.html", {
        "base_template": get_base_template(request),
        "user": user,
        "history": history
    })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    profile = None
    usage_count = 0

    if user:
        user_id = user["sub"]
        profile = await get_user_profile(user_id)
        usage_count = await get_user_usage(user_id)

    return templates.TemplateResponse(request, "profile.html", {
        "base_template": get_base_template(request),
        "user": user,
        "profile": profile,
        "usage_count": usage_count
    })

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    user = get_current_user(request)
    plan = "free"

    if user:
        user_id = user["sub"]
        profile = await get_user_profile(user_id)
        plan = profile.get("plan", "free").lower()

    return templates.TemplateResponse(request, "pricing.html", {
        "base_template": get_base_template(request),
        "user": user,
        "plan": plan
    })

# ── Legal pages ────────────────────────────────────────────────────────────────

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "privacy.html", {
        "base_template": get_base_template(request),
        "user": user,
    })

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "terms.html", {
        "base_template": get_base_template(request),
        "user": user,
    })

@app.get("/refund", response_class=HTMLResponse)
async def refund_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "refund.html", {
        "base_template": get_base_template(request),
        "user": user,
    })
