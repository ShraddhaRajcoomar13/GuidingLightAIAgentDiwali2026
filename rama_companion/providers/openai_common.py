import requests
from providers.base import ApiError
BASE = "https://api.openai.com/v1"

def _check(r):
    if r.ok: return
    try: code = (r.json().get("error") or {}).get("code") or ""
    except Exception: code = ""
    s = r.status_code
    if s == 401: raise ApiError("auth")
    if s == 402 or (s == 429 and code == "insufficient_quota"): raise ApiError("credits")
    if s == 429: raise ApiError("rate")
    raise ApiError("other", f"HTTP {s}")      # never include server text (may echo key fragments)

def post(path, key, timeout=60, **kw):
    if not key: raise ApiError("nokey")
    try:
        r = requests.post(BASE + path, headers={"Authorization": "Bearer " + key}, timeout=timeout, **kw)
    except (requests.ConnectionError, requests.Timeout):
        raise ApiError("network")
    except requests.RequestException:
        raise ApiError("other")
    _check(r)
    return r

def validate_key(key):
    """returns 'ok' | 'auth' | 'network'"""
    try:
        r = requests.get(BASE + "/models", headers={"Authorization": "Bearer " + key}, timeout=15)
    except requests.RequestException:
        return "network"
    return "auth" if r.status_code == 401 else "ok"
