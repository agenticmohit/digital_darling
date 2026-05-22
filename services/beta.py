"""
Beta user — in-memory tracking for the hardcoded beta tester account.
Works without Supabase. Usage resets each calendar day (UTC).
"""
import hashlib
import time

BETA_EMAIL    = "beta_user@dd.com"
BETA_PASSWORD = "beta1234"
BETA_DAILY_LIMIT = 5

# In-memory counter: resets on each new UTC date
_usage: dict = {"date": None, "count": 0}


def get_beta_user_id() -> str:
    """Deterministic UUID-style ID for the beta user (matches _make_mock_user_id)."""
    h = hashlib.md5(BETA_EMAIL.strip().lower().encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def is_beta_user(user: dict) -> bool:
    return (
        user.get("email") == BETA_EMAIL
        or user.get("sub") == get_beta_user_id()
    )


def get_beta_usage() -> int:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _usage["date"] != today:
        _usage["date"] = today
        _usage["count"] = 0
    return _usage["count"]


def increment_beta_usage() -> int:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _usage["date"] != today:
        _usage["date"] = today
        _usage["count"] = 0
    _usage["count"] += 1
    return _usage["count"]


def beta_reads_left() -> int:
    return max(0, BETA_DAILY_LIMIT - get_beta_usage())
