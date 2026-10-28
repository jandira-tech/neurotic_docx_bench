"""Hold the mbx target's shared lease only while the original scoring parent lives.

This preserves in-flight workers' already-imported binary path. New runs use the
byte-identical local bin/page-metrics copy instead of the evictable cache path.
"""
import fcntl
import os
import sys
import time
from pathlib import Path

parent_pid = int(sys.argv[1])
target = Path.home() / 'temp/T/docxide-pdf/tools/target'
lock = Path(str(target.resolve()) + '.lock')
with lock.open('a') as stream:
    fcntl.flock(stream, fcntl.LOCK_SH)
    print(f'Native scorer target lease held for PID {parent_pid}', flush=True)
    while True:
        try:
            os.kill(parent_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(1)
