"""
INSTAGRAM EMPLOYEE  (reads only rules/instagram_rules.json, works only in its own lane)

  python workers/instagram_worker.py prepare   # take new briefs -> caption + edit -> draft/approved -> slot
  python workers/instagram_worker.py publish   # post anything whose time slot has come

Task life:  new -> draft -> (you approve in app) -> approved -> scheduled -> published
            (auto_publish=true skips the draft step)
"""
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import ai  # noqa: E402
from common.lanes import ROOT, Lane  # noqa: E402
from common.media import brand, fit_canvas, open_image, prepare_video, to_jpeg, video_frame  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
lane = Lane("INSTAGRAM")
TASKS = "queues/instagram/tasks"


def now():
    return datetime.now(IST)


# ----------------------------------------------------------------- captions
def clean_hashtags(tags, rules):
    out = []
    for t in list(rules["brand_hashtags"]) + list(tags or []):
        t = "#" + re.sub(r"[^\w]", "", str(t).lstrip("#"))
        if len(t) > 1 and t.lower() not in [x.lower() for x in out]:
            out.append(t)
    return out[: rules["max_hashtags"]]


def write_caption(rules, brief, preview: bytes) -> dict:
    if not ai.available():
        body = f"✨ {brief['description']}\n\n📍 KRISHIL edu hub, Madhuram, Junagadh\n📲 Order on WhatsApp: 8347902010"
        return {"caption": body, "hashtags": clean_hashtags([], rules)}
    prompt = f"""You are the INSTAGRAM social media employee of KRISHIL edu hub (xerox, printing, stationery shop, Junagadh).
Write ONE Instagram caption for this {brief['kind']}.
What it shows: {brief['description']}
Selling points: {brief['key_points']}
Owner's note: {brief['note'] or 'none'}
Language: {rules['caption_language']}. Style: {rules['style']}.
Rate card (only use these prices, only if relevant): {rules['rate_card']}
Never: {rules['do_not']}
Return JSON: {{"caption": "caption text WITHOUT hashtags, under 600 characters", "hashtags": ["up to 3 relevant local/niche tags"], "hook": "first line"}}"""
    out = ai.ask_json(prompt, preview)
    out["hashtags"] = clean_hashtags(out.get("hashtags"), rules)
    return out


def full_caption(task, rules):
    text = (task.get("caption") or "").strip()
    text = re.sub(r"(?<!\w)#\w+", "", text).strip()  # hashtags only from the hashtag list
    tags = clean_hashtags([h for h in task.get("hashtags", [])], rules)
    return (text + "\n\n" + " ".join(tags)).strip()[: rules["caption_max_chars"]]


# ----------------------------------------------------------------- prepare
def prepare(rules):
    for f in lane.list("queues/instagram/new", {".json"}):
        brief = lane.read_json(f)
        tid = brief["id"]
        src = lane.check_read(brief["original"])
        logo = ROOT / "assets/logo.png"
        strip = "KRISHIL edu hub • Madhuram, Junagadh • WA 8347902010"
        try:
            if brief["kind"] == "image":
                img = open_image(src.read_bytes())
                out = brand(fit_canvas(img, *rules["image_size"]), logo, strip)
                jpg = to_jpeg(out)
                media_rel = f"media/instagram/{tid}.jpg"
                lane.write_bytes(media_rel, jpg)
                preview = to_jpeg(out, max_side=1024)
            else:
                media_rel = f"media/instagram/{tid}.mp4"
                dst = lane.check_write(media_rel)
                dst.parent.mkdir(parents=True, exist_ok=True)
                prepare_video(src, dst, *rules["reel_size"], rules["reel_max_seconds"])
                preview = video_frame(dst)
            cap = write_caption(rules, brief, preview)
        except Exception as e:
            print("prepare failed, retry next run:", tid, e)
            continue
        task = dict(brief, media=media_rel, caption=cap.get("caption", ""), hashtags=cap.get("hashtags", []),
                    status="approved" if rules.get("auto_publish") else "draft", slot=None, attempts=0,
                    prepared=now().isoformat(timespec="minutes"))
        lane.write_json(f"{TASKS}/{tid}.json", task)
        lane.check_write(f).unlink()
        print("PREPARED", tid, task["status"])
    schedule(rules)


def all_tasks():
    return [(f, lane.read_json(f)) for f in lane.list(TASKS, {".json"})]


