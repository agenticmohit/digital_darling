from fastapi import APIRouter, Request, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from services.supabase_client import (
    supabase,
    get_or_create_profile,
    get_current_user,
)
from services.beta import BETA_EMAIL, BETA_PASSWORD, get_beta_user_id
from config import settings
import hashlib
import jwt
import time
import re

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="templates")

limiter = Limiter(key_func=get_remote_address)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _safe_error(raw: str) -> str:
    low = raw.lower()
    if "invalid login credentials" in low or "invalid" in low:
        return "Invalid email or password."
    if "user already registered" in low or "already" in low:
        return "An account with this email already exists."
    if "email not confirmed" in low:
        return "Please confirm your email before signing in."
    if "password" in low and "weak" in low:
        return "Password is too weak. Use at least 8 characters."
    return "Something went wrong. Please try again."


def _make_mock_user_id(email: str) -> str:
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _get_base_template(request: Request) -> str:
    return "partials/htmx_base.html" if request.headers.get("HX-Request") else "base.html"


def _is_secure() -> bool:
    return settings.environment != "development"


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600 * 24 * 7,
        samesite="lax",
        secure=_is_secure(),
    )


def _validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email)) and len(email) <= 254


def _validate_password(password: str) -> bool:
    return 8 <= len(password) <= 128


def _mock_token(email: str) -> str:
    user_id = _make_mock_user_id(email)
    return jwt.encode(
        {"sub": user_id, "email": email, "aud": "authenticated",
         "exp": int(time.time()) + 3600 * 24 * 7},
        settings.supabase_jwt_secret, algorithm="HS256"
    )


def _htmx_redirect(url: str, token: str = None) -> Response:
    """Return a 200 response that tells HTMX to do a full page navigation.
    Using 200 (not 303) because HTMX's XHR follows 303 silently — the
    HX-Redirect header on a 303 is never seen by HTMX."""
    res = HTMLResponse(content="", status_code=200)
    res.headers["HX-Redirect"] = url
    if token:
        _set_auth_cookie(res, token)
    return res


# ── GET /auth/login ────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "profile.html", {
        "base_template": _get_base_template(request),
        "user": None,
    })


# ── POST /auth/login ───────────────────────────────────────────────────────────

@router.post("/login")
@limiter.limit("5/minute")
async def handle_login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    email = email.strip().lower()

    if not _validate_email(email):
        return _auth_error_response(request, "Please enter a valid email address.")
    if not _validate_password(password):
        return _auth_error_response(request, "Password must be between 8 and 128 characters.")

    try:
        # ── Beta user — hardcoded credentials, works in any mode ──────────────
        if email == BETA_EMAIL:
            if password != BETA_PASSWORD:
                return _auth_error_response(request, "Invalid email or password.")
            token = _mock_token(email)
            await get_or_create_profile(get_beta_user_id(), email)

        # ── Beta mode — deployed with real AI but no Supabase ─────────────────
        # Only the beta user above is allowed; block everything else
        elif settings.is_beta_mode:
            return _auth_error_response(request, "Invalid email or password.")

        # ── Local sandbox — any credentials (dev convenience) ─────────────────
        elif settings.is_sandbox_mode:
            token = _mock_token(email)
            await get_or_create_profile(_make_mock_user_id(email), email)

        # ── Production Supabase ───────────────────────────────────────────────
        else:
            auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if not auth_res.session:
                return _auth_error_response(request, "Could not sign in. Please try again.")
            token = auth_res.session.access_token
            await get_or_create_profile(str(auth_res.user.id), email)

        if request.headers.get("HX-Request"):
            return _htmx_redirect("/profile", token)

        res = RedirectResponse(url="/profile", status_code=303)
        _set_auth_cookie(res, token)
        return res

    except HTTPException:
        raise
    except Exception as e:
        return _auth_error_response(request, _safe_error(str(e)))


# ── POST /auth/signup ──────────────────────────────────────────────────────────

