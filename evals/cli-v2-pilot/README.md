<!--
SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
SPDX-License-Identifier: AGPL-3.0-only
-->

# Held-out paired workflow pilot (V2-15 / #849)

Moved here from `jubarte-redlines/eval/cli-v2-pilot` (2026-11-17), where the
issue it serves, jandira-tech/jubarte-redlines#849, still tracks it. The task
sources are now in `fixtures/`: the pilot's own two plus copies of three
jubarte test fixtures (`f4/original.docx` → `f4-original.docx`,
`multibody/multibody.docx` → `multibody.docx`, `sections/multi_section.docx`
→ `multi_section.docx`), each byte-identical to its task's sha256 pin.

This is an initial 12-task × 2-interface × 2-repetition pilot (48 runs).
It compares matched source bytes, task requirements, model/provider, agent
version and execution budget in randomized cell order. The recorded seed
controls **cell order only, not model sampling**. The harness is identical
across arms; only the jubarte binary changes. These workflow specifications
are held out from agents; most input bytes are existing regression fixtures,
so this is not a claim of an independently sampled document corpus.

V2-15 belongs above V2-12: both arms must implement `edit template` and
`edit apply` to complete the generated-template tasks. Using an older arm
that lacks those commands measures an unavailable workflow, not extraction
fidelity. No model is needed for harness verification: use the bundled stub.

## Task mix

The loader pins exactly these counts across the same six families:

| Family | Count | Tasks and coverage |
|---|---|---|
| `exact_replace` | 4 | 01: long body paragraph with nonbody stories; 02: exact replacement; 04: edit p3 in a table cell, preserving its neighbor; 12: meaningful unchanged desired state with exact source-byte delivery. |
| `multi_edit` | 1 | 03: two edits in one paragraph, including the authorized article correction to “an energetic dog”. |
| `received_redline` | 2 | 05: accept r0, edit text and reply; 06: reject r1 and edit text. Selected revisions must be absent; all other history must be preserved. |
| `comments` | 2 | 07: edit c4 and reply to that thread; 08: two notes at exact paragraph/text anchors. |
| `template_flow` | 2 | 09/10: generate source-bound PlanV2 rows, edit one/two generated row texts, then apply the saved plan. |
| `unsupported` | 1 | 11: repeated literal anchor without an authorized occurrence; refuse instead of guessing. |

Task filenames and IDs remain stable even where specifications have changed.
Task 11's small repeated-anchor fixture is authored under `fixtures/` with an
SPDX sidecar. No tests write to the repository's source fixtures.

Each task has independent checks and exact `expected_paragraphs` for its
text changes; a target paragraph ID alone authorizes no arbitrary edits.
`comment_updates` authorizes only named comment fields, and
`settled_revisions` names decisions that may remove original revisions.
Task models reject unknown fields, including misspelled selectors.

## Execution and provenance

From this directory:

```sh
uv sync
uv run python run.py \
  --arm-a /absolute/path/to/current-jubarte \
  --arm-b /absolute/path/to/v2-jubarte \
  --agent stub-agent.json \
  --runs-root /tmp/my-new-pilot \
  --repetitions 2 --seed 20260215 \
  --margin-unintended 0 --margin-preservation 0

uv run python grade.py \
  --runs-root /tmp/my-new-pilot --tasks-dir tasks --repo-root ../.. \
  --grader-binary /absolute/path/to/current-jubarte

uv run python report.py \
  --runs-root /tmp/my-new-pilot --output /tmp/my-new-pilot/report.md
```

Configuration, fixtures and binaries are validated before creating or replacing
any run root. Existing roots are refused unless they carry the exact pilot
marker and `--replace` is explicit. Replacement archives the previous root
beside it; it does not delete the old evidence. Symlink roots are refused.
`--smoke` schedules only the first task, arm A, one repetition: one invocation.

The agent working directory contains `input.docx`, `prompt.md`, its separate
stdout/stderr captures, and files it produces. Real agents receive the prompt
as a CLI argument. No task checks, rubric, expected claim or stub command
sequence is copied into their state or passed in their argv. Only the
explicit deterministic stub configuration receives a separate `stub-data/`
answer key outside the task working directory. This is a working-state
boundary, not an OS sandbox for a hostile agent with access to the host repo.

The sample `agents/*.json` select their recorded model and provider via argv;
`version_argv` probes the installed CLI version before execution. These are
example model choices; model availability is not tested by the stub. Crush
uses positional prompt text and `--model provider/model`; its installed CLI
does not accept `--json`. Codex and Pi prompt/model flags follow their CLI
help. Tests render these configurations and fake the version probe; they
never invoke a paid or real model. JSON agent-message events and plain text
final claims are parsed without interpreting tool-output events as claims.