def schedule(rules):
    """Give approved posts the next free time slots, mixing categories."""
    tasks = all_tasks()
    taken = {t["slot"] for _, t in tasks if t.get("slot") and t["status"] in ("scheduled", "published")}
    per_day = {}
    for s in taken:
        per_day[s[:10]] = per_day.get(s[:10], 0) + 1
    waiting = sorted([(f, t) for f, t in tasks if t["status"] == "approved"], key=lambda x: x[1]["created"])
    if not waiting:
        return
    # free slots for the next 14 days
    slots, start = [], now() + timedelta(minutes=10)
    for d in range(15):
        day = (start + timedelta(days=d)).date()
        for hm in rules["time_slots_ist"][: rules["posts_per_day"]]:
            h, m = map(int, hm.split(":"))
            dt = datetime(day.year, day.month, day.day, h, m, tzinfo=IST)
            key = dt.isoformat(timespec="minutes")
            if dt > start and key not in taken and per_day.get(key[:10], 0) < rules["posts_per_day"]:
                slots.append(key)
    last_cat = None
    for slot in slots:
        if not waiting:
            break
        pick = next((x for x in waiting if x[1]["category"] != last_cat), waiting[0])  # variety
        waiting.remove(pick)
        f, t = pick
        t["slot"], t["status"] = slot, "scheduled"
        per_day[slot[:10]] = per_day.get(slot[:10], 0) + 1
        last_cat = t["category"]
        lane.write_json(f, t)
        print("SCHEDULED", t["id"], slot)


# ----------------------------------------------------------------- publish
class IG:
    def __init__(self, ver):
        self.token = os.environ["IG_ACCESS_TOKEN"]
        self.uid = os.environ["IG_USER_ID"]
        self.base = f"https://graph.instagram.com/{ver}"
        self.ver = ver

    def _post(self, path, data):
        r = requests.post(f"{self.base}/{path}", data=dict(data, access_token=self.token), timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"{path}: {r.status_code} {r.text[:300]}")
        return r.json()

    def wait_ready(self, cid, tries=40):
        for _ in range(tries):
            r = requests.get(f"{self.base}/{cid}", params={"fields": "status_code,status", "access_token": self.token}, timeout=60).json()
            if r.get("status_code") == "FINISHED":
                return
            if r.get("status_code") in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {r}")
            time.sleep(15)
        raise RuntimeError("container not ready in time")

    def image(self, url, caption):
        cid = self._post(f"{self.uid}/media", {"image_url": url, "caption": caption})["id"]
        self.wait_ready(cid, 10)
        return self._post(f"{self.uid}/media_publish", {"creation_id": cid})["id"]

    def reel(self, path: Path, caption):
        c = self._post(f"{self.uid}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true"})
        uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{self.ver}/{c['id']}"
        data = path.read_bytes()
        r = requests.post(uri, data=data, timeout=600, headers={
            "Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(len(data))})
        if r.status_code >= 400:
            raise RuntimeError(f"upload: {r.status_code} {r.text[:300]}")
        self.wait_ready(c["id"])
        return self._post(f"{self.uid}/media_publish", {"creation_id": c["id"]})["id"]


def publish(rules):
    status = {"last_run": now().isoformat(timespec="minutes"), "published": [], "errors": []}
    if not (os.environ.get("IG_ACCESS_TOKEN") and os.environ.get("IG_USER_ID")):
        status["errors"].append("Instagram not connected yet (IG_ACCESS_TOKEN / IG_USER_ID secrets missing)")
        lane.write_json("status/instagram.json", status)
        print(status["errors"][0])
        return
    ig = IG(rules["graph_api_version"])
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    due = sorted([(f, t) for f, t in all_tasks() if t["status"] == "scheduled" and t["slot"] <= now().isoformat(timespec="minutes")],
                 key=lambda x: x[1]["slot"])
    ledger_path = "queues/instagram/published_ledger.json"
    ledger = lane.read_json(ledger_path) if lane.check_read(ledger_path).exists() else {}
    for f, t in due[:1]:  # max one post per run — keeps spacing natural
        if t["id"] in ledger:  # already posted once — never post twice
            t.update(status="published", ig_media_id=ledger[t["id"]])
            lane.write_json(f, t)
            continue
        try:
            cap = full_caption(t, rules)
            if t["media"].endswith(".jpg"):
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/{t['media']}"
                mid = ig.image(url, cap)
            else:
                mid = ig.reel(lane.check_read(t["media"]), cap)
            ledger[t["id"]] = mid
            lane.write_json(ledger_path, ledger)
            t.update(status="published", ig_media_id=mid, published=now().isoformat(timespec="minutes"))
            status["published"].append(t["id"])
            print("PUBLISHED", t["id"], mid)
        except Exception as e:
            t["attempts"] = t.get("attempts", 0) + 1
            t["last_error"] = str(e)[:400]
            if t["attempts"] >= 3:
                t["status"] = "failed"
            status["errors"].append(f"{t['id']}: {str(e)[:200]}")
            print("ERROR", t["id"], e)
        lane.write_json(f, t)
    lane.write_json("status/instagram.json", status)


if __name__ == "__main__":
    rules = lane.rules()
    {"prepare": prepare, "publish": publish}[sys.argv[1] if len(sys.argv) > 1 else "prepare"](rules)
