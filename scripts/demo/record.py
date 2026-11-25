"""Run from repository root with .venv/bin/python scripts/demo/record.py 01."""
import argparse
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import uvicorn
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "apps/api"))
from reset_demo import reset_demo_database

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", choices=[f"{i:02}" for i in range(1, 7)])
    args = parser.parse_args()
    os.umask(0o077)
    state = ROOT / ".mira/recording"
    state.mkdir(exist_ok=True)
    target = state / "isolated.sqlite3"
    import fcntl
    lock = (state / "run.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not target.exists():
        with tempfile.TemporaryDirectory(dir=state) as temp:
            fresh = Path(temp) / "copy.sqlite3"
            with sqlite3.connect("file:.mira/demo.sqlite3?mode=ro", uri=True) as source, sqlite3.connect(fresh) as dest:
                source.backup(dest)
            source.close()
            dest.close()
            reset_demo_database(fresh)
            fresh.rename(target)
    for key, value in dotenv_values(ROOT / ".env").items():
        if value is not None:
            os.environ.setdefault(key, value)
    os.environ.update(MIRA_DB=str(target), AS_OF_DATE="2026-11-19", MIRA_ORIGIN="http://127.0.0.1:5175",
                      LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        os.environ["RECORD_API"] = f"http://127.0.0.1:{sock.getsockname()[1]}"
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "mira.main:app", "--fd", str(sock.fileno()),
                                   "--no-access-log"], pass_fds=(sock.fileno(),), env={**os.environ, "PYTHONPATH":str(ROOT/"apps/api")},
                                  stdout=subprocess.DEVNULL, stderr=(state/"api.log").open("w"))
        try:
            import time
            from urllib.request import urlopen
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Isolated API failed to start. Check private .mira/recording/api.log.")
                try:
                    with urlopen(os.environ["RECORD_API"] + "/api/health", timeout=.5):
                        break
                except OSError:
                    time.sleep(.15)
            else:
                raise RuntimeError("Isolated API readiness timeout")
            raise SystemExit(subprocess.call(["node", "scripts/demo/record.cjs", args.scene]))
        finally:
            server.terminate()
            server.wait()
