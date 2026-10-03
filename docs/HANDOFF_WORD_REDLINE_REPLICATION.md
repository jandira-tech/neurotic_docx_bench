# Handoff: replicating the search for Word's redline algorithm

This is a methodology handoff. It tells you how the result was reached,
not what the result is, and it hands over no code. Your job is to
rediscover, by measurement, the rule Microsoft Word applies when it
compares two documents and decides how to mark a changed paragraph:
when it marks the paragraph word by word, when it strikes the whole
paragraph and inserts the new one, and where it anchors the marks. If
your rule and the one on `main` agree, both stand on evidence. If they
disagree, one of them is wrong, and the probes will say which.

Read `AGENTS.md` first. Everything below assumes its rules: Word is the
only oracle, it is driven only through the scripts named there, and a
conversion that fails scores zero.

## What "done" means

- A rule stated in one sentence, with its constants, that predicts
  Word's verdict on every probe paragraph you made and on the corpus
  pairs, and whose misses you can attribute to something other than the
  rule (name it).
- A prediction script that, given two paragraphs, outputs the verdict
  the rule predicts, and an evaluation script that scores it against
  Word's own redlines (`scripts/` is where these live; name yours after
  the question they answer, not after today's date).
- A measurement of the rule inside the engine against a control group
  that you did not tune on, with the paired difference and its
  confidence interval, and a second measurement on a holdout you never
  opened.

Numbers without a holdout are not done. A holdout you looked at is not
a holdout.

## The oracle

Word's own compare (Review › Compare) is the ground truth. The corpus
under `corpus/word/` holds thousands of pairs with Word's redline of
each pair, and `scripts/word_redline.py` makes new ones. Run it in its
default batch mode first; rerun the dropped pairs with the flag that
disables the one-redline osascript; run `scripts/check_redline_identity.py`
on every batch before you score anything, because a redline that is not
the pair its filename names will teach you a false rule. Keep the
watchdog pointed at the folder the current job grows. Word freezing is
normal; the watchdog clears it.

Word is noisy in one specific way you must learn early: typing anything
while a batch runs leaves phantom deletions in the output. The identity
check misses those; an exact rebuilt-text check catches them. Build that
check before you build anything else.

## Method: St. Thomas

Every decision is a measured decision. The cycle is always the same and
you do not skip a step because the answer "is obvious":

1. State the hypothesis as a rule that makes a prediction on a document
   you have not yet put through Word.
2. Write the prediction down before Word runs: which paragraphs will be
   word-level, which replaced, where the anchors fall. A prediction
   written after the result is not a prediction.
3. Build the probe documents. Synthetic, minimal, one variable per
   document. Keep the package valid (the OOXML validator in the engine
   repository, `tools/validate-docx`, must pass; Word's repair prompt
   is a failed probe).
4. Put them through Word. Measure the verdict from the redline's XML,
   not from a rendering.
5. Score the prediction. Count the misses. Read every miss in the XML.
6. If a miss has an explanation outside the rule (the aligner chose a
   different anchor, a run boundary, a field), record it as such and
   keep the rule. If not, the rule is wrong: refine it or refute it, and
   write the refuted version down so nobody revives it.
7. Only then touch the engine. Then measure the engine on the control
   group, then on the holdout.

A rule that explains the corpus but has not predicted a fresh probe is a
story, not a finding.

## How to design the probes

Word's verdict depends on what the two paragraphs share, so your probes
vary that dimension and hold everything else constant. Things that
turned out to matter, or to be worth ruling out explicitly:

- The amount of text the two sides share, as a fraction, and of which
  side's length. Vary the fraction finely (steps of a few percent) across
  the range where the verdict flips, and vary which side is longer.
- Paragraph length, from a handful of words to thousands. A rule that
  only works at one length is two rules.
- Whether the shared text is one run of consecutive words or scattered
  single words. Whether it sits at the start, the end, or the middle.
- Punctuation and blanks. Decide, by measurement, whether a shared space
  or comma counts as shared text, and whether the paragraph mark counts
  as a character. These details move the constant you will fit, so pin
  them down with probes built for that question alone.
- Multi-paragraph regions: a changed region spanning several paragraphs
  behaves differently from a single changed paragraph. Probe the
  single-paragraph case to exhaustion first, then the region case, and
  do not let the second contaminate the first.
- Realistic edits (a sentence rewritten, a clause inserted, a list
  reordered) as a separate wave, after the synthetic waves: synthetic
  probes find the rule, realistic ones find what the rule does not cover.

Hundreds of probe paragraphs per wave is normal; a wave of ten teaches
little. Long file stems break Word's staging ("File name too long");
stage long pairs under short ids and keep a map back.

## What to refute on purpose

Write down the competing explanations before you fit anything, and
build at least one probe that separates each pair of them. Candidates
you should expect to have to kill or confirm include: a threshold on the
shorter side, a threshold on the longer side, a threshold on the total,
a minimum paragraph length below which Word always goes word by word,
anchoring on a shared prefix or suffix, a rule in terms of runs rather
than characters, and a rule with more than one constant. Your final rule
is the simplest one that survives; every refuted candidate is recorded
with the probe that refuted it.

## Measuring the engine

- The engine's redline is scored against Word's by the bench's redline
  scorer; the per-paragraph verdict agreement is the metric for the rule
  itself, the document score is the metric for the engine.
- Control group: a seeded random sample of pairs from across the corpus
  sets, large enough that a change of a tenth of a point is resolved
  (two thousand pairs was the size used). Report mean, median, the paired
  difference with a bootstrap interval, wins and losses beyond half a
  point, and the largest losses by stem. Read every loss above a point in
  the XML; a control group loss is how the engine's other bugs announce
  themselves.
- Holdout: a smaller, stratified set you select before you start and
  never open: never diagnose, probe, or tune against it. A build is done
  only if, on the holdout, mean and median together drop by less than
  0.1 and no document newly falls below 50 or below 90. Otherwise it is
  not done: find the cause in the control group or in probes.
- A fresh output directory per binary; the evaluation harness skips
  existing outputs silently otherwise.
- Rebuild the bench's engine binary from the engine checkout for every
  measurement. Never patch a copied binary.

## Reporting

For each decision: the hypothesis, the prediction written beforehand,
the probe count, the hit rate, the misses and their attribution, the
refuted alternatives, the control-group numbers, the holdout numbers.
Commit and push the prediction and evaluation scripts with the finding,
on a branch, often. If you cannot show the prediction you wrote before
the measurement, the measurement does not count.

## Agents

You may dispatch agents, sparingly, with `pi -p '<prompt>'`. Use them to
excavate (read XML, tabulate verdicts), not to decide; every verdict on
a hypothesis is yours and is backed by a probe you can name.
