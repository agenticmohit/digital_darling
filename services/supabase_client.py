from supabase import create_client
from config import settings
import jwt
import time
from fastapi import Request

# Create Supabase client
supabase = create_client(settings.supabase_url, settings.supabase_anon_key)

# In-memory mock database for Sandbox Mode testing fallback
_mock_profiles = {}
_mock_usage: dict[str, dict] = {}  # {user_id: {"count": N, "date": "YYYY-MM-DD"}}
# NOTE (production): usage table needs a `reset_date` TEXT column (YYYY-MM-DD).
# Run: ALTER TABLE usage ADD COLUMN reset_date TEXT;
_mock_history = {}

# Verify JWT token from cookie
def verify_jwt(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Get current user payload from request cookies
def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    return verify_jwt(token)

# Get or create user profile
async def get_or_create_profile(user_id: str, email: str) -> dict:
    if settings.is_sandbox_mode:
        if user_id not in _mock_profiles:
            _mock_profiles[user_id] = {"user_id": user_id, "email": email, "plan": "free"}
        return _mock_profiles[user_id]

    result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    
    # Profile does not exist, let's create a new one
    new_profile = {"user_id": user_id, "email": email, "plan": "free"}
    insert_result = supabase.table("profiles").insert(new_profile).execute()
    if insert_result.data:
        return insert_result.data[0]
    return new_profile

# Get profile by user_id
async def get_user_profile(user_id: str) -> dict:
    if settings.is_sandbox_mode:
        if user_id not in _mock_profiles:
            _mock_profiles[user_id] = {"user_id": user_id, "email": "mock_tester@example.com", "plan": "free"}
        return _mock_profiles[user_id]

    result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    return {"user_id": user_id, "email": "", "plan": "free"}

# Update user plan
async def update_user_plan(user_id: str, plan: str) -> dict | None:
    if settings.is_sandbox_mode:
        profile = await get_user_profile(user_id)
        profile["plan"] = plan
        _mock_profiles[user_id] = profile
        return profile

    result = supabase.table("profiles").update({"plan": plan}).eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    return None

# Get daily usage count — resets automatically each calendar day (UTC)
async def get_user_usage(user_id: str) -> int:
    today = time.strftime("%Y-%m-%d", time.gmtime())

    if settings.is_sandbox_mode:
        entry = _mock_usage.get(user_id)
        if not entry or entry.get("date") != today:
            return 0
        return entry.get("count", 0)

    result = supabase.table("usage").select("count, reset_date").eq("user_id", user_id).execute()
    if result.data:
        row = result.data[0]
        if row.get("reset_date") != today:
            return 0  # different day — treat as fresh
        return row.get("count", 0)
    return 0

# Increment daily usage count (auto-resets if day rolled over)
async def increment_user_usage(user_id: str) -> int:
    today = time.strftime("%Y-%m-%d", time.gmtime())

    if settings.is_sandbox_mode:
        entry = _mock_usage.get(user_id, {})
        if entry.get("date") != today:
            _mock_usage[user_id] = {"count": 1, "date": today}
            return 1
        entry["count"] = entry.get("count", 0) + 1
        _mock_usage[user_id] = entry
        return entry["count"]

    existing = supabase.table("usage").select("count, reset_date").eq("user_id", user_id).execute()
    if existing.data:
        row = existing.data[0]
        new_count = 1 if row.get("reset_date") != today else row.get("count", 0) + 1
        result = supabase.table("usage").update({"count": new_count, "reset_date": today}).eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]["count"]
    else:
        result = supabase.table("usage").insert({"user_id": user_id, "count": 1, "reset_date": today}).execute()
        if result.data:
            return result.data[0]["count"]
    return 1

# Reset daily usage (manual override if needed)
async def reset_user_usage(user_id: str) -> int:
    today = time.strftime("%Y-%m-%d", time.gmtime())

    if settings.is_sandbox_mode:
        _mock_usage[user_id] = {"count": 0, "date": today}
        return 0

    supabase.table("usage").update({"count": 0, "reset_date": today}).eq("user_id", user_id).execute()
    return 0

# Retrieve history list
async def get_user_history(user_id: str) -> list[dict]:
    if settings.is_sandbox_mode:
        return _mock_history.get(user_id, [])

    result = supabase.table("history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    if result.data:
        return result.data
    return []

# Add entry to history table
async def add_history_entry(user_id: str, chat_snippet: str, score: int, label: str, result_dict: dict) -> dict | None:
    # Use first 80 characters of snippet to avoid breaking UI layouts
    snippet = chat_snippet.strip()
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
        
    entry = {
        "user_id": user_id,
        "chat_snippet": snippet,
        "score": score,
        "label": label,
        "result": result_dict,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    if settings.is_sandbox_mode:
        if user_id not in _mock_history:
            _mock_history[user_id] = []
        _mock_history[user_id].insert(0, entry) # Prepend to put newest first
        return entry

    result = supabase.table("history").insert(entry).execute()
    if result.data:
        return result.data[0]
    return None

