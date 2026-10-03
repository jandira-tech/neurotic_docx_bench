#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# usage: run_pdf300.sh NAME BIN  -> /tmp/pdf-300/NAME.json, work dir /tmp/pdf-300/work-NAME
set -u
NAME=$1; BIN=$2
cd ~/T/neurotic_docx_bench || exit 1
ARGS=()
while IFS= read -r f; do ARGS+=(--files-list "$f"); done < /tmp/pdf-300/list.txt
uv run bench docx-to-pdf --converter "$BIN" --origin list "${ARGS[@]}" \
  --json /tmp/pdf-300/$NAME.json --work-dir /tmp/pdf-300/work-$NAME --jobs 3 --convert-workers 3 \
  > /tmp/pdf-300/$NAME.log 2>&1
echo "PDF300 $NAME DONE exit $?" >> /tmp/pdf-300/$NAME.log