import json
import os
import time
from typing import Any


def load_cookies(cookie_path: str) -> list[dict[str, Any]]:
    if not os.path.exists(cookie_path):
        return []
    with open(cookie_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "cookies" in data:
        cookies = data.get("cookies")
    else:
        cookies = data
    if not isinstance(cookies, list):
        return []
    return [c for c in cookies if isinstance(c, dict)]


def save_cookies(cookie_path: str, cookies: list[dict[str, Any]]):
    payload = {
        "saved_at": int(time.time()),
        "cookies": cookies,
    }
    with open(cookie_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def sanitize_cookie(cookie: dict[str, Any]) -> dict[str, Any]:
    """只保留 selenium add_cookie 常见字段，避免不兼容字段导致整体失败。"""
    allowed_keys = {
        "name",
        "value",
        "domain",
        "path",
        "expiry",
        "secure",
        "httpOnly",
        "sameSite",
    }
    sanitized = {k: v for k, v in cookie.items() if k in allowed_keys}

    # expiry 需要是 int
    if "expiry" in sanitized and sanitized["expiry"] is not None:
        try:
            sanitized["expiry"] = int(sanitized["expiry"])
        except Exception:
            sanitized.pop("expiry", None)

    return sanitized
