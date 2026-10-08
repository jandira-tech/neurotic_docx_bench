# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
FROM rust:slim-trixie AS docxide
ARG DOCXIDE_VERSION=0.18.3
RUN apt-get update && apt-get install -y --no-install-recommends pkg-config libfontconfig1-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*
RUN cargo install docxide-pdf --version "${DOCXIDE_VERSION}" --locked

FROM node:24-bookworm-slim AS superdoc
ARG SUPERDOC_COMMIT=06d9fcfbb80b28cee0c7cd71cda720297712ace5
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/yuch85/superdoc-redlines.git /opt/superdoc-redlines \
    && cd /opt/superdoc-redlines && git checkout "${SUPERDOC_COMMIT}" && npm ci --ignore-scripts \
    && git rev-parse HEAD > /opt/superdoc-redlines/COMMIT && rm -rf .git

FROM mcr.microsoft.com/dotnet/runtime:10.0 AS dotnet

FROM python:3.14-slim-trixie
ARG JUBARTE_VERSION=latest
ENV PYTHONUNBUFFERED=1 DATA_DIR=/data BENCH_DEVICE=numpy \
    DOTNET_ROOT=/usr/share/dotnet PATH=/usr/share/dotnet:/usr/local/bin:/usr/bin:/bin \
    HOME=/tmp/livebench-home FONTCONFIG_PATH=/etc/fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation2 fonts-dejavu-core fonts-noto-core \
    fonts-crosextra-carlito fonts-crosextra-caladea fontconfig libicu76 libfontconfig1 libfreetype6 \
    libstdc++6 libssl3t64 ca-certificates libseccomp2 \
    && rm -rf /var/lib/apt/lists/* && fc-cache -f
COPY --from=docxide /usr/local/cargo/bin/docxide-pdf /usr/local/bin/docxide-pdf
COPY --from=superdoc /usr/local/bin/node /usr/local/bin/node
COPY --from=superdoc /opt/superdoc-redlines /opt/superdoc-redlines
COPY --from=dotnet /usr/share/dotnet /usr/share/dotnet
WORKDIR /app
COPY live-bench/install_soffice.py /app/live-bench/install_soffice.py
RUN apt-get update && python live-bench/install_soffice.py && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 libx11-xcb1 libxinerama1 libxext6 libnss3 libnspr4 libdbus-1-3 \
    libcairo2 libglib2.0-0t64 libcups2t64 libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/* && soffice --headless --version
COPY pyproject.toml README.md LICENSE /app/
COPY src/neurotic_docx_bench /app/src/neurotic_docx_bench
COPY live-bench/backend /app/live-bench/backend
COPY live-bench/install_jubarte.py /app/live-bench/install_jubarte.py
RUN pip install --no-cache-dir /app /app/live-bench/backend \
    && python live-bench/install_jubarte.py "${JUBARTE_VERSION}" \
    && python -c 'import json,pathlib,subprocess; p=pathlib.Path("/app/tool-versions.json"); v=json.loads(p.read_text()); v.update(soffice_install=json.loads(pathlib.Path("/app/soffice-install.json").read_text()), docxide="0.18.3", superdoc_redlines_commit=pathlib.Path("/opt/superdoc-redlines/COMMIT").read_text().strip(), dotnet=subprocess.check_output(["dotnet","--list-runtimes"],text=True).strip()); p.write_text(json.dumps(v))' \
    && jubarte --help >/dev/null && docxide-pdf --help >/dev/null && dotnet --list-runtimes
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=3 \
    CMD ["jubarte-live-bench", "--health"]
CMD ["jubarte-live-bench"]
