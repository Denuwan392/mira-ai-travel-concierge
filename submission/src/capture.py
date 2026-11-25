"""Capture high-resolution desktop (1440x900 @2x) and mobile (390x844 @2x) screenshots
from the running canonical Ceylon Compass application using an isolated copy of the
verified recording database (zero modifications to production/demo DBs, zero LLM calls).
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)


def main():
    isolated_src = ROOT / ".mira/recording/isolated.sqlite3"
    if not isolated_src.exists():
        raise FileNotFoundError(f"Expected verified recording DB at {isolated_src}")

    out_dir = ROOT / "submission/assets/screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="mira-shots-") as tmp:
        tmp_db = Path(tmp) / "capture.sqlite3"
        shutil.copy2(isolated_src, tmp_db)

        env = os.environ.copy()
        for k, v in dotenv_values(ROOT / ".env").items():
            if v is not None:
                env.setdefault(k, v)
        env.update(
            MIRA_DB=str(tmp_db),
            AS_OF_DATE="2026-11-19",
            MIRA_ORIGIN="http://127.0.0.1:5175",
            PYTHONPATH=str(ROOT / "apps/api"),
            GEMINI_API_KEY="",
            LANGFUSE_PUBLIC_KEY="",
            LANGFUSE_SECRET_KEY="",
        )

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            env["RECORD_API"] = f"http://127.0.0.1:{port}"
            env["SHOTS_OUT"] = str(out_dir)

            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "mira.main:app", "--fd", str(sock.fileno()), "--no-access-log"],
                pass_fds=(sock.fileno(),),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=open(Path(tmp) / "api.log", "w"),
            )
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError("Isolated API failed to start")
                    try:
                        with urlopen(env["RECORD_API"] + "/api/health", timeout=0.5):
                            break
                    except OSError:
                        time.sleep(0.15)
                else:
                    raise RuntimeError("API readiness timeout")

                rc = subprocess.call(["node", "submission/src/capture.cjs"], env=env)
                raise SystemExit(rc)
            finally:
                server.terminate()
                server.wait()


if __name__ == "__main__":
    main()
