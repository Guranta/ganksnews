from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.browser.cookies import BrowserCookie, redact_cookies, to_playwright_cookies
from app.models import BrowserProfile


def ensure_profile_dir(profile: BrowserProfile) -> Path:
    profile_dir = Path(profile.profile_path)
    (profile_dir / "health").mkdir(parents=True, exist_ok=True)
    (profile_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (profile_dir / "user-data-dir").mkdir(parents=True, exist_ok=True)
    return profile_dir


def write_imported_cookies(profile: BrowserProfile, cookies: list[BrowserCookie]) -> Path:
    profile_dir = ensure_profile_dir(profile)
    path = profile_dir / "cookies.imported.json"
    payload = {
        "imported_at": datetime.now(UTC).isoformat(),
        "cookies": [cookie.__dict__ for cookie in cookies],
        "redacted_cookies": redact_cookies(cookies),
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def write_storage_state(profile: BrowserProfile, cookies: list[BrowserCookie]) -> Path:
    profile_dir = ensure_profile_dir(profile)
    path = profile_dir / "storage_state.json"
    payload = {"cookies": to_playwright_cookies(cookies), "origins": []}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def write_health_summary(profile: BrowserProfile, summary: dict[str, Any]) -> Path:
    profile_dir = ensure_profile_dir(profile)
    path = profile_dir / "health" / "latest.json"
    path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, default=str), encoding="utf-8")
    return path
