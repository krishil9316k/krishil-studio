"""
Free AI brain: Google Gemini API (free tier from Google AI Studio).
Model is set by the GEMINI_MODEL secret/variable (default gemini-2.5-flash),
so if Google renames free models you only change one setting.
If no key is set, workers fall back to simple template captions — nothing breaks.
"""
import base64
import json
import os
import time

import requests

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KEY = os.environ.get("GEMINI_API_KEY", "")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"


def available() -> bool:
    return bool(KEY)


def ask_json(prompt: str, image_bytes: bytes | None = None, mime: str = "image/jpeg", retries: int = 3) -> dict:
    """Send prompt (+ optional image) and get a JSON object back."""
    if not KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    parts = [{"text": prompt}]
    if image_bytes:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}})
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
    }
    last = None
    for attempt in range(retries):
        r = requests.post(URL.format(m=MODEL), params={"key": KEY}, json=body, timeout=90)
        if r.status_code == 429 or r.status_code >= 500:  # free-tier limit or busy: wait and retry
            last = f"{r.status_code} {r.text[:200]}"
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        return json.loads(text)
    raise RuntimeError(f"Gemini failed: {last}")
