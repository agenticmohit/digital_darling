from cachetools import TTLCache
import hashlib

# In-memory TTL cache: 500 items capacity, 1 hour (3600 seconds) expiration
_cache = TTLCache(maxsize=500, ttl=3600)

# Generate a cached key based on the sha256 hash of the cleaned text
def make_key(text: str) -> str:
    cleaned = text.strip().lower()
    return hashlib.sha256(cleaned.encode()).hexdigest()

# Retrieve item from cache
def cache_get(key: str) -> dict | None:
    return _cache.get(key)

# Put item into cache
def cache_set(key: str, value: dict) -> None:
    _cache[key] = value
