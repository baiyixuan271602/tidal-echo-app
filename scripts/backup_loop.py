#!/usr/bin/env python3
"""Periodic backup: push relay.db + loop config to GitHub.
Protections (learned the hard way):
  - if /data/.restore_failed exists  -> skip (never overwrite a good remote)
  - if local db is empty but remote has messages -> skip
"""
import json, base64, os, time, sqlite3, urllib.request, urllib.error
from pathlib import Path

GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = os.environ.get("GH_BACKUP_REPO", "")
GH_PATH = os.environ.get("GH_BACKUP_PATH", "backup.json")
INTERVAL = int(os.environ.get("GH_BACKUP_INTERVAL", "180"))
DATA = Path("/data")
DB = DATA / "relay.db"
LOOP_CFG = DATA / "api_loop.config.json"
FLAG = DATA / ".restore_failed"
API = "https://api.github.com"

def log(m): print("[backup]", m, flush=True)

def count_local():
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        con.close()
        return n
    except Exception:
        return 0

def remote_meta():
    try:
        req = urllib.request.Request(
            f"{API}/repos/{GH_REPO}/contents/{GH_PATH}",
            headers={"Authorization": f"Bearer {GH_TOKEN}", "User-Agent": "tidal-backup"})
        j = json.load(urllib.request.urlopen(req, timeout=30))
        payload = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
        return {"sha": j.get("sha"), "exists": True, "messages": payload.get("messages_count", 0)}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"exists": False}
        log(f"remote_meta HTTP {e.code}")
        return None
    except Exception as e:
        log(f"remote_meta error: {e}")
        return None

def push(sha, local_n):
    db_b64 = base64.b64encode(DB.read_bytes()).decode()
    cfg_b64 = base64.b64encode(LOOP_CFG.read_bytes()).decode() if LOOP_CFG.exists() else ""
    payload = {
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "messages_count": local_n,
        "relay_db_b64": db_b64,
        "loop_config_b64": cfg_b64,
    }
    body = {"message": f"auto backup ({local_n} msgs)",
            "content": base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode()}
    if sha:
        body["sha"] = sha
    req = urllib.request.Request(
        f"{API}/repos/{GH_REPO}/contents/{GH_PATH}",
        data=json.dumps(body).encode("utf-8"), method="PUT",
        headers={"Authorization": f"Bearer {GH_TOKEN}", "User-Agent": "tidal-backup",
                 "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60)

def tick():
    global _last_saved
    if FLAG.exists():
        return
    if not DB.exists():
        return
    local_n = count_local()
    r = remote_meta()
    if r is None:
        return
    if local_n == 0 and r.get("exists") and r.get("messages", 0) > 0:
        log(f"protect: local empty but remote has {r['messages']} msgs - skip")
        return
    push(r.get("sha"), local_n)
    log(f"pushed ({local_n} msgs)")

def main():
    if not GH_TOKEN or not GH_REPO:
        log("no GH_TOKEN/GH_REPO configured; backup loop disabled")
        return
    log(f"backup loop started: repo={GH_REPO}, every {INTERVAL}s")
    while True:
        try:
            tick()
        except Exception as e:
            log(f"tick error: {e}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
