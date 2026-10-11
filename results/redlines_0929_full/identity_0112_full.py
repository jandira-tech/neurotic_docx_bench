#!/usr/bin/env python3
"""The full 0.11.2 lane (jubarte-pdf29) against the release sample lane
(jubarte-pdf25) on the pairs both redlined: byte-identical docx, or else the
first zip member that differs. Word exports only what is new or different.

    python3 identity_0112_full.py   (from this folder)
Writes identity_0112_full.tsv: key, verdict (same | differs:<member> | only_full).
"""

import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FULL = HERE / "jubarte-0.11.2-full" / "docx"
SAMPLE = HERE / "jubarte-0.11.2" / "docx"


def key_of(path: Path, tool: str) -> str:
    return path.name[: -len(f"_{tool}.docx")]


def first_diff(a: Path, b: Path) -> str:
    with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
        names = sorted(set(za.namelist()) | set(zb.namelist()))
        for name in names:
            try:
                if za.read(name) != zb.read(name):
                    return name
            except KeyError:
                return f"{name} (absent on one side)"
    return "zip framing only"


def main() -> None:
    sample = {key_of(p, "jubarte-0.11.2"): p for p in SAMPLE.glob("*_jubarte-0.11.2.docx")}
    rows, same, differs = [], 0, 0
    for p in sorted(FULL.glob("*_jubarte-0.11.2-full.docx")):
        k = key_of(p, "jubarte-0.11.2-full")
        s = sample.get(k)
        if s is None:
            rows.append((k, "only_full"))
        elif s.read_bytes() == p.read_bytes():
            rows.append((k, "same"))
            same += 1
        else:
            rows.append((k, f"differs:{first_diff(s, p)}"))
            differs += 1
    out = HERE / "identity_0112_full.tsv"
    out.write_text("".join(f"{k}\t{v}\n" for k, v in rows))
    matched = sum(1 for k in sample if any(r[0] == k for r in rows))
    print(f"full {len(rows)} | sample {len(sample)} | matched keys {matched} | same {same} | differs {differs}")


if __name__ == "__main__":
    main()