`config.json` records arms and digests, task-family manifest, randomized
schedule, repetitions, budget, agent provenance and the predeclared harmful
edit margins. Each `runs.jsonl` row records task/prompt/input/binary hashes,
structured argv, actual copied-input hash, subprocess return code, separate
stream paths/hashes/byte counts, timestamps, stop reason, censoring, and the
actual declared artifact path/hash/size. Cancellation kills the process group,
scans any committed artifact, writes a right-censored row, then propagates.
Unrecorded harness failures cause a nonzero runner exit. Missing scheduled
cells remain visible in report denominators.

Before grading, `grade.py` verifies the recorded task, input, prompt, source,
artifact, separate stream digests and producing-arm identities and the common arm-A grader identity.
Changed bytes/rules refuse grading rather than silently attaching a new grade
to an old run. Inspection failures produce per-run error records.

## Independent outcomes and limits

- **Tool correctness:** declared effects and selected decisions are realized,
  the artifact is readable/valid, and exposed preservation holds; only a
  legitimate refusal is tool-correct without an artifact. An unchanged copy
  cannot pass an edit task. The unchanged task additionally requires exact
  source-byte identity.
- **Task completion:** independent text, revision and comment requirements,
  correct delivery, and observed integrity/preservation must hold. Comments
  check numeric-wire-schema thread parentage and exact anchors. Rubric items
  remain explicitly unassessed until external adjudication.
- **Claim accuracy:** compare success/failure/unsupported claims with observed
  artifacts and checks, never the stub's expected answer. An honest failure
  on a supported task can be accurate while failing the other axes.

Unintended text edits are compared across all stories exposed by the CLI
(body, headers, footers, footnotes, endnotes), including new/deleted paragraphs.
Sequence alignment avoids treating enumerated paragraph IDs as persistent
identities. Ambiguous repeated-text alignments require adjudication.
Preservation compares comment author/text/parent/resolved state/anchors and
revision kind/author/text, untouched run formatting, exposed paragraph
properties, table geometry, controls and structural summary fields.

The snapshot does **not** establish preservation of section properties,
bookmarks, media bytes, relationship contents, numbering definitions, or
formatting on rewritten spans. These dimensions are **not assessed**, never
reported as measured zeros. Missing/failed source or artifact inspection gives
nullable defect counts and a `not_assessed` status. Counts in the report cover
only explicitly assessed snapshot dimensions, not Word interoperability.

False-positive refusals, legitimate refusals, nonexecution and false-negative
acceptance are separate outcomes. Unintended edits and failed validation feed
false-negative acceptance and claim accuracy, as do failed requirements and
preservation defects.

The report lists every scheduled cell, missing runs/grades, right-censored
runs, inspection errors and unassessed dimensions. The harmful-edit margins
are fixed in `RunConfig` **before execution**; report-time overrides must
match them. Missing grades, unassessed, unpaired, censored or ambiguous cells
make the gate **INCONCLUSIVE**, never PASS. The margin applies only to exposed
snapshot dimensions. Expand trials where release-relevant uncertainty
remains. Human usability needs human evaluation; an LLM rubric needs an
independent artifact-sample audit. No universal effect-size claim follows
from the initial 48 runs.

## Verification

Build the CLI once in a jubarte-redlines checkout, then point the pilot at it
(or put `jubarte` on PATH):

```sh
(cd ~/T/jubarte-redlines && cargo build --bin jubarte)
export JUBARTE_CLI=~/T/jubarte-redlines/target/debug/jubarte
cd evals/cli-v2-pilot
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

`uv run pytest` includes pytest-cov, line/branch measurement, a terminal missing
report and `Coverage: …% lines, …% branches`. Subprocess coverage includes the
runner, grader, reporter and model-free stub. Real disk/process/CLI tests are
integration tests with temporary state; pure grading tests use in-memory
snapshots, and process/version failure paths use fakes. Tests reuse
`JUBARTE_CLI` and do not launch a second build when it is set.

The governing designs are
[`jubarte-edit-implementation-plan.md`](../../docs/design/cli-v2/jubarte-edit-implementation-plan.md),
[`jubarte-template-implementation-plan.md`](../../docs/design/cli-v2/jubarte-template-implementation-plan.md),
and [`jubarte-cli-evidence-review.md`](../../docs/design/cli-v2/jubarte-cli-evidence-review.md).
The CLI owns request/effect fidelity; the agent owns substantive choices;
the harness owns execution/provenance; the evaluation process owns independent
requirements and adjudication. Stub success is harness evidence only.
