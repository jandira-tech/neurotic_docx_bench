"""Log what Word and the processes that put up its dialogs are showing.

Two kinds of line, both from CoreGraphics' window list (no Apple events, no System Events: the Word
driver's watchdogs keep System Events busy and press No/OK through it on an 8 s budget):
  - every <interval> seconds, a snapshot of every Word/dialog window ("same" when unchanged);
  - the moment a dialog appears, a "DIALOG" line with its text. The window list is read every
    POLL seconds and each new dialog window is screenshotted at once and read, because the driver
    answers Word's repair prompt within a few seconds, well inside one interval. An alert zooms in
    (40x44 ... 260x282 over a few polls), so a window is read once its size holds for one poll; one
    that closes before that is read from its newest screenshot and marked "(closed before it settled)".
Reading: macOS Vision (accurate), else tesseract on a 3x copy, else Vision (fast). Vision's accurate
model can break system-wide (2026-10-13: e5rt "precompiled compute operation" error in every
process, CPU-only too, ~40 s per failed call), so it is tried once at start and skipped when broken;
tesseract reads Word's alerts, file names included. The engine that read the text is named on the
line when it is not Vision accurate. Keep screenshots out of /tmp: tesseract's Leptonica rewrites
/tmp paths and then cannot open them.
A dialog is a window at a level above normal (Word's alerts are modal panels, layer 8) or one no
bigger than DIALOG_MAX. Read-only; screenshots are deleted after reading, except when nothing
can read one: that png is kept in <log>.unread/ and its name logged.

usage: uv run --no-project --with pyobjc-framework-Quartz --with pyobjc-framework-Vision \
         python -I word_screen_log.py <log_file> [interval_seconds=10]

Note (2026-10-14): `word_pdf.py` now reads and logs each alert's text itself and answers the repair
prompt No then OK with Word brought forward (`word_pdf_focus.py` is superseded). This logger stays
as the independent record: it also catches alerts the driver never saw, and macOS permission
prompts such as "uv would like to control this Mac", which it logged on the 2026-10-14 smoke run.

Note (2026-10-13): start it before a `word_pdf.py` batch and leave it
running beside the batch, with Word in front; it is the on-screen record of what Word said about
each file. Word's alerts last only a few seconds, because the driver answers them, so a 10 s sample alone
missed every one and grabbed the rest as they closed (the old "<ocr failed>" lines). The 0.25 s
poll catches them. Verified on a real driver run: it logged the repair prompt ("Word found
unreadable content in <file>. Do you want to recover the contents…") and the follow-up ("Word
experienced an error trying to open the file … OK"). The second alert can vanish in under 0.1 s
on Word's second attempt; then the line reads "<no screenshot: … could not create image from
window>". Needs Screen Recording permission for the terminal that launches it. The live-bench
harvest (live-bench/harvest/) runs this copy; the ~/temp/T working copy is gone.
"""

import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import Quartz
import Vision
from Foundation import NSURL

POLL = 0.25
OWNERS = {"Microsoft Word", "Microsoft Error Reporting", "UserNotificationCenter",
          "CoreServicesUIAgent", "SecurityAgent", "universalAccessAuthWarn", "tccd"}
DIALOG_MAX = (900, 700)  # a window no bigger than this is read; document windows are bigger
tmp = Path(tempfile.mkdtemp(prefix="word_screen_"))  # under $TMPDIR (/var/folders), never /tmp
unread: Path | None = None  # <log>.unread, where unreadable screenshots are kept; set by run()
accurate_ok = False  # probed once by run(): a broken accurate model costs ~40 s per failed call


