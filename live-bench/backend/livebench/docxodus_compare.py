# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Single pair through the official Docxodus Python wheel and its .NET host."""

import sys
from pathlib import Path

from docx_scalpel import DocxDiffSettings, docx_diff_compare, shutdown_host


def main():
    previous, current, output = map(Path, sys.argv[1:])
    try:
        # Matches Docxodus' Word-Compare entrypoint's input-revision policy.
        redline = docx_diff_compare(
            previous.read_bytes(), current.read_bytes(), DocxDiffSettings(pre_accept_input_revisions=True)
        )
        output.write_bytes(redline)
    finally:
        shutdown_host()


if __name__ == "__main__":
    main()
