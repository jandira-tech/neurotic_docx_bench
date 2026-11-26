"""Start the real server twice and prove each Word lane recycles and recovers."""

from __future__ import annotations

import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.factory import encode_form, make_docx  # noqa: E402

PYTHON = ROOT / ".tools" / "python" / "python.exe"


def token() -> str:
    for line in (ROOT / ".env").read_text(encoding="ascii").splitlines():
        if line.startswith("WORD_API_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("missing token")


def winword_pids() -> set[int]:
    output = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    pids = set()
    for line in output.splitlines():
        if "WINWORD.EXE" not in line.upper():
            continue
        parts = line.replace('"', "").split(",")
        if len(parts) > 1 and parts[1].strip().isdigit():
            pids.add(int(parts[1].strip()))
    return pids


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def call(base: str, path: str, payload: bytes, content_type: str, secret: str | None):
    headers = {"Content-Type": content_type, "User-Agent": "Mozilla/5.0"}
    if secret:
        headers["Authorization"] = "Bearer " + secret
    request = urllib.request.Request(base + path, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def read_pid(name: str) -> int:
    return int((ROOT / "work" / name).read_text(encoding="ascii").strip())


def stop_server(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is None:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    # WINWORD is not a child of the server, and taskkill does not run atexit.
    running = winword_pids()
    for name in ("compare.word.pid", "convert.word.pid"):
        path = ROOT / "work" / name
        try:
            pid = int(path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            continue
        if pid in running:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
                check=False,
            )


def one_run(number: int, secret: str) -> None:
    print(f"RUN {number}")
    before = winword_pids()
    port = free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["WORD_API_TOKEN"] = secret
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [str(PYTHON), str(ROOT / "serve.py")],
        cwd=str(ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    ready = {"compare": False, "convert": False}
    assert proc.stdout is not None
    lines: queue.Queue[bytes | None] = queue.Queue()

    def read_stdout() -> None:
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.readline()
            if not chunk:
                lines.put(None)
                return
            lines.put(chunk)

    threading.Thread(target=read_stdout, daemon=True).start()
    deadline = time.time() + 90
    log = bytearray()
    while time.time() < deadline and not all(ready.values()):
        try:
            line = lines.get(timeout=1)
        except queue.Empty:
            if proc.poll() is not None:
                break
            continue
        if line is None:
            break
        log.extend(line)
        text = line.decode("utf-8", "replace")
        if "compare Word is ready" in text:
            ready["compare"] = True
        if "convert Word is ready" in text:
            ready["convert"] = True
    print("warm", ready, "server", proc.poll(), flush=True)
    if not all(ready.values()):
        print(log.decode("utf-8", "replace")[-2000:])
        stop_server(proc)
        raise SystemExit(f"run {number} did not warm both lanes")
    base = f"http://127.0.0.1:{port}"
    health = urllib.request.urlopen(base + "/health", timeout=10)
    print("health", health.status, health.read().decode())
    content_type, denied = encode_form([("document", "a.docx", make_docx(["Hello"]))])
    unauth_status, body = call(base, "/v1/convert", denied, content_type, None)
    print("unauth", unauth_status, body[:80])
    document = make_docx(["Hello from the converter."])
    content_type, payload = encode_form([("document", "a.docx", document)])
    status, first = call(base, "/v1/convert", payload, content_type, secret)
    convert_pid = read_pid("convert.word.pid")
    status2, second = call(base, "/v1/convert", payload, content_type, secret)
    same = read_pid("convert.word.pid")
    print(
        "convert",
        status,
        first.startswith(b"%PDF-"),
        len(first),
        status2,
        second.startswith(b"%PDF-"),
        len(second),
        "pid",
        convert_pid,
        same,
    )
    original = make_docx(["The fee is 100 dollars."])
    revised = make_docx(["The fee is 250 dollars."])
    content_type, payload = encode_form(
        [("original", "a.docx", original), ("revised", "b.docx", revised)]
    )
    status, compared = call(base, "/v1/compare", payload, content_type, secret)
    xml = b""
    if compared.startswith(b"PK"):
        xml = zipfile.ZipFile(BytesIO(compared)).read("word/document.xml")
    compare_pid = read_pid("compare.word.pid")
    print(
        "compare",
        status,
        compared.startswith(b"PK"),
        b"w:ins" in xml or b"w:del" in xml,
        b"100" in xml and b"250" in xml,
        "pid",
        compare_pid,
    )
    if convert_pid not in winword_pids():
        raise SystemExit("convert pid was not WINWORD before the kill")
    subprocess.run(["taskkill", "/F", "/PID", str(convert_pid)], capture_output=True, text=True, check=False)
    print("killed convert", convert_pid, "still", convert_pid in winword_pids(), "compare", compare_pid in winword_pids())
    content_type, payload = encode_form([("document", "a.docx", document)])
    status, recovered = call(base, "/v1/convert", payload, content_type, secret)
    new_pid = read_pid("convert.word.pid")
    compare_now = read_pid("compare.word.pid")
    service = {compare_now, new_pid}
    running = winword_pids()
    print(
        "recover",
        status,
        recovered.startswith(b"%PDF-"),
        len(recovered),
        "new",
        new_pid,
        "compare",
        compare_now,
        "service",
        sorted(service),
        "service-up",
        service <= running,
        "extras",
        sorted(running - before - service),
    )
    problems = []
    if health.status != 200 or unauth_status != 401:
        problems.append("health-or-auth")
    if status != 200 or not recovered.startswith(b"%PDF-") or len(recovered) < 500:
        problems.append("recover-pdf")
    if new_pid == convert_pid or compare_now != compare_pid:
        problems.append("pids")
    if not (service <= running) or len(service) != 2:
        problems.append("service-count")
    if running - before - service:
        problems.append("extras")
    if not (first.startswith(b"%PDF-") and second.startswith(b"%PDF-") and same == convert_pid and len(first) > 500):
        problems.append("recycle")
    if status != 200:
        pass
    compare_ok = (
        compared.startswith(b"PK")
        and (b"w:ins" in xml or b"w:del" in xml)
        and b"100" in xml
        and b"250" in xml
    )
    if not compare_ok:
        problems.append("compare")
    stop_server(proc)
    print("stopped", number)
    if problems:
        raise SystemExit(f"run {number} failed: {problems}")


def main() -> int:
    secret = token()
    for number in (1, 2):
        one_run(number, secret)
    print("LIVE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
