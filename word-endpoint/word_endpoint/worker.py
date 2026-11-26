"""Word automation for one job directory.

This process creates its own Word instance with DispatchEx. It must never
attach to a Word window the user already has open, and it must never update
fields: field updates are how DDE and INCLUDE instructions run.
"""

from __future__ import annotations

import csv
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import re
import subprocess
import sys
import time
import uuid
from ctypes import wintypes
from pathlib import Path

import pywintypes
import pythoncom
import win32com.client
import win32gui
import win32process

from word_endpoint.paths import LOG_DIR, WORK_ROOT

# msoAutomationSecurityForceDisable. Macros cannot run in this instance.
_FORCE_DISABLE_MACROS = 3
_ALERTS_NONE = 0  # wdAlertsNone
_DO_NOT_SAVE = 0  # wdDoNotSaveChanges
_COMPARE_DESTINATION_NEW = 2
_GRANULARITY_WORD = 1
_DOCX = 12
_PDF = 17
_EXPORT_WITH_MARKUP = 7
# The review settings of the Word for Mac that made the bench's oracle (Word 16.115, read
# from Word itself on 2026-11-24; docs/review-view.md). Set on every Word start, so a
# fresh profile or another machine marks revisions the same way. Values are the Windows
# enums (WdInsertedTextMark, WdColorIndex, WdCellColor, ...).
_MAC_REVISION_OPTIONS = (
    ("InsertedTextMark", 3),  # underline
    ("InsertedTextColor", -1),  # by author
    ("DeletedTextMark", 1),  # strikethrough
    ("DeletedTextColor", -1),  # by author
    ("RevisedPropertiesMark", 0),  # none
    ("RevisedPropertiesColor", -1),  # by author
    ("RevisedLinesMark", 3),  # outside border
    ("RevisedLinesColor", 6),  # red
    ("CommentsColor", -1),  # by author
    ("MoveFromTextMark", 1),  # double strikethrough
    ("MoveFromTextColor", 11),  # green
    ("MoveToTextMark", 4),  # double underline
    ("MoveToTextColor", 11),  # green
    ("InsertedCellColor", 2),  # light blue
    ("DeletedCellColor", 1),  # pink
    ("MergedCellColor", 3),  # light yellow
    ("SplitCellColor", 5),  # light orange
)
# The view Word for Mac opens a redline in and exports it from: all markup, final,
# insertions, deletions and formatting changes inline (wdInLineRevisions), comments in
# the margin. Inline mode still prints comment balloons; it prints no "Formatted:"
# balloons, which mixed mode (2) adds and Word for Mac never shows.
_INLINE_REVISIONS = 1
_REVISIONS_VIEW_FINAL = 0
_REVISIONS_MARKUP_ALL = 2
_MAX_FIELDS = 100000
_MAX_STORIES = 4096
_JOB = None

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class WorkerError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def contain_process_tree() -> None:
    """Best-effort job object so Word exits when this process exits."""
    global _JOB
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x2000 | 0x200
        info.JobMemoryLimit = 2 * 1024 * 1024 * 1024
        size = ctypes.sizeof(info)
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), size):
            info.BasicLimitInformation.LimitFlags = 0x2000
            info.JobMemoryLimit = 0
            if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), size):
                return
        if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
            return
        _JOB = job
    except Exception:
        logging.info("job object was not applied")


def safe_workdir(raw: str) -> Path:
    workdir = Path(raw).resolve()
    root = WORK_ROOT.resolve()
    if workdir.parent != root or re.fullmatch(r"[0-9a-f]{32}", workdir.name) is None:
        raise WorkerError("word_failed")
    if not workdir.is_dir():
        raise WorkerError("word_failed")
    return workdir


def execute(kind: str, workdir: Path) -> int:
    """One-shot path used only if a caller still passes a single work directory."""
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    word = None
    code = 0
    before = winword_pids()
    try:
        word = start_word()
        if not _wait_word_ready(word):
            raise WorkerError("word_failed")
        publish_word_pid(word, workdir, before)
        if not run_job(word, kind, workdir):
            code = 1
    except Exception:
        logging.exception("unexpected worker failure")
        write_result(workdir, False, "word_failed")
        code = 1
    finally:
        if word is not None:
            quit_word(word)
        pythoncom.CoUninitialize()
    return code


