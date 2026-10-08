-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
-- SPDX-License-Identifier: AGPL-3.0-only
-- Every new score updates a small cohort row, so polling cost stays bounded as history grows.
CREATE TABLE bench_cohorts (
  run_id TEXT NOT NULL,
  tool TEXT NOT NULL,
  benchmark TEXT NOT NULL,
  reference_tool TEXT NOT NULL,
  reference_renderer TEXT NOT NULL,
  count INTEGER NOT NULL,
  broken INTEGER NOT NULL,
  score_sum REAL NOT NULL,
  PRIMARY KEY (run_id, tool, benchmark, reference_tool, reference_renderer)
);

INSERT INTO bench_cohorts
SELECT run_id, tool, benchmark, reference_tool, COALESCE(reference_renderer, ''),
       COUNT(*), SUM(status = 'broken'), SUM(CASE WHEN status = 'broken' THEN 0 ELSE overall END)
FROM bench_scores
WHERE status IN ('ok', 'broken') AND overall IS NOT NULL AND tool != reference_tool
GROUP BY run_id, tool, benchmark, reference_tool, COALESCE(reference_renderer, '');

CREATE TRIGGER bench_score_rollup AFTER INSERT ON bench_scores
WHEN NEW.status IN ('ok', 'broken') AND NEW.overall IS NOT NULL AND NEW.tool != NEW.reference_tool
BEGIN
  INSERT INTO bench_cohorts VALUES (
    NEW.run_id, NEW.tool, NEW.benchmark, NEW.reference_tool, COALESCE(NEW.reference_renderer, ''),
    1, NEW.status = 'broken', CASE WHEN NEW.status = 'broken' THEN 0 ELSE NEW.overall END
  ) ON CONFLICT (run_id, tool, benchmark, reference_tool, reference_renderer) DO UPDATE SET
    count = count + 1,
    broken = broken + excluded.broken,
    score_sum = score_sum + excluded.score_sum;
END;
