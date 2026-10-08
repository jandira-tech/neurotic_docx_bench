# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Install the newest official stable LibreOffice DEBs, verifying its SHA256."""
import hashlib
import json
import platform
import re
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = "https://download.documentfoundation.org/libreoffice/stable/"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Jubarte-Live-Bench-Builder/1"})
    return urllib.request.urlopen(request, timeout=120)


def install():
    with fetch(ROOT) as response:
        versions = re.findall(r'href="(\d+\.\d+\.\d+)/"', response.read().decode())
    version = max(versions, key=lambda value: tuple(map(int, value.split("."))))
    arch = "aarch64" if platform.machine() == "aarch64" else "x86_64"
    label = "aarch64" if arch == "aarch64" else "x86-64"
    name = f"LibreOffice_{version}_Linux_{label}_deb.tar.gz"
    url = f"{ROOT}{version}/deb/{arch}/{name}"
    with fetch(url + ".sha256") as response:
        expected = response.read().decode().split()[0]
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise RuntimeError("official LibreOffice checksum unavailable")
    with tempfile.TemporaryDirectory(prefix="lo-install-") as folder:
        root = Path(folder)
        archive = root / name
        digest = hashlib.sha256()
        with fetch(url) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError("LibreOffice download checksum mismatch")
        with tarfile.open(archive) as package:
            package.extractall(root, filter="data")
        debs = sorted(map(str, root.glob("*/DEBS/*.deb")))
        subprocess.run(["apt-get", "install", "-y", "--no-install-recommends", *debs], check=True)
    target = next(Path("/opt").glob("libreoffice*/program/soffice"))
    Path("/usr/local/bin/soffice").symlink_to(target)
    Path("/app/soffice-install.json").write_text(json.dumps({
        "version": version, "archive_sha256": expected, "download_url": url,
    }))
    print(f"Installed checksum-verified LibreOffice {version} ({arch})")


if __name__ == "__main__":
    install()
