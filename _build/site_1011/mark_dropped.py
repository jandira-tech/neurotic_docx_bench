"""Hide, per case, the engine columns whose stale results were removed (2026-10-11).

    python3 -I mark_dropped.py index.html jubarte libreoffice     # after patch_site.py d2p

A case gets `dropped`: the engines it had in the published page (git HEAD) and no longer has.
The viewer leaves those columns out for that case instead of drawing empty ones. Engines a
case never had (an old failure, a tool not run) keep their column as before.
"""

from __future__ import annotations

import json
import subprocess
import sys

from patch_site import SITE, once, split

FILTER = "const on = ENGINES.filter(([k]) => state.on[k]);"
NEW = "const on = ENGINES.filter(([k]) => state.on[k] && !(c.dropped || []).includes(k));"


def main(rel: str, keys: list[str]) -> None:
    path = SITE / rel
    _, old, _ = split(subprocess.run(["git", "-C", str(SITE), "show", f"HEAD:{rel}"],
                                     capture_output=True, text=True, check=True).stdout)
    had = {(c["group"], c["case"]): {k for k in keys if k in c["pages"] or k in c.get("page_counts", {})} for c in old}
    head, data, tail = split(path.read_text())
    n = 0
    for c in data:
        gone = sorted(had.get((c["group"], c["case"]), set()) - set(c["pages"]) - set(c.get("page_counts", {})))
        if gone:
            c["dropped"] = gone
            n += 1
    if NEW not in tail:
        tail = once(tail, FILTER, NEW)
    path.write_text(head + "const DATA = " + json.dumps(data, ensure_ascii=False) + tail)
    print(f"{rel}: {n} cases hide {', '.join(keys)} where removed")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
