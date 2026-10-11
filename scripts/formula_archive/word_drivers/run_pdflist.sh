#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# usage: run_pdflist.sh DIR LIST NAME BIN -> DIR/NAME.json, work dir DIR/work-NAME
set -u
DIR=$1; LIST=$2; NAME=$3; BIN=$4
cd ~/T/neurotic_docx_bench || exit 1
ARGS=()
while IFS= read -r f; do ARGS+=(--files-list "$f"); done < "$LIST"
uv run bench docx-to-pdf --converter "$BIN" --origin list "${ARGS[@]}" \
  --json "$DIR/$NAME.json" --work-dir "$DIR/work-$NAME" --jobs 3 --convert-workers 3 \
  > "$DIR/$NAME.log" 2>&1
echo "PDFLIST $NAME DONE exit $?" >> "$DIR/$NAME.log"