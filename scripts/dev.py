"""Supervise the local services in their own process groups (macOS and Linux)."""
import json
import logging
import os
import re
import signal
import socket
import subprocess
import sys
from threading import Thread
from time import monotonic, sleep

from mira.observability import configure, event, valid_id

SERVICES = (
    ("API", 8000, ".", (sys.executable, "-u", "-m", "mira.serve")),
    ("NEXT", 3000, "apps/web", ("node_modules/.bin/next", "dev", "--hostname", "127.0.0.1", "--port", "3000")),
    ("WEB", 5175, "apps/ceylon-compass",
     ("node_modules/.bin/vite", "dev", "--host", "127.0.0.1", "--port", "5175", "--strictPort")),
)


def ports_free():
    for component, port, _, _ in SERVICES:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                event("ERROR", "port.unavailable", level=logging.ERROR, service=component, port=port,
                      remedy=f"Run lsof -nP -iTCP:{port} -sTCP:LISTEN and stop the owning service before retrying.")
                return False
    return True


def relay(pipe, component, port, severity):
    with pipe:
        for raw in pipe:
            line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw).strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    record = json.loads(line)
                except ValueError:
                    record = None
                if isinstance(record, dict) and record.get("event") in {
                    "ssr.failed", "ssr.invalid_response", "proxy.failed", "copilot.proxy_failed",
                }:
                    identifier = record.get("request_id")
                    status = record.get("status")
                    event(component, record["event"], level=logging.ERROR,
                          upstream_request_id=valid_id(identifier) if isinstance(identifier, str) else None,
                          status=status if isinstance(status, int) else None)
                    continue
            if re.search(r"\bready in \d", line, re.I):
                event(component, "server.ready", port=port)
            elif match := re.match(r"^(GET|POST|PUT|PATCH|DELETE|HEAD)\s+(\S+)\s+(\d{3})\s+in\s+(\d+)ms\b", line):
                method, path, status, duration = match.groups()
                # Quiet noisy static assets and internal proxy calls in dev console
                is_static = path.startswith(("/_next/static", "/_next/image", "/favicon.ico"))
                is_proxy = path.startswith("/api/copilotkit/agent")
                event(component, "frontend.request", method=method, path=path, status=int(status),
                      duration_ms=int(duration),
                      level=logging.DEBUG if (is_static or is_proxy) else logging.INFO)
            elif match := re.match(r"^(GET|POST|PUT|PATCH|DELETE|HEAD)\s+\S+\s+(\d{3})\s+in\s+(\d+)ms\b", line):
                method, status, duration = match.groups()
                event(component, "frontend.request", method=method, status=int(status), duration_ms=int(duration))
            elif match := re.match(r"^at (?:async )?([\w.$<>]+) \((?:[^?()\s]+/)?([\w.-]+:\d+:\d+)\)$", line):
                event(component, "framework.frame", frame=match.group(2), function=match.group(1), level=severity)
            elif component == "NEXT" and "Unable to acquire lock" in line:
                event("ERROR", "next.dev_lock", level=logging.ERROR,
                      remedy="Stop the other Next.js dev server for this checkout before retrying.")
            elif "EADDRINUSE" in line:
                event("ERROR", "port.bind_failed", level=logging.ERROR, service=component, port=port)
            else:
                event(component, "framework.diagnostic",
                      level=logging.DEBUG if severity == logging.INFO else severity)


def signal_groups(processes, sig):
    for process in processes:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass


def stop(processes):
    signal_groups(processes, signal.SIGTERM)
    deadline = monotonic() + 5
    for process in processes:
        try:
            process.wait(timeout=max(0, deadline - monotonic()))
        except subprocess.TimeoutExpired:
            break
    # Reap descendants even when their original group leader has exited.
    signal_groups(processes, signal.SIGKILL)
    for process in processes:
        process.wait()


def supervise(services=SERVICES):
    interrupted = None

    def interrupt(sig, _frame):
        nonlocal interrupted
        interrupted = sig

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupt)
    processes = []
    readers = []
    try:
        for component, port, cwd, command in services:
            if interrupted:
                return 128 + interrupted
            captured = component != "API"
            dest = subprocess.PIPE if captured else None
            try:
                process = subprocess.Popen(command, cwd=cwd, stdout=dest, stderr=dest,
                                           text=True, errors="replace", start_new_session=True)
            except OSError:
                event("ERROR", "service.launch_failed", level=logging.ERROR, service=component, exception=True)
                return 1
            processes.append(process)
            event(component, "service.started", port=port)
            if captured:
                for pipe, severity in ((process.stdout, logging.INFO), (process.stderr, logging.WARNING)):
                    reader = Thread(target=relay, args=(pipe, component, port, severity), daemon=True)
                    reader.start()
                    readers.append(reader)
        while not interrupted:
            for (component, _, _, _), process in zip(services, processes):
                if (status := process.poll()) is not None:
                    event("ERROR", "service.exited", level=logging.ERROR, service=component, exit_status=status)
                    return status if status > 0 else 128 - status if status < 0 else 1
            sleep(0.1)
        return 128 + interrupted
    finally:
        stop(processes)
        for reader in readers:
            reader.join(timeout=1)


if __name__ == "__main__":
    configure()
    if not ports_free():
        sys.exit(1)
    if "--check-ports" not in sys.argv:
        sys.exit(supervise())
