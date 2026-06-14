from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

ALLOWED_TWITTER_DOMAINS = {"x.com", ".x.com", "twitter.com", ".twitter.com"}
REQUIRED_AUTH_COOKIE = "auth_token"


class CookieImportError(ValueError):
    pass


@dataclass(frozen=True)
class BrowserCookie:
    name: str
    value: str
    domain: str
    path: str
    expires: int | float | None = None
    http_only: bool | None = None
    secure: bool | None = None
    same_site: str | None = None


def parse_cookie_import(payload: dict[str, Any]) -> list[BrowserCookie]:
    raw_cookies = payload.get("cookies")
    if not isinstance(raw_cookies, list) or not raw_cookies:
        raise CookieImportError("Cookie import failed: cookies must be a non-empty array")

    cookies: list[BrowserCookie] = []
    for raw in raw_cookies:
        if not isinstance(raw, dict):
            raise CookieImportError("Cookie import failed: each cookie must be an object")

        name = _required_string(raw, "name")
        value = _required_string(raw, "value")
        domain = _required_string(raw, "domain").lower()
        path = _required_string(raw, "path")

        cookies.append(
            BrowserCookie(
                name=name,
                value=value,
                domain=domain,
                path=path,
                expires=raw.get("expires") or raw.get("expirationDate"),
                http_only=_optional_bool(raw, "httpOnly", "http_only"),
                secure=_optional_bool(raw, "secure"),
                same_site=_optional_same_site(raw.get("sameSite") or raw.get("same_site")),
            )
        )

    validate_twitter_cookies(cookies)
    return cookies


def validate_twitter_cookies(cookies: list[BrowserCookie]) -> None:
    if not cookies:
        raise CookieImportError("Cookie import failed: cookies must be a non-empty array")

    names = set()
    for cookie in cookies:
        if cookie.domain not in ALLOWED_TWITTER_DOMAINS:
            raise CookieImportError("Cookie import failed: cookie domain must belong to x.com or twitter.com")
        if not cookie.value:
            raise CookieImportError("Cookie import failed: cookie value cannot be empty")
        names.add(cookie.name)

    if REQUIRED_AUTH_COOKIE not in names:
        raise CookieImportError("Cookie import failed: missing required auth_token cookie")


def redact_cookies(cookies: list[BrowserCookie]) -> list[dict[str, Any]]:
    return [
        {
            "name": cookie.name,
            "domain": cookie.domain,
            "path": cookie.path,
            "expires": cookie.expires,
            "httpOnly": cookie.http_only,
            "secure": cookie.secure,
            "sameSite": cookie.same_site,
            "value": _redacted_value(cookie.value),
        }
        for cookie in cookies
    ]


def cookie_fingerprint(cookies: list[BrowserCookie]) -> str:
    digest = hashlib.sha256()
    for cookie in sorted(cookies, key=lambda item: (item.domain, item.path, item.name)):
        digest.update(cookie.domain.encode())
        digest.update(b"\0")
        digest.update(cookie.path.encode())
        digest.update(b"\0")
        digest.update(cookie.name.encode())
        digest.update(b"\0")
        digest.update(cookie.value.encode())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def to_playwright_cookies(cookies: list[BrowserCookie]) -> list[dict[str, Any]]:
    return [
        {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path,
            "expires": _playwright_expires(cookie.expires),
            "httpOnly": bool(cookie.http_only),
            "secure": bool(cookie.secure),
            "sameSite": cookie.same_site or "Lax",
        }
        for cookie in cookies
    ]


def _required_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CookieImportError(f"Cookie import failed: missing required cookie field {key}")
    return value.strip()


def _optional_bool(raw: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, bool):
            return value
    return None


def _optional_same_site(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"no_restriction", "none"}:
        return "None"
    if normalized == "lax":
        return "Lax"
    if normalized == "strict":
        return "Strict"
    return None


def _playwright_expires(value: int | float | None) -> int:
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _redacted_value(value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()[:12]
    return f"<redacted:sha256:{digest}>"
