# Contributing to neurotic-docx-bench

Thank you for your interest in contributing to neurotic-docx-bench! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.14+
- Node.js 18+
- LibreOffice 26.2.4.2 (for rendering DOCX to PDF)
- uv (Python package manager)
- bun (Node.js package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/arthrod/neurotic-docx-bench.git
cd neurotic-docx-bench

# Install Python dependencies
uv sync

# Install Node.js dependencies
bun install --frozen-lockfile
```

### Running Tests

```bash
# Python tests
uv run pytest -q

# TypeScript tests
bunx vitest run
```

### Running the Benchmark

```bash
# Run all benchmarks
uv run bench run

# Run a specific tool
uv run bench run --only jubarte-final-lossless --limit 5

# Run speed benchmark
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl
```

## Project Structure

- `src/neurotic_docx_bench/` - Python benchmark core
- `scripts/` - TypeScript/Node.js redline generators
- `corpus/word_based/` - Test corpus (DOCX files, PDF oracles)
- `tests/` - Python and TypeScript tests
- `harness/` - Viewer harnesses for visual benchmarks
- `results/` - Benchmark results and reports

## Adding a New Tool

To add a new DOCX redline tool to the benchmark:

1. **Create a generator** - Add a generator in `scripts/generate-native-redlines.ts` (Node) or create a Python generator module
2. **Write to correct format** - Generators must write `<base>_<next>_<tool>_redline.docx` files
3. **Handle failures** - Write failures to `$RUN_DIR/generate_failures.json` and don't abort on partial failure
4. **Add to bench.yaml** - Add a run configuration with version source
5. **Add tests** - Add pytest or vitest tests that assert the tool emits `w:ins`/`w:del`

See AGENTS.md for detailed guidelines.

## Version Bumping

When preparing a release:

1. Update the version using the bump script:
   ```bash
   node --import tsx scripts/bump-version.ts <major|minor|patch>
   ```

2. Update CHANGELOG.md with release notes for the new version

3. Commit the changes:
   ```bash
   git add pyproject.toml package.json CHANGELOG.md
   git commit -m "chore: bump version to X.Y.Z"
   ```

4. Create and push a git tag:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

## Code Style

- **Python**: Follow PEP 8, use `uv run ty .` for type checking
- **TypeScript**: Use the provided TypeScript config, run `bun run typecheck` and `bun run lint`
- **Testing**: Maintain test coverage; new features should include tests

## Important Invariants

- **Scoring core**: The scoring modules (`score.py`, `diff.py`, `raster.py`, `report.py`, `html_report.py`) are lifted verbatim from superdoc-visual-benchmarks. Do not edit their logic—`tests/test_parity.py` guards byte-identical scoring.
- **LibreOffice version**: The benchmark is pinned to LibreOffice 26.2.4.2 for consistent rendering. CI regenerates the oracle in-image.
- **Tool versions**: Tool versions are pinned in `bench.yaml`. Do not bump to `@latest` without re-review.

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run the test suite to ensure everything passes
5. Commit your changes with clear messages
6. Push to your fork and submit a pull request

## Questions?

Feel free to open an issue for questions or discussion about potential contributions.