def serve(kind: str) -> int:
    """Keep one Word process open and accept work directories on stdin."""
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    word = None
    pid_path = WORK_ROOT / f"{kind}.word.pid"
    before = winword_pids()
    try:
        word = start_word()
        if not _wait_word_ready(word):
            logging.error("Word did not answer after start")
            return 1
        pid = discover_word_pid(word, before)
        if pid is None:
            logging.error("could not determine the WINWORD pid")
            return 1
        WORK_ROOT.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(pid), encoding="ascii")
        _say(f"ready {pid}\n".encode("ascii"))
        while True:
            line = sys.stdin.buffer.readline()
            if not line or line.strip() == b"quit":
                return 0
            if line.strip() == b"ping":
                reusable = lane_reusable(word_alive(word), open_document_count(word))
                _say(b"alive\n" if reusable else b"dead\n")
                if not reusable:
                    return 1
                continue
            try:
                operation, workdir = parse_job_command(kind, line)
            except (UnicodeDecodeError, WorkerError):
                logging.error("rejected work directory")
                _say(b"done\n")
                continue
            (workdir / "word.pid").write_text(str(pid), encoding="ascii")
            alive = run_job(word, operation, workdir)
            if not alive:
                _say(b"dead\n")
                return 1
            _say(b"done\n")
    except Exception:
        logging.exception("Word worker stopped")
        return 1
    finally:
        if word is not None:
            quit_word(word)
        try:
            pid_path.unlink(missing_ok=True)
        except OSError:
            pass
        pythoncom.CoUninitialize()


