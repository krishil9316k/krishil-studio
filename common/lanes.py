"""
Lane guard — the wall between the employees.

Every worker declares who it is (MANAGER, INSTAGRAM or WHATSAPP).
It may only READ and WRITE inside its own lane folders, and only load
its own rules file. Any attempt to touch the other lane raises
LaneViolation and the run stops, so the two systems can never collide.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LANES = {
    "MANAGER": {
        "write": ["inbox", "media/originals", "queues/instagram/new", "queues/whatsapp/new", "status/manager.json"],
        "read":  ["inbox", "media/originals", "rules/manager_rules.json", "assets"],
        "rules": "rules/manager_rules.json",
    },
    "INSTAGRAM": {
        "write": ["queues/instagram", "media/instagram", "status/instagram.json"],
        "read":  ["queues/instagram", "media/instagram", "media/originals", "rules/instagram_rules.json", "assets"],
        "rules": "rules/instagram_rules.json",
    },
    "WHATSAPP": {
        "write": ["queues/whatsapp", "media/whatsapp", "status/whatsapp.json"],
        "read":  ["queues/whatsapp", "media/whatsapp", "media/originals", "rules/whatsapp_rules.json", "assets"],
        "rules": "rules/whatsapp_rules.json",
    },
}


class LaneViolation(Exception):
    pass


class Lane:
    def __init__(self, role: str):
        if role not in LANES:
            raise LaneViolation(f"Unknown role {role}")
        self.role = role
        self.cfg = LANES[role]

    # ---- path checks -------------------------------------------------
    def _rel(self, path) -> str:
        p = (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            return p.relative_to(ROOT).as_posix()
        except ValueError:
            raise LaneViolation(f"{self.role}: path outside project: {path}")

    def _allowed(self, rel: str, kind: str) -> bool:
        return any(rel == a or rel.startswith(a.rstrip("/") + "/") for a in self.cfg[kind])

    def check_write(self, path) -> Path:
        rel = self._rel(path)
        if not self._allowed(rel, "write"):
            raise LaneViolation(f"{self.role} may not WRITE {rel}")
        return ROOT / rel

    def check_read(self, path) -> Path:
        rel = self._rel(path)
        if not (self._allowed(rel, "read") or self._allowed(rel, "write")):
            raise LaneViolation(f"{self.role} may not READ {rel}")
        return ROOT / rel

    # ---- helpers -----------------------------------------------------
    def rules(self) -> dict:
        return json.loads(self.check_read(self.cfg["rules"]).read_text(encoding="utf-8"))

    def read_json(self, path):
        return json.loads(self.check_read(path).read_text(encoding="utf-8"))

    def write_json(self, path, data):
        p = self.check_write(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)

    def write_bytes(self, path, data: bytes):
        p = self.check_write(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def move(self, src, dst):
        s = self.check_write(src)
        d = self.check_write(dst)
        d.parent.mkdir(parents=True, exist_ok=True)
        os.replace(s, d)

    def list(self, folder, suffix=None):
        p = self.check_read(folder)
        if not p.exists():
            return []
        out = sorted(x for x in p.iterdir() if x.is_file() and not x.name.startswith("."))
        return [x for x in out if suffix is None or x.suffix.lower() in suffix]

    def rel(self, path) -> str:
        return self._rel(path)
