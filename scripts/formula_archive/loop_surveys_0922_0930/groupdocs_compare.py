# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Compare two docx with GroupDocs Comparison Cloud.

usage: uv run --script groupdocs_compare.py SOURCE.docx TARGET.docx OUT.docx

Uploads both files to the API's storage, POSTs /comparison/comparisons with
an OutputPath, and downloads the result. The token comes from
RAPID_API_TOKEN in jubarte-redlines/.env (a GroupDocs Cloud JWT, sent to
api.groupdocs.cloud directly); it is never printed.
"""

import sys
import uuid
from pathlib import Path

import httpx

ENV = Path.home() / "temp/T/jubarte-redlines/.env"


def env() -> dict[str, str]:
    out = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    src, tgt, dst = map(Path, sys.argv[1:4])
    e = env()
    token = e["RAPID_API_TOKEN"].removeprefix("Bearer ")
    # The token is a GroupDocs Cloud JWT (iss api.groupdocs.cloud), not a
    # RapidAPI key: RapidAPI refuses it, GroupDocs takes it as a bearer.
    base = "https://api.groupdocs.cloud/v2.0/comparison"
    auth_modes = [{"Authorization": f"Bearer {token}"}]
    run = f"jubarte-{uuid.uuid4().hex[:8]}"
    with httpx.Client(timeout=300) as c:
        headers = None
        for mode in auth_modes:
            h = dict(mode)
            r = c.put(
                f"{base}/storage/file/{run}/source.docx",
                headers=h,
                files={"File": ("source.docx", src.read_bytes())},
            )
            print("upload source", next(iter(mode)), r.status_code, r.text[:300])
            if r.status_code < 300:
                headers = h
                break
        if headers is None:
            return 1
        r = c.put(
            f"{base}/storage/file/{run}/target.docx",
            headers=headers,
            files={"File": ("target.docx", tgt.read_bytes())},
        )
        print("upload target", r.status_code, r.text[:300])
        r.raise_for_status()
        body = {
            "SourceFile": {"FilePath": f"{run}/source.docx"},
            "TargetFiles": [{"FilePath": f"{run}/target.docx"}],
            "OutputPath": f"{run}/result.docx",
        }
        r = c.post(f"{base}/comparisons", headers=headers, json=body)
        print("compare", r.status_code, r.text[:500])
        r.raise_for_status()
        r = c.get(f"{base}/storage/file/{run}/result.docx", headers=headers)
        print("download", r.status_code, len(r.content))
        r.raise_for_status()
        dst.write_bytes(r.content)
        print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
