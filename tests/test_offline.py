"""Offline test (no AI key, no Instagram token): checks the full flow and the walls between lanes.
Run from the project folder:  python tests/test_offline.py"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402

from common.lanes import Lane, LaneViolation  # noqa: E402

ok = lambda m: print("  ✔", m)  # noqa: E731


def walls():
    ig, wa, mg = Lane("INSTAGRAM"), Lane("WHATSAPP"), Lane("MANAGER")
    for lane, bad in [(ig, "queues/whatsapp/ready/x.json"), (ig, "rules/whatsapp_rules.json"),
                      (wa, "queues/instagram/tasks/x.json"), (wa, "rules/instagram_rules.json"),
                      (wa, "status/instagram.json"), (mg, "queues/instagram/tasks/x.json"), (ig, "../outside.txt")]:
        try:
            lane.check_write(bad)
            raise SystemExit(f"WALL BROKEN: {lane.role} could write {bad}")
        except LaneViolation:
            pass
    for lane, bad in [(ig, "rules/whatsapp_rules.json"), (wa, "rules/instagram_rules.json"), (wa, "queues/instagram/tasks")]:
        try:
            lane.check_read(bad)
            raise SystemExit(f"WALL BROKEN: {lane.role} could read {bad}")
        except LaneViolation:
            pass
    ok("lane walls hold (no cross reads/writes)")


def run(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/usr/local/bin:/bin"})
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit(f"FAILED: {args}")
    return r.stdout


def flow():
    inbox = ROOT / "inbox"
    Image.new("RGB", (1200, 900), (240, 200, 60)).save(inbox / "20261102100000__pens.jpg")
    (inbox / "20261102100000__pens.jpg.json").write_text(json.dumps({"note": "New gel pens ₹10", "send_to": "both"}))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25",
                    "-t", "3", str(inbox / "20261102100001__shop.mp4")], check=True)
    print(run("manager/manager.py"))
    assert (ROOT / "queues/instagram/new/20261102100000.json").exists()
    assert (ROOT / "queues/whatsapp/new/20261102100000.json").exists()
    assert (ROOT / "queues/instagram/new/20261102100001.json").exists()  # 'other' video -> instagram only
    assert not (ROOT / "queues/whatsapp/new/20261102100001.json").exists()
    ok("manager routed photo to BOTH (separate copies) and video to Instagram only")

    print(run("workers/instagram_worker.py", "prepare"))
    t = json.loads((ROOT / "queues/instagram/tasks/20261102100000.json").read_text())
    assert t["status"] == "draft" and len(t["hashtags"]) <= 5
    im = Image.open(ROOT / t["media"])
    assert im.size == (1080, 1350) and im.format == "JPEG"
    ok(f"Instagram draft made: {im.size} JPEG, {len(t['hashtags'])} hashtags")
    v = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(ROOT / "media/instagram/20261102100001.mp4")], capture_output=True, text=True).stdout.strip()
    assert v == "1080,1920", v
    ok("Reel converted to 1080x1920")

    # approve + schedule
    t["status"] = "approved"
    (ROOT / "queues/instagram/tasks/20261102100000.json").write_text(json.dumps(t))
    run("workers/instagram_worker.py", "prepare")
    t = json.loads((ROOT / "queues/instagram/tasks/20261102100000.json").read_text())
    assert t["status"] == "scheduled" and t["slot"]
    ok(f"approved post scheduled for {t['slot']}")
    out = run("workers/instagram_worker.py", "publish")
    assert "not connected" in out
    ok("publish safely waits until Instagram is connected")

    print(run("workers/whatsapp_worker.py", "prepare"))
    w = json.loads((ROOT / "queues/whatsapp/ready/20261102100000.json").read_text())
    assert w["status"] == "ready" and "8347902010" in w["message"]
    ok(f"WhatsApp message ready for {w['send_on']} with its own image")


def clean():
    for p in ["inbox", "media/originals", "media/instagram", "media/whatsapp", "queues/instagram/new",
              "queues/instagram/tasks", "queues/whatsapp/new", "queues/whatsapp/ready"]:
        for f in (ROOT / p).iterdir():
            if f.name != ".keep":
                f.unlink() if f.is_file() else shutil.rmtree(f)
    (ROOT / "queues/instagram/published_ledger.json").unlink(missing_ok=True)
    for s in ["manager", "instagram", "whatsapp"]:
        (ROOT / f"status/{s}.json").write_text("{}")


if __name__ == "__main__":
    clean()
    walls()
    try:
        flow()
        print("\nALL TESTS PASSED")
    finally:
        clean()
