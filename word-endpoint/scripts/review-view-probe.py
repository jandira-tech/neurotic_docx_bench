"""Read Word's revision options and review view here, through the endpoint's own worker code.

    python scripts/review-view-probe.py dump [<docx>...]
    python scripts/review-view-probe.py export <out_dir> <view>... -- <docx>...

Word cannot open documents from an ssh (session 0) shell: run this through
scripts/run-in-session.ps1, which runs it once in the interactive session.

``dump`` prints the Word options the endpoint sets (``worker._MAC_REVISION_OPTIONS``) and the
view Word opens each document in. ``export`` opens each document the way /v1/convert does
(read-only, properties scrubbed) and exports it with markup under each named view:

* ``endpoint``: ``worker.export_pdf``, the view the endpoint ships;
* ``untouched``: the view Word opened the document in, unchanged;
* ``mixed``: the pre-2026-11-24 endpoint (balloons for comments and formatting when the
  document has comments, inline otherwise).

The last line printed is ``RESULT <json>``. docs/review-view.md has what this read on
2026-11-24 and how the views scored against Word for Mac's PDFs.
"""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pythoncom  # noqa: E402

from word_endpoint import worker as W  # noqa: E402

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="LOG %(levelname)s %(message)s")

VIEW = ["MarkupMode", "RevisionsMode", "RevisionsView", "ShowRevisionsAndComments", "ShowInsertionsAndDeletions",
        "ShowFormatChanges", "ShowComments", "ShowInkAnnotations", "RevisionsBalloonShowConnectingLines",
        "RevisionsBalloonSide", "RevisionsBalloonWidth", "RevisionsBalloonWidthType"]
OPTIONS = [name for name, _ in W._MAC_REVISION_OPTIONS] + ["RevisionsBalloonPrintOrientation"]


def read(obj, names):
    out = {}
    for name in names:
        try:
            value = getattr(obj, name)
            out[name] = value if isinstance(value, (int, float, str, bool)) or value is None else str(value)
        except Exception as exc:
            out[name] = f"error {type(exc).__name__}"
    return out


def view_of(document):
    view = document.ActiveWindow.View
    out = read(view, VIEW)
    out["RevisionsFilter.Markup"] = view.RevisionsFilter.Markup
    out["RevisionsFilter.View"] = view.RevisionsFilter.View
    return out


def _export_as(document, output: Path) -> None:
    document.ExportAsFixedFormat(OutputFileName=str(output), ExportFormat=W._PDF, OpenAfterExport=False,
                                 OptimizeFor=0, Range=0, From=1, To=1, Item=W._EXPORT_WITH_MARKUP,
                                 IncludeDocProps=False, KeepIRM=False, CreateBookmarks=0, DocStructureTags=True,
                                 BitmapMissingFonts=True, UseISO19005_1=False)


def _mixed(document, output: Path) -> None:
    view = document.ActiveWindow.View
    view.ShowRevisionsAndComments = True
    view.ShowComments = True
    view.RevisionsMode = 2 if int(document.Comments.Count) else 1
    _export_as(document, output)


VIEWS = {"endpoint": W.export_pdf, "untouched": _export_as, "mixed": _mixed}


def export(word, path: Path, output: Path, name: str) -> dict:
    document = W.open_document(word, path, read_only=True)
    try:
        W.scrub_properties(document)
        before = view_of(document)
        started = time.monotonic()
        VIEWS[name](document, output)
        return {"doc": path.name, "view": name, "comments": int(document.Comments.Count),
                "seconds": round(time.monotonic() - started, 2), "view_opened": before,
                "view_exported": view_of(document), "ok": output.is_file()}
    finally:
        W.close_document(document)


def run(word, argv, result) -> None:
    if argv[0] == "dump":
        result["docs"] = {}
        for path in map(Path, argv[1:]):
            document = W.open_document(word, path, read_only=True)
            try:
                result["docs"][path.name] = view_of(document) | {"comments": int(document.Comments.Count)}
            finally:
                W.close_document(document)
    elif argv[0] == "export":
        out_dir, split = Path(argv[1]), argv.index("--")
        views, docs = argv[2:split], [Path(p) for p in argv[split + 1:]]
        unknown = sorted(set(views) - set(VIEWS))
        if unknown:
            raise SystemExit(f"unknown view(s) {unknown}; known: {sorted(VIEWS)}")
        result["exports"] = []
        for name in views:
            (out_dir / name).mkdir(parents=True, exist_ok=True)
            for path in docs:
                try:
                    row = export(word, path, out_dir / name / f"{path.stem}.pdf", name)
                except Exception as exc:
                    row = {"doc": path.name, "view": name, "ok": False, "error": repr(exc)[:300]}
                result["exports"].append(row)
                print(f"{name} {path.name} {row['ok']}", flush=True)
    else:
        raise SystemExit(__doc__)


def main(argv) -> None:
    if not argv:
        raise SystemExit(__doc__)
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    word = W.start_word()  # sets the revision options, as the endpoint's workers do
    try:
        if not W._wait_word_ready(word):
            raise SystemExit("Word did not answer")
        result = {"version": str(word.Version), "build": str(word.Build), "options": read(word.Options, OPTIONS)}
        run(word, argv, result)
        print("RESULT " + json.dumps(result))
    finally:
        W.quit_word(word)
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main(sys.argv[1:])
