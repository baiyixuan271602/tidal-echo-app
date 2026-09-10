#!/usr/bin/env python3
"""Boot-time restore: pull the latest backup from GitHub into /data.
Retries 3 times; on total failure sets /data/.restore_failed so the backup
loop will refuse to overwrite the remote copy."""
import json, base64, os, time, urllib.request, urllib.error
from pathlib import Path

GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = os.environ.get("GH_BACKUP_REPO", "")
GH_PATH = os.environ.get("GH_BACKUP_PATH", "backup.json")
DATA = Path("/data")
DB = DATA / "relay.db"
LOOP_CFG = DATA / "api_loop.config.json"
FLAG = DATA / ".restore_failed"

def log(m): print("[restore]", m, flush=True)

def gh_get():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/contents/{GH_PATH}",
        headers={"Authorization": f"Bearer {GH_TOKEN}", "User-Agent": "tidal-restore"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def local_has_data():
    if not DB.exists():
        return False
    try:
        import sqlite3
        con = sqlite3.connect(DB)
        n = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        con.close()
        return n > 0
    except Exception:
        return False

def main():
    if not GH_TOKEN or not GH_REPO:
        log("no GH_TOKEN/GH_REPO configured, skip restore")
        return
    if local_has_data():
        log("local db already has data, skip")
        return
    for attempt in range(1, 4):
        try:
            j = gh_get()
            payload = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
            db_b64 = payload.get("relay_db_b64", "")
            if not db_b64:
                log("backup empty (no relay_db_b64)")
                return
            DATA.mkdir(parents=True, exist_ok=True)
            tmp = DB.with_suffix(".tmp")
            tmp.write_bytes(base64.b64decode(db_b64))
            tmp.replace(DB)
            cfg_b64 = payload.get("loop_config_b64", "")
            if cfg_b64:
                LOOP_CFG.write_bytes(base64.b64decode(cfg_b64))
            log(f"restored OK (messages={payload.get('messages_count','?')}, saved_at={payload.get('saved_at','?')})")
            if FLAG.exists():
                FLAG.unlink()
            return
        except urllib.error.HTTPError as e:
            if e.code == 404:
                log("no backup yet (404) - fresh start")
                return
            log(f"attempt {attempt}: HTTP {e.code}")
        except Exception as e:
            log(f"attempt {attempt}: {e}")
        if attempt < 3:
            time.sleep(5)
    FLAG.write_text(f"restore failed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n", encoding="utf-8")
    log("RESTORE FAILED after 3 attempts - flag set; backup loop will not overwrite remote")

if __name__ == "__main__":
    main()
