# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""wordflag.py: `--revisions word` for binaries that know it (older ones paint Word's marks by default)."""
import subprocess,functools,os
@functools.lru_cache(None)
def word_flag(binp):
    h=subprocess.run([binp,"convert","--help"],capture_output=True,text=True).stdout
    # JUBARTE_FLAGS (e.g. --compress) rides along on every convert.
    return (["--revisions","word"] if "--revisions" in h else [])+os.environ.get("JUBARTE_FLAGS","").split()
