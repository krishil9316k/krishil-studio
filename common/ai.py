"""
Free AI brain: Google Gemini API (free tier from Google AI Studio).
Tries several free models in order, so a renamed/retired model or a busy one
never stops the system. Set GEMINI_MODEL (repo variable) to put your own first.
If every model fails, callers fall back to simple template text — nothing gets stuck.
"""
import base64
import json
import os
import time

import requests

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
MODELS = [m for m in [os.environ.get("GEMINI_MODEL", "").strip(),
                      "gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3-flash-preview",
                      "gemini-2.5-flash-lite", "gemini-flash-latest"] if m]
MODELS = list(dict.fromkeys(MODELS))
last_error = ""


def _safe(text: str) -> str:
    """Never let the key appear in logs or status files (the repo is public)."""
    return text.replace(KEY, "***") if KEY else text


def available() -> bool:
    return bool(KEY)


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1] if start >= 0 else text)


def ask_json(prompt: str, image_bytes: bytes | None = None, mime: str = "image/jpeg") -> dict:
    """Send prompt (+ optional image) and get a JSON object back. Raises RuntimeError if all models fail."""
    global last_error
    if not KEY:
        raise RuntimeError("GEMINI_API_KEY secret is missing")
    parts = [{"text": prompt}]
    if image_bytes:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8}}
    errors = []
    for model in MODELS:
        for attempt in range(2):
            try:
                r = requests.post(URL.format(m=model), headers={"x-goog-api-key": KEY}, json=body, timeout=90)
            except requests.RequestException as e:
                errors.append(f"{model}: network error {type(e).__name__}")
                time.sleep(5)
                continue
            if r.status_code == 200:
                try:
                    data = r.json()
                    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
                    print(f"AI ok ({model})")
                    return _parse(text)
                except Exception as e:  # odd reply: try next model
                    errors.append(f"{model}: bad reply {e}")
                    break
            errors.append(_safe(f"{model}: {r.status_code} {r.text[:160]}"))
            if r.status_code in (400, 401, 403) and "API key" in r.text:
                last_error = _safe("Gemini key is wrong or not active: " + r.text[:160])
                raise RuntimeError(last_error)
            if r.status_code in (429, 500, 503) and attempt == 0:
                time.sleep(8)
                continue
            break  # 404 / other: next model
    last_error = _safe(" | ".join(e[:140] for e in errors))[:600]
    raise RuntimeError("All Gemini models failed: " + last_error)