@router.post("/signup")
@limiter.limit("3/minute")
async def handle_signup(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    email = email.strip().lower()

    if not _validate_email(email):
        return _auth_error_response(request, "Please enter a valid email address.")
    if not _validate_password(password):
        return _auth_error_response(request, "Password must be at least 8 characters.")

    try:
        # Beta mode — no sign-ups, use the beta account to try the app
        if settings.is_beta_mode:
            return _auth_error_response(
                request,
                "Sign-ups are paused during beta. Use the beta account to try the app."
            )

        if settings.is_sandbox_mode:
            token = _mock_token(email)
            await get_or_create_profile(_make_mock_user_id(email), email)
        else:
            auth_res = supabase.auth.sign_up({"email": email, "password": password})
            if not auth_res.session:
                # Email confirmation required
                return _auth_success_response(
                    request,
                    "Account created! Check your email to confirm, then sign in."
                )
            token = auth_res.session.access_token
            await get_or_create_profile(str(auth_res.user.id), email)

        if request.headers.get("HX-Request"):
            return _htmx_redirect("/profile", token)

        res = RedirectResponse(url="/profile", status_code=303)
        _set_auth_cookie(res, token)
        return res

    except HTTPException:
        raise
    except Exception as e:
        return _auth_error_response(request, _safe_error(str(e)))


# ── POST /auth/magic-link ──────────────────────────────────────────────────────

@router.post("/magic-link")
@limiter.limit("3/minute")
async def handle_magic_link(
    request: Request,
    email: str = Form(...)
):
    email = email.strip().lower()

    if not _validate_email(email):
        return _auth_error_response(request, "Please enter a valid email address.")

    try:
        if settings.is_sandbox_mode:
            # Sandbox: skip email, auto-login immediately
            token = _mock_token(email)
            await get_or_create_profile(_make_mock_user_id(email), email)
            if request.headers.get("HX-Request"):
                return _htmx_redirect("/profile", token)
            res = RedirectResponse(url="/profile", status_code=303)
            _set_auth_cookie(res, token)
            return res
        else:
            supabase.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "email_redirect_to": f"{settings.app_url}/auth/callback",
                    "should_create_user": True,
                }
            })
            return _auth_success_response(
                request,
                f"Magic link sent to {email} — check your inbox!"
            )

    except HTTPException:
        raise
    except Exception as e:
        return _auth_error_response(request, _safe_error(str(e)))


# ── GET /auth/callback ─────────────────────────────────────────────────────────
# Handles redirects from: magic link clicks, email confirmation

@router.get("/callback")
async def handle_auth_callback(request: Request):
    params = request.query_params
    error = params.get("error")
    token_hash = params.get("token_hash")
    otp_type = params.get("type", "email")   # 'email', 'magiclink', 'recovery', etc.

    if error or not token_hash:
        return RedirectResponse(url="/profile", status_code=303)

    try:
        auth_res = supabase.auth.verify_otp({
            "token_hash": token_hash,
            "type": otp_type,
        })
        session = auth_res.session
    except Exception:
        session = None

    if not session:
        return RedirectResponse(url="/profile", status_code=303)

    email = session.user.email or ""
    await get_or_create_profile(str(session.user.id), email)

    res = RedirectResponse(url="/profile", status_code=303)
    _set_auth_cookie(res, session.access_token)
    return res


# ── GET /auth/logout ───────────────────────────────────────────────────────────

@router.get("/logout")
async def handle_logout(request: Request):
    try:
        if not settings.is_sandbox_mode:
            supabase.auth.sign_out()
    except Exception:
        pass

    res = RedirectResponse(url="/", status_code=303)
    res.delete_cookie(key="access_token", samesite="lax", path="/")
    return res


# ── Helpers ────────────────────────────────────────────────────────────────────

def _auth_error_response(request: Request, msg: str):
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=f'<span>{msg}</span>',
            headers={"HX-Retarget": "#auth-error", "HX-Reswap": "innerHTML"},
        )
    return templates.TemplateResponse(request, "profile.html", {
        "base_template": _get_base_template(request),
        "user": None,
        "error_message": msg,
    })


def _auth_success_response(request: Request, msg: str):
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=f'<span style="color:rgba(100,220,130,0.95);">{msg}</span>',
            headers={"HX-Retarget": "#auth-error", "HX-Reswap": "innerHTML"},
        )
    return templates.TemplateResponse(request, "profile.html", {
        "base_template": _get_base_template(request),
        "user": None,
        "success_message": msg,
    })
