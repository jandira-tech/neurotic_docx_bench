# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Where do Word's revision boundaries fall, and what are the one-word islands?"""
import collections
import re
import sys

sys.path.insert(0, "/tmp")
import redline_stats as rs  # noqa: E402

SENT = re.compile(r"[.?!:;]\s*$")


def shape(path, big=8):
    paras = rs.segs(path)
    starts_at_sentence = ends_at_sentence = n_big = 0
    single = collections.Counter()
    pairs = isolated = 0
    whole = []
    for m in paras:
        total_words = sum(len(rs.words(t)) for _, t in m)
        for i, (k, t) in enumerate(m):
            w = len(rs.words(t))
            if k == "eq":
                if 0 < i < len(m) - 1 and w == 1:
                    single[rs.words(t)[0].lower()] += 1
                continue
            if k == "del":
                if i + 1 < len(m) and m[i + 1][0] == "ins":
                    pairs += 1
                elif i == 0 or m[i - 1][0] != "ins":
                    isolated += 1
            if w >= big:
                n_big += 1
                before = m[i - 1][1] if i > 0 and m[i - 1][0] == "eq" else ""
                if i == 0 or SENT.search(before) or before.endswith("\n"):
                    starts_at_sentence += 1
                if i == len(m) - 1 or SENT.search(t) or t.endswith("\n"):
                    ends_at_sentence += 1
            if w == total_words and len(m) == 1:
                whole.append(w)
    name = path.split("/")[-1]
    print(
        f"{name:44} big-revs={n_big} start@sentence={starts_at_sentence} end@sentence={ends_at_sentence} "
        f"del+ins pairs={pairs} isolated-del={isolated} whole-para={whole}"
    )
    print("   one-word islands:", single.most_common(12))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        shape(p)