def _wait_word_ready(word, timeout_s: float = 15.0) -> bool:
    """Word rejects COM calls for a moment after launch; wait until it answers."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if str(word.Version):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def start_word():
    word = win32com.client.DispatchEx("Word.Application")
    silence_word(word)
    # Set once per Word process; these options are unnecessary for rendering
    # and comparisons, and repeated COM assignments add per-job overhead.
    options = word.Options
    for name in ("CheckSpellingAsYouType", "CheckGrammarAsYouType"):
        try:
            setattr(options, name, False)
            if bool(getattr(options, name)):
                logging.warning("Word option %s remained enabled", name)
            else:
                logging.info("Word option %s disabled", name)
        except Exception:
            logging.warning("could not disable Word option %s", name, exc_info=True)
    set_revision_options(options)
    return word


def set_revision_options(options) -> None:
    changed = []
    for name, value in _MAC_REVISION_OPTIONS:
        try:
            if int(getattr(options, name)) != value:
                setattr(options, name, value)
                changed.append(name)
            if int(getattr(options, name)) != value:
                logging.warning("Word option %s is %s, not %s", name, getattr(options, name), value)
        except Exception:
            logging.warning("could not set Word option %s", name, exc_info=True)
    logging.info("Word revision options match Word for Mac (%s)", f"set {', '.join(changed)}" if changed else "already set")


def parse_job_command(lane: str, line: bytes) -> tuple[str, Path]:
    raw = line.decode("ascii").strip()
    # Accept the old path-only protocol as well as operation<TAB>path.
    operation, path = raw.split("\t", 1) if "\t" in raw else (lane, raw)
    allowed = {"compare", "compare_pdf"} if lane == "compare" else {"convert"}
    if operation not in allowed:
        raise WorkerError("word_failed")
    return operation, safe_workdir(path)


def silence_word(word) -> None:
    word.Visible = False
    word.DisplayAlerts = _ALERTS_NONE
    word.AutomationSecurity = _FORCE_DISABLE_MACROS
    try:
        word.ScreenUpdating = False
    except Exception:
        logging.info("ScreenUpdating could not be changed")


def lane_reusable(alive: bool, open_documents: int | None) -> bool:
    """A Word process is reused only when it is alive and has no open documents."""
    return alive and open_documents == 0


def run_job(word, kind: str, workdir: Path) -> bool:
    """Run one job. Return False when this Word process must be discarded."""
    discard = False
    started = time.monotonic()
    try:
        silence_word(word)
        if kind in {"compare", "compare_pdf"}:
            compare_documents(word, workdir, as_pdf=kind == "compare_pdf")
        else:
            convert_document(word, workdir)
        write_result(workdir, True, None)
    except WorkerError as exc:
        logging.info("worker rejected the job: %s", exc.code)
        write_result(workdir, False, exc.code)
    except pywintypes.com_error as exc:
        logging.exception("Word COM failed")
        write_result(workdir, False, classify(exc, kind).code)
        discard = True
    except Exception:
        logging.exception("unexpected worker failure")
        write_result(workdir, False, "word_failed")
        discard = True
    finally:
        close_open_documents(word)
        logging.info("job id=%s kind=%s word_ms=%d", workdir.name, kind,
                     (time.monotonic() - started) * 1000)
    return (not discard) and lane_reusable(word_alive(word), open_document_count(word))


def word_alive(word) -> bool:
    try:
        word.Visible = False
        return True
    except Exception:
        return False


def open_document_count(word) -> int | None:
    try:
        return int(word.Documents.Count)
    except Exception:
        return None


def discover_word_pid(word, before: set[int]) -> int | None:
    """Wait until the new Word process is visible. Never adopt one that already existed.

    This Word type library does not expose Application.Hwnd. Two lanes start
    together, so the only new WINWORD can belong to the other lane. A unique
    caption on this instance's hidden window identifies its own process.
    """
    marker = f"word-endpoint-{uuid.uuid4().hex}"
    try:
        word.Caption = marker
    except Exception:
        logging.info("could not mark the Word window")
        marker = ""
    for _ in range(40):
        pid = _pid_for_caption(marker) if marker else None
        if pid is None:
            pid = hwnd_pid(word)
        current = winword_pids()
        if pid and pid in current and pid not in before:
            return pid
        time.sleep(0.25)
    fresh = winword_pids() - before
    if marker == "" and len(fresh) == 1:
        return next(iter(fresh))
    return None


def _pid_for_caption(marker: str) -> int | None:
    found: list[int] = []

    def visit(hwnd, _extra) -> bool:
        try:
            if win32gui.GetClassName(hwnd) != "OpusApp":
                return True
            if win32gui.GetWindowText(hwnd) != marker:
                return True
            _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            return True
        if int(pid) > 4:
            found.append(int(pid))
        return True

    try:
        win32gui.EnumWindows(visit, None)
    except Exception:
        return None
    if len(found) != 1:
        return None
    return found[0]


def close_open_documents(word) -> None:
    try:
        count = int(word.Documents.Count)
    except Exception:
        return
    for _ in range(max(count, 0)):
        try:
            document = word.Documents.Item(1)
            document.Saved = True
            document.Close(SaveChanges=_DO_NOT_SAVE)
        except Exception:
            logging.info("could not close a leftover document")
            return


def _say(payload: bytes) -> None:
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def compare_documents(word, workdir: Path, *, as_pdf: bool = False) -> None:
    original = _timed_call("open_original", workdir, open_document, word, workdir / "original.docx", read_only=False)
    revised = _timed_call("open_revised", workdir, open_document, word, workdir / "revised.docx", read_only=False)
    word.Visible = False
    result = _timed_call("compare", workdir, word.CompareDocuments,
        OriginalDocument=original,
        RevisedDocument=revised,
        Destination=_COMPARE_DESTINATION_NEW,
        Granularity=_GRANULARITY_WORD,
        CompareFormatting=True,
        CompareCaseChanges=True,
        CompareWhitespace=True,
        CompareTables=True,
        CompareHeaders=True,
        CompareFootnotes=True,
        CompareTextboxes=True,
        CompareFields=True,
        CompareComments=True,
        CompareMoves=True,
        RevisedAuthor="Comparison",
        IgnoreAllComparisonWarnings=True,
    )
    if result is None or not hasattr(result, "SaveAs2"):
        raise WorkerError("compare_failed")
    output = workdir / ("output.pdf" if as_pdf else "output.docx")
    scrub_properties(result)
    if as_pdf:
        # Export the live comparison result. No intermediate DOCX or reopen.
        lock_fields(result)
        _timed_call("export_pdf", workdir, export_pdf, result, output)
    else:
        _timed_call("save_docx", workdir, result.SaveAs2, FileName=str(output), FileFormat=_DOCX, AddToRecentFiles=False)
    close_document(result)
    close_document(original)
    close_document(revised)
    assert_output(output, b"%PDF-" if as_pdf else b"PK", "convert_failed" if as_pdf else "compare_failed")


def convert_document(word, workdir: Path) -> None:
    document = _timed_call("open_document", workdir, open_document, word, workdir / "document.docx", read_only=True)
    word.Visible = False
    scrub_properties(document)
    output = workdir / "output.pdf"
    _timed_call("export_pdf", workdir, export_pdf, document, output)
    close_document(document)
    assert_output(output, b"%PDF-", "convert_failed")


# Word's COM server can reject a call outright while it is busy settling
# after a start or a previous job (RPC_E_CALL_REJECTED /
# RPC_E_SERVERCALL_RETRYLATER). The call never ran, so retrying is safe.
_BUSY_COM = {-2147418111, -2147417846}


def _timed_call(phase, workdir, function, *args, **kwargs):
    started = time.monotonic()
    try:
        attempts = 0
        while True:
            try:
                return function(*args, **kwargs)
            except pywintypes.com_error as exc:
                attempts += 1
                if attempts <= 3 and getattr(exc, "hresult", None) in _BUSY_COM:
                    logging.warning("Word busy in %s (attempt %d), retrying",
                                    phase, attempts)
                    time.sleep(attempts * 2)
                    continue
                raise
    finally:
        logging.info("job id=%s phase=%s ms=%d", workdir.name, phase,
                     (time.monotonic() - started) * 1000)


def open_document(word, path: Path, *, read_only: bool):
    document = word.Documents.Open(
        FileName=str(path.resolve()),
        ConfirmConversions=False,
        ReadOnly=read_only,
        AddToRecentFiles=False,
        Visible=False,
        OpenAndRepair=False,
        NoEncodingDialog=True,
    )
    word.Visible = False
    full_name = str(document.FullName)
    if not same_file(full_name, path):
        raise WorkerError("external_content")
    try:
        document.UpdateStylesOnOpen = False
    except Exception:
        logging.info("could not disable style updates")
    lock_fields(document)
    try:
        document.Saved = True
    except Exception:
        logging.info("could not mark the document unchanged")
    return document


def export_pdf(document, output: Path) -> None:
    # A failed markup export must never silently become a clean PDF.
    try:
        # Use the same view for a live comparison and a reopened redline (Word
        # otherwise inherits different views in the two lanes): Word for Mac's.
        view = document.ActiveWindow.View
        view.RevisionsFilter.Markup = _REVISIONS_MARKUP_ALL
        view.RevisionsFilter.View = _REVISIONS_VIEW_FINAL
        view.ShowRevisionsAndComments = True
        view.ShowInsertionsAndDeletions = True
        view.ShowFormatChanges = True
        # Word for Mac opens a saved redline with this off and still prints its
        # comments; so does Word here (same pages either way on 24 of 24 saved
        # redlines, 2026-11-24). A live comparison result is different: with
        # this off its comments are not printed at all (tests/live_check.py).
        view.ShowComments = True
        view.RevisionsMode = _INLINE_REVISIONS
        document.ExportAsFixedFormat(
            OutputFileName=str(output),
            ExportFormat=_PDF,
            OpenAfterExport=False,
            OptimizeFor=0,
            Range=0,
            From=1,
            To=1,
            Item=_EXPORT_WITH_MARKUP,
            IncludeDocProps=False,
            KeepIRM=False,
            CreateBookmarks=0,
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )
    except pywintypes.com_error as exc:
        logging.exception("PDF export with markup failed")
        raise WorkerError("convert_failed") from exc



def lock_fields(document) -> None:
    try:
        _lock_fields(document)
    except WorkerError:
        raise
    except Exception:
        logging.exception("field lock failed")
        raise WorkerError("word_failed") from None


def _lock_fields(document) -> None:
    # StoryRanges includes headers, footnotes and text boxes. NextStoryRange
    # visits additional sections without an arbitrary 40-section rejection.
    total_fields = 0
    total_stories = 0
    for first in document.StoryRanges:
        story = first
        while story is not None:
            total_stories += 1
            fields = story.Fields
            total_fields += int(fields.Count)
            if total_fields > _MAX_FIELDS or total_stories > _MAX_STORIES:
                raise WorkerError("too_large")
            try:
                fields.Locked = True
            except pywintypes.com_error as exc:
                # Word refuses to lock fields on some documents (protection
                # among other causes). Locking is best-effort hardening,
                # never a reason to reject a job.
                logging.warning("field lock skipped (Word hresult 0x%08X)",
                                getattr(exc, "hresult", 0) & 0xFFFFFFFF)
            story = story.NextStoryRange


def scrub_properties(document) -> None:
    needles = [str(WORK_ROOT).lower(), str(Path.home()).lower()]
    try:
        props = document.BuiltInDocumentProperties
        count = int(props.Count)
    except Exception:
        return
    for index in range(1, min(count, 40) + 1):
        try:
            prop = props.Item(index)
            value = prop.Value
        except Exception:
            continue
        if isinstance(value, str) and any(needle in value.lower() for needle in needles):
            try:
                prop.Value = ""
            except Exception:
                continue


def same_file(actual: str, expected: Path) -> bool:
    try:
        return Path(actual).resolve().as_posix().lower() == expected.resolve().as_posix().lower()
    except OSError:
        return False


def assert_output(path: Path, magic: bytes, code: str) -> None:
    if not path.is_file():
        raise WorkerError("no_output")
    size = path.stat().st_size
    if size < 64:
        raise WorkerError("no_output")
    if size > 80 * 1024 * 1024:
        raise WorkerError("word_failed")
    with path.open("rb") as handle:
        if handle.read(len(magic)) != magic:
            raise WorkerError(code)


def close_document(document) -> None:
    try:
        document.Saved = True
        document.Close(SaveChanges=_DO_NOT_SAVE)
    except Exception:
        logging.exception("close failed")


def quit_word(word) -> None:
    try:
        word.DisplayAlerts = _ALERTS_NONE
    except Exception:
        logging.info("could not silence alerts during quit")
    for _ in range(10):
        try:
            count = int(word.Documents.Count)
        except Exception:
            break
        if count <= 0:
            break
        try:
            document = word.Documents.Item(1)
            document.Saved = True
            document.Close(SaveChanges=_DO_NOT_SAVE)
        except Exception:
            logging.exception("close failed")
            break
    try:
        word.Quit(SaveChanges=_DO_NOT_SAVE)
    except AttributeError:
        # The dynamic COM proxy raises AttributeError once the Word process
        # is gone. Nothing is left to quit; the lane starts a fresh Word.
        logging.info("word process already gone during quit")
    except Exception:
        logging.exception("quit failed")


def classify(exc: pywintypes.com_error, kind: str) -> WorkerError:
    text = " ".join(str(part) for part in getattr(exc, "args", ())).lower()
    if "password" in text:
        return WorkerError("password_protected")
    if "corrupt" in text or "damaged" in text or "unreadable" in text:
        return WorkerError("corrupt")
    if kind in {"compare", "compare_pdf"}:
        return WorkerError("compare_failed")
    return WorkerError("convert_failed")


def publish_word_pid(word, workdir: Path, before: set[int]) -> None:
    pid = discover_word_pid(word, before)
    if pid is None:
        logging.warning("could not determine the WINWORD pid")
        return
    (workdir / "word.pid").write_text(str(pid), encoding="ascii")


def hwnd_pid(word) -> int | None:
    try:
        hwnd = int(word.Hwnd)
    except Exception:
        return None
    if hwnd <= 0:
        return None
    _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
    if int(pid) <= 4:
        return None
    return int(pid)


def winword_pids() -> set[int]:
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"],
            text=True,
            errors="replace",
            timeout=10,
            creationflags=_NO_WINDOW,
        )
    except (subprocess.SubprocessError, OSError):
        return set()
    pids: set[int] = set()
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("INFO:"):
            continue
        try:
            row = next(csv.reader([line]))
        except csv.Error:
            continue
        if row and row[0].lower() == "winword.exe" and row[1].isdigit():
            pids.add(int(row[1]))
    return pids


def write_result(workdir: Path, ok: bool, error: str | None) -> None:
    payload = {"ok": ok, "error": error}
    (workdir / "result.json").write_text(json.dumps(payload), encoding="utf-8")


def main(argv: list[str]) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    kind = argv[2] if len(argv) == 3 and argv[1] == "serve" else "oneshot"
    log_name = kind if kind in {"compare", "convert"} else "oneshot"
    logging.basicConfig(
        level=logging.INFO,
        handlers=[RotatingFileHandler(LOG_DIR / f"{log_name}-worker.log", maxBytes=2_000_000,
                                      backupCount=3, encoding="utf-8")],
        format="%(asctime)s %(levelname)s %(message)s",
    )
    contain_process_tree()
    if len(argv) == 3 and argv[1] == "serve" and argv[2] in {"compare", "convert"}:
        return serve(argv[2])
    if len(argv) != 3 or argv[1] not in {"compare", "convert"}:
        logging.error("usage: worker serve compare|convert")
        return 2
    try:
        workdir = safe_workdir(argv[2])
    except WorkerError:
        logging.error("rejected work directory")
        return 2
    return execute(argv[1], workdir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
