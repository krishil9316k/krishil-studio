"""
THE MANAGER
Looks at every new photo/video in inbox/, understands it with AI, and hands a
separate brief to each employee that should handle it:
    queues/instagram/new/<id>.json   -> Instagram employee
    queues/whatsapp/new/<id>.json    -> WhatsApp employee
It never captions, edits or posts. Lane guard stops it touching anything else.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import ai  # noqa: E402
from common.lanes import Lane  # noqa: E402
from common.media import kind_of, open_image, to_jpeg, video_frame  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
lane = Lane("MANAGER")


def analyse(rules: dict, preview: bytes, note: str) -> dict:
    cats = rules["categories"]
    if not ai.available():
        return {"category": "other", "description": note or "New photo from the shop", "safe": True,
                "reason": "", "key_points": [note] if note else [], "quality_ok": True}
    prompt = f"""You are the MANAGER of a small xerox/printing/stationery shop called {rules['shop']['name']} in Junagadh, Gujarat.
The owner uploaded this photo/video frame. Owner's note: "{note or 'none'}".
Shop services: {', '.join(rules['shop']['services'])}.
Decide:
- category: one of {cats}
- description: 1-2 plain sentences of what is shown (products, colours, quantities, any visible price)
- key_points: up to 4 short selling points a caption writer could use (only from what is visible or in the note)
- quality_ok: false if blurry/dark/unusable
- safe: false if any of these is true: {rules['never_route_if']}
- reason: why, if not safe or not quality_ok
Return JSON with exactly these keys."""
    out = ai.ask_json(prompt, preview)
    if out.get("category") not in cats:
        out["category"] = "other"
    return out


def main():
    rules = lane.rules()
    status = {"last_run": datetime.now(IST).isoformat(timespec="minutes"), "routed": [], "held": []}
    for f in lane.list("inbox"):
        if f.suffix == ".json" or kind_of(f) == "other":
            continue
        meta_path = f.with_name(f.name + ".json")
        meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
        note = meta.get("note", "")
        send_to = meta.get("send_to", "auto")
        kind = kind_of(f)
        task_id = f.stem.split("__")[0] if "__" in f.stem else datetime.now(IST).strftime("%Y%m%d%H%M%S")

        preview = video_frame(f) if kind == "video" else to_jpeg(open_image(f.read_bytes()), max_side=1280)
        try:
            info = analyse(rules, preview, note)
        except Exception as e:  # AI down/limit: try again next run, keep file in inbox
            print("AI error, will retry later:", e)
            continue

        original = f"media/originals/{f.name}"
        lane.move(f, original)
        if meta_path.exists():
            lane.move(meta_path, f"media/originals/{meta_path.name}")

        if not info.get("safe", True) or not info.get("quality_ok", True):
            status["held"].append({"id": task_id, "file": original, "reason": info.get("reason", "")})
            print("HELD", task_id, info.get("reason"))
            continue

        route = send_to if send_to in ("instagram", "whatsapp", "both") else rules["routing"].get(info["category"], "instagram")
        targets = ["instagram", "whatsapp"] if route == "both" else [route]
        brief = {
            "id": task_id, "kind": kind, "original": original, "note": note,
            "category": info["category"], "description": info.get("description", ""),
            "key_points": info.get("key_points", []), "created": datetime.now(IST).isoformat(timespec="minutes"),
        }
        for t in targets:  # each employee gets its OWN copy — they never share a task file
            lane.write_json(f"queues/{t}/new/{task_id}.json", dict(brief, assigned_to=t))
        status["routed"].append({"id": task_id, "to": targets, "category": info["category"]})
        print("ROUTED", task_id, "->", targets)

    lane.write_json("status/manager.json", status)


if __name__ == "__main__":
    main()
