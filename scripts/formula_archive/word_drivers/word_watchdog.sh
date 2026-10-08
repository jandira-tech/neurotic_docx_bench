#!/bin/zsh
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
# word_watchdog.sh PATH... (logs or output folders) : kill Word when none of the logs has grown for WD_SECS (default 60s) while Word runs,
# so word_pdf.py / word_redline.py recycle it and resume (a modal dialog blocks their own timeouts).
# Only an idle Word is frozen: a modal leaves it near 0% CPU, a long export keeps it busy (WD_CPU, default 5%).
# A busy Word is still killed after WD_MAX seconds of silence (default 300).
last=""; since=$(date +%s)
while true; do
  cur=$(ls -lT "$@" 2>/dev/null | md5)
  now=$(date +%s)
  if [ "$cur" != "$last" ]; then last=$cur; since=$now
  elif pgrep -x "Microsoft Word" >/dev/null && [ $((now-since)) -ge ${WD_SECS:-60} ]; then
    cpu=$(ps -o %cpu= -p $(pgrep -x "Microsoft Word" | head -1) | tr -d " " | cut -d. -f1)
    if [ "${cpu:-0}" -ge ${WD_CPU:-5} ] && [ $((now-since)) -lt ${WD_MAX:-300} ]; then echo "$(date +%T) quiet $((now-since))s but Word busy (${cpu}% CPU): waiting"; sleep 15; continue; fi
    echo "$(date +%T) no log growth for $((now-since))s, Word idle (${cpu}% CPU): killing Word"; pkill -9 -x "Microsoft Word"; since=$now
  fi
  sleep 15
done
