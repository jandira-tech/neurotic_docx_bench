"""scripts/release_conv_queue.py: the control cohort holds exactly the requested size."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'release_conv_queue.py'
spec = importlib.util.spec_from_file_location('release_conv_queue', SCRIPT)
rcq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcq)


def test_the_control_holds_exactly_the_requested_count():
    # per-state rounding gave 12 + 12 + 10 + 15 = 49 of 50 on this split
    sizes = {'clean': 150, 'tracking': 150, 'comments': 125, 'mixed': 175}
    shares = rcq.allocate(50, sizes)
    assert sum(shares.values()) == 50
    assert all(abs(shares[s] - 50 * n / 600) < 1 for s, n in sizes.items())


def test_the_allocation_is_deterministic_and_never_exceeds_a_state():
    sizes = {'a': 1, 'b': 1, 'c': 1}
    assert rcq.allocate(2, sizes) == {'a': 1, 'b': 1, 'c': 0}
    assert rcq.allocate(3, sizes) == {'a': 1, 'b': 1, 'c': 1}
