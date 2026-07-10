# neurotic-docx-bench runtime image: LibreOffice (soffice) + Python 3.14/uv + Node/bun +
# Playwright Chromium. See docker-compose.yml / .github/workflows/bench.yml for usage.
#
# LibreOffice version note (plan Context §7): the committed oracle PDFs were rendered by
# LibreOffice 26.2.4.2. Rather than pin that exact build (hard across distros), CI
# REGENERATES the oracle in-image from the committed Word redline DOCX using whatever
# LibreOffice this image ships — so oracle and candidates share one renderer and the
# identity/parity holds regardless of version. (Locally, the committed PDFs are used as-is.)
FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# System deps: LibreOffice (headless), fonts, and Playwright/Chromium prerequisites.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer libreoffice-core \
        fonts-liberation fonts-dejavu fonts-noto \
        curl ca-certificates git unzip \
    && rm -rf /var/lib/apt/lists/*

# uv (Python 3.14 manager) and bun.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.local/bin:/root/.bun/bin:${PATH}"

WORKDIR /bench
COPY pyproject.toml uv.lock package.json bun.lock ./
RUN uv sync --frozen && bun install --frozen-lockfile

# Playwright Chromium (for the planned browser renderers) — best-effort; skip on failure.
RUN uv run python -m playwright install --with-deps chromium || true

COPY . .
RUN uv sync --frozen  # re-sync now that the package source is present

ENTRYPOINT ["uv", "run", "bench"]
CMD ["run", "--clean-runs"]
