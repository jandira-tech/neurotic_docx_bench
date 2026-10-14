"""Log what Word and the processes that put up its dialogs are showing.

Two kinds of line, both from CoreGraphics' window list (no Apple events, no System Events: the Word
driver's watchdogs keep System Events busy and press No/OK through it on an 8 s budget):
  - every <interval> seconds, a snapshot of every Word/dialog window ("same" when unchanged);
  - the moment a dialog appears, a "DIALOG" line with its text. The window list is read every
    POLL seconds and each new dialog window is screenshotted at once and read by macOS Vision,
    because the driver answers Word's repair prompt within a few seconds, well inside one interval.
A dialog is a window at a level above normal (Word's alerts are modal panels, layer 8) or one no
bigger than DIALOG_MAX. Read-only; screenshots are deleted after reading, except when Vision
cannot read one: that png is kept in <log>.unread/ and its name logged.

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
window>". Needs Screen Recording permission for the terminal that launches it. Working copy (the
one the live-bench harvest runs): ~/temp/T/d1_jubarte_live_bench_scripts/word_screen_log.py.
"""

import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import Quartz
import Vision
from Foundation import NSURL

log, every = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
POLL = 0.25
OWNERS = {"Microsoft Word", "Microsoft Error Reporting", "UserNotificationCenter",
          "CoreServicesUIAgent", "SecurityAgent", "universalAccessAuthWarn", "tccd"}
DIALOG_MAX = (900, 700)  # a window no bigger than this is read; document windows are bigger
tmp = Path(tempfile.mkdtemp(prefix="word_screen_"))
unread = Path(f"{log}.unread")


def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def ocr(png: Path) -> str | None:
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(str(png)), None)
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        return None
    return " | ".join(o.topCandidates_(1)[0].string() for o in (req.results() or [])) or "<no text>"


def windows() -> list[dict]:
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
    return w["on"] and (w["layer"] > 0 or (w["w"] <= DIALOG_MAX[0] and w["h"] <= DIALOG_MAX[1]))


def describe(w: dict) -> str:
    return (f"[{w['owner']}] {'on screen' if w['on'] else 'hidden'} {w['w']}x{w['h']} "
            f"layer={w['layer']} title={w['title']!r}")


def read(w: dict) -> str:
    """Screenshot window w now and return its text; on failure keep the png and say where."""
    png = tmp / f"{w['id']}.png"
    r = subprocess.run(["screencapture", "-x", "-o", "-l", str(w["id"]), str(png)],
                       capture_output=True, text=True, timeout=10)
    if not png.exists() or png.stat().st_size == 0:
        return f"<no screenshot: rc={r.returncode} {r.stderr.strip()}>"
    text = ocr(png)
    if text is None:
        unread.mkdir(exist_ok=True)
        keep = unread / f"{datetime.now():%H%M%S}_{w['id']}.png"
        png.rename(keep)
        return f"<Vision could not read {keep}>"
    png.unlink()
    return text


seen: dict[int, tuple] = {}  # dialog window id -> (title,) already read
prev, next_snap = None, 0.0
with open(log, "a", buffering=1) as fh:
    fh.write(f"{stamp()} logger started (pid {__import__('os').getpid()}, poll {POLL}s, snapshot {every}s)\n")
    while True:
        try:
            ws = windows()
            live = {w["id"] for w in ws if is_dialog(w)}
            for w in ws:
                key = (w["title"],)  # not the size: an alert resizes while it animates in
                if is_dialog(w) and seen.get(w["id"]) != key:
                    seen[w["id"]] = key
                    fh.write(f"{stamp()} DIALOG {describe(w)}\n    says: {read(w)}\n")
            for gone in set(seen) - live:
                del seen[gone]
                fh.write(f"{stamp()} DIALOG closed id={gone}\n")
            if time.monotonic() >= next_snap:
                next_snap = time.monotonic() + every
                snap = "\n".join(describe(w) for w in ws) or "<no Word or dialog windows>"
                fh.write(f"{stamp()} same\n" if snap == prev else f"{stamp()}\n{snap}\n")
                prev = snap
        except Exception as exc:  # keep logging through a bad frame
            fh.write(f"{stamp()} <error: {type(exc).__name__}: {exc}>\n")
        time.sleep(POLL)
