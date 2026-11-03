"""
WHATSAPP EMPLOYEE  (reads only rules/whatsapp_rules.json, works only in its own lane)

  python workers/whatsapp_worker.py prepare   # new briefs -> Gujarati+English message + WhatsApp-sized media
  python workers/whatsapp_worker.py daily     # morning education-news update for teachers

It PREPARES. You send with one tap from the Manager app ("Share to WhatsApp"),
choosing your Channel / group / broadcast list. No bots, no ban risk, zero cost.
"""
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import ai  # noqa: E402
from common.lanes import ROOT, Lane  # noqa: E402
from common.media import brand, open_image, prepare_video, to_jpeg, video_frame  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
lane = Lane("WHATSAPP")
READY = "queues/whatsapp/ready"
SIGN = "— KRISHIL edu hub, Madhuram, Junagadh\n📲 WhatsApp: 8347902010"


def now():
    return datetime.now(IST)


def ready_items():
    return [(f, lane.read_json(f)) for f in lane.list(READY, {".json"})]


def next_promo_day(rules) -> str:
    """At most N promotional messages per day: find the first day with room."""
    used = {}
    for _, t in ready_items():
        if t.get("type") == "promo" and t["status"] in ("ready", "sent"):
            used[t["send_on"]] = used.get(t["send_on"], 0) + 1
    d = now().date()
    while used.get(d.isoformat(), 0) >= rules["max_promo_messages_per_day"]:
        d += timedelta(days=1)
    return d.isoformat()


def simple_message(brief) -> str:
    head = brief.get("note") or brief.get("description") or "નવું સ્ટોક આવી ગયું છે!"
    return f"🙏 નમસ્તે!\n*{head}*\n\nCopies • Prints • Stationery • Binding • ID cards\n\n{SIGN}"


def write_message(rules, brief, preview) -> str:
    if not ai.available():
        return simple_message(brief)
    prompt = f"""You are the WHATSAPP employee of KRISHIL edu hub (xerox, printing, stationery shop in Junagadh).
Write ONE WhatsApp message for our customers: {rules['audience']}.
It goes with this {brief['kind']}. What it shows: {brief['description']}. Points: {brief['key_points']}.
Owner's note: {brief['note'] or 'none'}.
Language: {rules['language']}. Style: {rules['style']}.
Never: {rules['do_not']}
Use WhatsApp formatting (*bold* for the key line). End exactly with:
{SIGN}
Return JSON: {{"message": "..."}}"""
    try:
        return ai.ask_json(prompt, preview)["message"]
    except Exception as e:
        print("AI message failed, using simple message:", e)
        return simple_message(brief)


def prepare(rules):
    for f in lane.list("queues/whatsapp/new", {".json"}):
        brief = lane.read_json(f)
        tid = brief["id"]
        src = lane.check_read(brief["original"])
        try:
            if brief["kind"] == "image":
                img = open_image(src.read_bytes())
                img = brand(img, ROOT / "assets/logo.png", "KRISHIL edu hub • WA 8347902010")
                media_rel = f"media/whatsapp/{tid}.jpg"
                lane.write_bytes(media_rel, to_jpeg(img, quality=85, max_side=rules["image_max_side"]))
                preview = to_jpeg(img, max_side=1024)
            else:
                media_rel = f"media/whatsapp/{tid}.mp4"
                dst = lane.check_write(media_rel)
                dst.parent.mkdir(parents=True, exist_ok=True)
                prepare_video(src, dst, 720, 1280, 60)
                preview = video_frame(dst)
            msg = write_message(rules, brief, preview)
        except Exception as e:
            print("prepare failed, retry next run:", tid, e)
            continue
        item = {"id": tid, "type": "promo", "category": brief["category"], "media": media_rel, "message": msg,
                "send_on": next_promo_day(rules), "status": "ready", "prepared": now().isoformat(timespec="minutes")}
        lane.write_json(f"{READY}/{tid}.json", item)
        lane.check_write(f).unlink()
        print("READY", tid, "for", item["send_on"])


# ----------------------------------------------------------------- daily news
def fetch_news(rules, limit=12):
    seen, items = set(), []
    cutoff = now() - timedelta(days=2)
    for url in rules["daily_update"]["news_feeds"]:
        try:
            xml = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).content
            for it in ET.fromstring(xml).iter("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                try:
                    when = parsedate_to_datetime(it.findtext("pubDate"))
                except Exception:
                    continue
                key = re.sub(r"\W", "", title.lower())[:60]
                if when >= cutoff and key not in seen:
                    seen.add(key)
                    items.append({"title": title, "link": link, "when": when.isoformat()})
        except Exception as e:
            print("feed error", url, e)
    items.sort(key=lambda x: x["when"], reverse=True)
    return items[:limit]


def daily(rules):
    cfg = rules["daily_update"]
    today = now().date().isoformat()
    rel = f"{READY}/daily-{today}.json"
    if not cfg["enabled"] or lane.check_write(rel).exists():
        return
    h, m = map(int, cfg["ready_by_ist"].split(":"))
    if now() < now().replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(minutes=90):
        return  # too early (e.g. midnight) — wait for the morning run
    news = fetch_news(rules)
    if ai.available() and news:
        prompt = f"""You are the WHATSAPP employee of KRISHIL edu hub, Junagadh. Prepare today's short morning update
for teachers, professors and college trustees. From these headlines pick the {cfg['news_items']} most useful
for Gujarat schools/colleges (exams, results, circulars, admissions, holidays). Summarise each in ONE line in
your own words (Gujarati, with a short English hint), each followed by its link on the next line.
Do NOT invent anything not in the headline. If fewer are relevant, use fewer.
Then add one helpful line about the shop (e.g. bulk printing of question papers / ID cards / binding) — no prices
unless given. Start with "🌅 *સુપ્રભાત* — આજનું શિક્ષણ અપડેટ ({today})". End exactly with:
{SIGN}
Headlines: {news}
Return JSON: {{"message": "..."}}"""
        try:
            msg = ai.ask_json(prompt)["message"]
        except Exception as e:
            print("AI error, using plain headlines:", e)
            lines = [f"• {n['title']}\n{n['link']}" for n in news[: cfg["news_items"]]]
            msg = f"🌅 *સુપ્રભાત* — આજનું શિક્ષણ અપડેટ ({today})\n\n" + "\n\n".join(lines) + f"\n\n{SIGN}"
    elif news:
        lines = [f"• {n['title']}\n{n['link']}" for n in news[: cfg["news_items"]]]
        msg = f"🌅 *સુપ્રભાત* — આજનું શિક્ષણ અપડેટ ({today})\n\n" + "\n\n".join(lines) + f"\n\n{SIGN}"
    else:
        print("no fresh news today")
        return
    lane.write_json(rel, {"id": f"daily-{today}", "type": "daily", "media": None, "message": msg,
                          "send_on": today, "status": "ready", "prepared": now().isoformat(timespec="minutes")})
    print("DAILY ready", today)


def run(rules):
    prepare(rules)
    daily(rules)
    lane.write_json("status/whatsapp.json", {"last_run": now().isoformat(timespec="minutes"),
                                             "ready_today": sum(1 for _, t in ready_items()
                                                                if t["status"] == "ready" and t["send_on"] <= now().date().isoformat())})


if __name__ == "__main__":
    rules = lane.rules()
    {"prepare": prepare, "daily": daily, "run": run}[sys.argv[1] if len(sys.argv) > 1 else "run"](rules)
