import random
from pathlib import Path

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.config import load_config

cfg = load_config(Path("bench.yaml"))
index = pipeline._index_redlines_union([cfg.source_of_truth, *cfg.extra_oracle_dirs], None)
keys = sorted(index)
print("universe:", len(keys))
sample = sorted(random.Random(0xD0C5).sample(keys, 20))
out = Path("/Users/arthrod/temp/T/bench-recovery/holdout_keys.txt")
out.write_text("\n".join(sample) + "\n")
print("\n".join(sample))
