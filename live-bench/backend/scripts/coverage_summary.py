# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path

totals = json.loads(Path("coverage.json").read_text())["totals"]
print(
    f"Coverage: {100 * totals['covered_lines'] / totals['num_statements']:.1f}% lines, "
    f"{100 * totals['covered_branches'] / totals['num_branches']:.1f}% branches"
)