def stamp() -> str:
    """Millisecond-stamped local time for log lines."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def vision(png: Path, level) -> str | None:
    """Read `png` with macOS Vision at `level`; the joined text, "" when it read nothing, None when it failed.

    An empty read is "", not a placeholder string, so `ocr` tries the next engine and `read`
    keeps the screenshot when nothing can read it. Only None (the request failed) tells `ocr`
    the accurate model is broken.
    """
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(level)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(str(png)), None)
    ok, _ = handler.performRequests_error_([req], None)
    if not ok:
        return None
    return " | ".join(o.topCandidates_(1)[0].string() for o in (req.results() or []))


TESSERACT = shutil.which("tesseract") or next((t for t in ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract")
                                               if Path(t).exists()), None)


def tesseract(png: Path) -> str | None:
    """Read `png` with tesseract off a 3x upscale (`sips`), tagged plain text, or None.

    Both subprocesses are bounded; a timeout anywhere returns None so `ocr` falls through to
    the next engine, and the 3x upscale never outlives the call (`finally`).
    """
    if not TESSERACT:
        return None
    big = png.with_name(png.stem + "_x3.png")
    try:
        width = int.from_bytes(png.read_bytes()[16:20], "big")  # PNG IHDR width
        subprocess.run(["sips", "--resampleWidth", str(width * 3), str(png), "--out", str(big)],
                       capture_output=True, timeout=10)
        r = subprocess.run([TESSERACT, str(big), "-"], capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None
    finally:
        big.unlink(missing_ok=True)
    text = " | ".join(x.strip() for x in r.stdout.decode(errors="replace").splitlines() if x.strip())
    return text if r.returncode == 0 and text else None


def accurate_works() -> bool:
    """Try Vision's accurate model once on a strip of the screen, at start, not on the first dialog."""
    png = tmp / "probe.png"
    subprocess.run(["screencapture", "-x", "-R0,0,400,60", str(png)], capture_output=True, timeout=10)
    ok = png.exists() and vision(png, Vision.VNRequestTextRecognitionLevelAccurate) is not None
    png.unlink(missing_ok=True)
    return ok


def ocr(png: Path) -> str | None:
    """Best text for `png`: Vision accurate, then tesseract, then Vision fast, each tagged but the first."""
    global accurate_ok
    if accurate_ok:
        text = vision(png, Vision.VNRequestTextRecognitionLevelAccurate)
        if text:
            return text
        if text is None:  # the request failed; a blank dialog ("") says nothing about the model
            accurate_ok = False
    text = tesseract(png)
    if text is not None:
        return f"{text}   (tesseract)"
    text = vision(png, Vision.VNRequestTextRecognitionLevelFast)
    return f"{text}   (vision fast)" if text else None


def windows() -> list[dict]:
    """Every on-screen window of the owners that put up Word's dialogs, with bounds and layer."""
    out = []
    for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID) or []:
        if w.get("kCGWindowOwnerName", "") not in OWNERS:
            continue
        b = w.get("kCGWindowBounds", {})
        width, height = int(b.get("Width", 0)), int(b.get("Height", 0))
        if width < 40 or height < 40:  # menu-bar items, invisible helpers
            continue
        out.append({"id": w["kCGWindowNumber"], "owner": w["kCGWindowOwnerName"], "w": width, "h": height,
                    "layer": w.get("kCGWindowLayer", 0), "title": w.get("kCGWindowName") or "",
                    "on": bool(w.get("kCGWindowIsOnscreen"))})
    return out


def is_dialog(w: dict) -> bool:
    """True for an on-screen window above normal layer or no bigger than DIALOG_MAX."""
    return w["on"] and (w["layer"] > 0 or (w["w"] <= DIALOG_MAX[0] and w["h"] <= DIALOG_MAX[1]))


def describe(w: dict) -> str:
    """One-line description of a window for the snapshot and DIALOG lines."""
    return (f"[{w['owner']}] {'on screen' if w['on'] else 'hidden'} {w['w']}x{w['h']} "
            f"layer={w['layer']} title={w['title']!r}")


