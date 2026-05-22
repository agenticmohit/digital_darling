from fastapi import APIRouter, Request, HTTPException, Form, File, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from services.supabase_client import (
    get_current_user,
    get_user_profile,
    get_user_usage,
    increment_user_usage,
    add_history_entry
)
from services.cache import make_key, cache_get, cache_set
from services.ai import analyze_chat, extract_chat_from_screenshot

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB


@router.post("/decode", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def decode_chat(
    request: Request,
    chat: str = Form(None),
    screenshot: UploadFile = File(None),
):
    # ── 1. Resolve input — screenshot takes priority over pasted text ──────────
    from_screenshot = False

    if screenshot and screenshot.filename:
        mime = (screenshot.content_type or "").lower().split(";")[0].strip()
        if mime not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload a JPEG, PNG, or WEBP screenshot.",
            )

        image_bytes = await screenshot.read()
        if len(image_bytes) > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image too large. Crop it under 4 MB.",
            )

        extracted = await extract_chat_from_screenshot(image_bytes, mime)
        if not extracted:
            return templates.TemplateResponse(
                request, "partials/error.html",
                {"detail": "Couldn't read that screenshot. Try a clearer crop, or paste the chat manually."},
            )
        chat = extracted
        from_screenshot = True

    # ── 2. Input validation ────────────────────────────────────────────────────
    if not chat or not chat.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paste a chat or upload a screenshot first.",
        )
    chat_text = chat.strip()

    if len(chat_text) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too short — needs more of the conversation.",
        )
    if len(chat_text) > 8000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too long — trim it down a bit.",
        )

    # ── 3. Auth check ──────────────────────────────────────────────────────────
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to decode chats.",
        )

    user_id = user["sub"]

    # ── 4. Usage / plan gate ───────────────────────────────────────────────────
    profile = await get_user_profile(user_id)
    plan = profile.get("plan", "free").lower()

    if plan != "paid":
        usage_count = await get_user_usage(user_id)
        if usage_count >= 3:
            return templates.TemplateResponse(request, "partials/paywall.html")

    # ── 5. Cache lookup ────────────────────────────────────────────────────────
    cache_key = make_key(chat_text)
    cached = cache_get(cache_key)
    if cached:
        return templates.TemplateResponse(
            request, "partials/result.html",
            {"result": cached, "from_screenshot": from_screenshot},
        )

    # ── 6. AI analysis ─────────────────────────────────────────────────────────
    result = await analyze_chat(chat_text)

    if result.get("label") == "ERROR" or result.get("error"):
        return templates.TemplateResponse(
            request, "partials/error.html",
            {"detail": result.get("verdict", "Analysis failed — try again.")},
        )

    # ── 7. Persist ─────────────────────────────────────────────────────────────
    await increment_user_usage(user_id)
    await add_history_entry(user_id, chat_text, result["score"], result["label"], result)
    cache_set(cache_key, result)

    # ── 8. Respond ─────────────────────────────────────────────────────────────
    return templates.TemplateResponse(
        request, "partials/result.html",
        {"result": result, "from_screenshot": from_screenshot},
    )
