from fastapi import APIRouter, Request, HTTPException, Form, Header, status
from fastapi.responses import JSONResponse
import razorpay
from config import settings
from services.supabase_client import get_current_user, update_user_plan
import hmac
import hashlib
import time
import json

router = APIRouter(prefix="/payments")

try:
    rz_client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
except Exception:
    rz_client = None

_PLAN_PRICE_PAISE = {
    "paid": 29900,   # ₹299
}

def _verify_razorpay_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

def _create_order(plan: str, user_id: str) -> dict:
    if not rz_client:
        raise ValueError("Payment gateway is not configured.")
    amount = _PLAN_PRICE_PAISE.get(plan)
    if not amount:
        raise ValueError("Invalid plan selected.")
    return rz_client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": f"dd_{plan}_{int(time.time())}",
        "notes": {"user_id": user_id, "plan": plan}
    })

# ── POST /payments/create-order ────────────────────────────────────────────────

@router.post("/create-order")
async def handle_create_order(request: Request, plan: str = Form("paid")):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Sign in to upgrade your plan.")

    if plan not in _PLAN_PRICE_PAISE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid plan selected.")

    try:
        order = _create_order(plan, user["sub"])
        return JSONResponse(content={
            "id": order["id"],
            "amount": order["amount"],
            "key": settings.razorpay_key_id,
            "email": user.get("email", ""),
            "plan": plan
        })
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Could not initialise payment. Please try again.")

# ── POST /payments/webhook ─────────────────────────────────────────────────────

@router.post("/webhook")
async def handle_webhook(request: Request,
                         x_razorpay_signature: str = Header(None)):
    body = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Missing signature.")

    if not _verify_razorpay_signature(body, x_razorpay_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
        event = payload.get("event")

        if event in ("order.paid", "payment.captured"):
            ep = payload.get("payload", {})
            entity = (ep.get("payment") or ep.get("order") or {}).get("entity", {})
            notes = entity.get("notes", {})
            user_id = notes.get("user_id")
            plan = notes.get("plan", "paid")

            if user_id and plan in _PLAN_PRICE_PAISE:
                await update_user_plan(user_id, plan)

        return JSONResponse(content={"status": "ok"})

    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Webhook processing error.")
