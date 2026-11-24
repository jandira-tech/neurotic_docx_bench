"""Protocol stand-in for a Word lane. It is not Word."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    kind = sys.argv[1]
    control = Path(sys.argv[2])
    sleeper = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(300)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (control / f"{kind}.pid").write_text(str(sleeper.pid), encoding="ascii")
    sys.stdout.buffer.write(f"ready {sleeper.pid}\n".encode("ascii"))
    sys.stdout.buffer.flush()
    while True:
        line = sys.stdin.buffer.readline()
        if not line or line.strip() == b"quit":
            sleeper.kill()
            return 0
        if line.strip() == b"ping":
            sys.stdout.buffer.write(b"alive\n")
            sys.stdout.buffer.flush()
            continue
        operation, path = line.decode("ascii").strip().split("\t", 1)
        workdir = Path(path)
        (control / f"{kind}.started").write_text("1", encoding="ascii")
        mode_path = control / f"{kind}.mode"
        mode = mode_path.read_text(encoding="ascii").strip() if mode_path.is_file() else "ok"
        if mode == "hang":
            time.sleep(300)
            return 0
        if mode == "die":
            return 1
        deadline = time.time() + 2
        while time.time() < deadline:
            if (control / "compare.started").is_file() and (control / "convert.started").is_file():
                break
            time.sleep(0.02)
        (workdir / "result.json").write_text(
            json.dumps({"ok": True, "error": None}),
            encoding="utf-8",
        )
        if operation in {"convert", "compare_pdf"}:
            (workdir / "output.pdf").write_bytes(b"%PDF-1.4\n" + b"x" * 80 + b"\n%%EOF\n")
        else:
            from tests.factory import make_docx

            (workdir / "output.docx").write_bytes(make_docx(["compared"]))
        count_path = control / f"{kind}.count"
        previous = int(count_path.read_text(encoding="ascii")) if count_path.is_file() else 0
        count_path.write_text(str(previous + 1), encoding="ascii")
        sys.stdout.buffer.write(b"done\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(main())
