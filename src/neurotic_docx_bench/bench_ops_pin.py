"""The reviewed bench-ops commit used by the release contract.

The package is deliberately not an ndb venv dependency (#134): ordinary
``uv run bench`` commands use the project's own environment, while the release
contract rides in a small overlay.  Keeping the pin here lets the plain CLI
and the PEP 723 release script name exactly the same reviewed commit.
"""

BENCH_OPS_SHA = "6478817465f67726c1450dbeaf090a9fa7ca44b2"
BENCH_OPS_REQUIREMENT = f"bench-ops @ git+https://github.com/arthrod/bench-ops@{BENCH_OPS_SHA}"
