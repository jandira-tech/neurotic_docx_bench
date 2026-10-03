# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json
rows = json.load(open('/tmp/measure_rows.json'))
for k, t in (("chars/max", 0.1229), ("chars/max_nosp", 0.1445)):
    print(f"\n{k} @ {t}: errors")
    for r in rows:
        if (r[k] >= t) != r["W"]:
            print(f"  {r['wave']:10} {r['name']:28} {'word-level' if r['W'] else 'replaced':10} {k}={r[k]:.4f} words/max={r['words/max']:.3f} runs/max_words={r['runs/max_words']:.3f}")