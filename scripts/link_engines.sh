#!/bin/zsh
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
# Link the engine checkouts this bench builds against into src/neurotic_docx_bench/utils/, the one
# place code and configs look for them (the links are gitignored). Override any source with its env var.
#
#   zsh scripts/link_engines.sh            # defaults: siblings of this repo
set -eu
here=${0:A:h:h}
T=${ENGINES_ROOT:-${here:h}}
U=$here/src/neurotic_docx_bench/utils
link() {  # link <target> <link path>
  local target=$1 dst=$2
  if [[ ! -e $target ]]; then echo "skip  ${dst#$here/} (no $target)"; return; fi
  mkdir -p ${dst:h}
  if [[ -L $dst ]]; then rm $dst; elif [[ -e $dst ]]; then echo "keep  ${dst#$here/} (a real folder)"; return; fi
  ln -s $target $dst && echo "link  ${dst#$here/} -> $target"
}
link ${JUBARTE_REDLINES:-$T/jubarte-redlines}           $U/jubarte/jubarte-redlines     # Rust engine + CLI (target/release/jubarte)
link ${JUBARTE_FIRST:-$T/jubarte-first}                 $U/jubarte/jubarte-first        # TS engine (dual-path and speed benches)
link ${JUBARTE_RUST_INPROC:-$T/jubarte-redlines/jubarte-rust-inproc} $U/jubarte/jubarte-rust-inproc
link ${JUBARTE_WASM:-$T/jubarte-redlines/jubarte-wasm}  $U/jubarte/jubarte-wasm
link ${OOXMLSDK:-$T/ooxmlsdk}                           $U/docxodus/ooxmlsdk            # Docxodus C# build the in-process adapter references
link ${FOLIO_CHECKOUT:-$T/reconciliation_plan/folio}    $U/folio-checkout               # folio source (redline scoreboard judge)
# working folder of the 2026-09 jubarte loop (runs/, holdout lists) that scripts/formula_archive reads
link ${JUBARTE_LOOP:-$T/jubarte-loop}                    $here/results/jubarte-loop
