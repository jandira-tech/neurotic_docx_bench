"""Check specified documents without launching Word or printing their contents."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from word_endpoint.guard import GuardError, prepare_docx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("documents", nargs="+")
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    baseline = None
    if args.baseline:
        spec = importlib.util.spec_from_file_location("baseline_guard", args.baseline)
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
    failures = 0
    for raw in args.documents:
        path = Path(raw)
        row = {"file": path.name}
        try:
            data = path.read_bytes()
            row["bytes"] = len(data)
            if baseline:
                try:
                    baseline.validate_docx(data)
                    row["baseline"] = "accepted"
                except baseline.GuardError as exc:
                    row["baseline"] = exc.code
            cleaned = prepare_docx(data)
            row["updated"] = "accepted"
            row["template_detached"] = cleaned != data
        except GuardError as exc:
            row.update(updated=exc.code, reason=exc.reason, part=exc.part)
            failures += 1
        except OSError as exc:
            row.update(updated="unreadable", reason=type(exc).__name__)
            failures += 1
        print(json.dumps(row))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