def shoot(w: dict) -> Path | None:
    """Screenshot window `w` into the session temp dir; None when nothing usable came back."""
    png = tmp / f"{w['id']}.png"
    subprocess.run(["screencapture", "-x", "-o", "-l", str(w["id"]), str(png)], capture_output=True, timeout=10)
    return png if png.exists() and png.stat().st_size else None


def read(png: Path | None) -> str:
    """Text of a screenshot; when nothing can read it, keep the png and say where.

    The move into `unread` is a `shutil.move`: the screenshot sits under $TMPDIR and the
    log dir can be on another volume, where `rename` would raise cross-device.
    """
    if png is None:
        return "<no screenshot: the window was gone before it could be captured>"
    text = ocr(png)
    if text is None:
        unread.mkdir(exist_ok=True)
        keep = unread / f"{datetime.now():%H%M%S}_{png.name}"
        shutil.move(png, keep)
        return f"<could not read {keep}>"
    png.unlink()
    return text


shape: dict[int, tuple] = {}  # dialog window id -> (title, w, h) at the previous poll
read_at: dict[int, tuple] = {}  # dialog window id -> the (title, w, h) it was read at
last: dict[int, tuple[dict, Path | None]] = {}  # unsettled dialog -> its newest screenshot
said: dict[int, str] = {}  # dialog window id -> text last logged


def say(w: dict, text: str, fh) -> None:
    """Write a DIALOG line for `w` when `text` differs from what it last said."""
    if text != said.get(w["id"]):
        said[w["id"]] = text
        fh.write(f"{stamp()} DIALOG {describe(w)}\n    says: {text}\n")


def handle_frame(dialogs: dict[int, dict], fh) -> None:
    """One poll's dialog bookkeeping: read settled dialogs, keep shots of zooming ones, forget closed."""
    for i, w in dialogs.items():
        key = (w["title"], w["w"], w["h"])
        if read_at.get(i) == key:
            continue
        if shape.get(i) == key:  # same size as one poll ago: done zooming, read it
            png = shoot(w)
            if png is not None:  # a failed capture leaves the dialog eligible for the next poll
                read_at[i] = key
                last.pop(i, None)
                say(w, read(png), fh)
        else:  # new or still zooming: keep a shot in case it closes before it settles
            last[i] = (w, shoot(w))
        shape[i] = key
    for gone in set(shape) - set(dialogs):
        if gone in last:  # closed before it settled: read the newest shot
            w, png = last.pop(gone)
            say(w, read(png) + "   (closed before it settled)", fh)
        shape.pop(gone, None)
        read_at.pop(gone, None)
        said.pop(gone, None)
        fh.write(f"{stamp()} DIALOG closed id={gone}\n")


def run(log: str, every: float = 10.0) -> None:
    """Append the Word/dialog record to `log` until killed; snapshot every `every` seconds."""
    global unread, accurate_ok
    unread = Path(f"{log}.unread")
    accurate_ok = accurate_works()
    prev, next_snap = None, 0.0
    with open(log, "a", buffering=1) as fh:
        fh.write(f"{stamp()} logger started (pid {__import__('os').getpid()}, poll {POLL}s, snapshot {every}s, "
                 f"tesseract {TESSERACT or 'missing'}, vision accurate {'works' if accurate_ok else 'broken'})\n")
        while True:
            try:
                ws = windows()
                handle_frame({w["id"]: w for w in ws if is_dialog(w)}, fh)
                if time.monotonic() >= next_snap:
                    next_snap = time.monotonic() + every
                    snap = "\n".join(describe(w) for w in ws) or "<no Word or dialog windows>"
                    fh.write(f"{stamp()} same\n" if snap == prev else f"{stamp()}\n{snap}\n")
                    prev = snap
            except Exception as exc:  # keep logging through a bad frame
                fh.write(f"{stamp()} <error: {type(exc).__name__}: {exc}>\n")
            time.sleep(POLL)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: word_screen_log.py <log_file> [interval_seconds=10]")
    run(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 10.0)
