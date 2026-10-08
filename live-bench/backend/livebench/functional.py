# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from neurotic_docx_bench.functional_lens import check_functional

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="livebench-functional-") as folder:
        result = check_functional(*map(Path, sys.argv[1:4]), Path(folder))
        print(json.dumps(asdict(result), allow_nan=False))
