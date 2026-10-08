# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Install the requested/latest official release, verified against its checksum ledger."""
import hashlib
import io
import json
import platform
import sys
import tarfile
import urllib.request
from pathlib import Path


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Jubarte-Live-Bench"}),
                                timeout=120) as response:
        return response.read()


requested = sys.argv[1] if len(sys.argv) > 1 else "latest"
root = "https://api.github.com/repos/jandira-tech/jubarte-redlines/releases"
release = json.loads(fetch(f"{root}/latest" if requested == "latest" else f"{root}/tags/v{requested.lstrip('v')}"))
version = release["tag_name"].lstrip("v")
arch = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x86_64"}[platform.machine()]
name = f"jubarte-{version}-linux-{arch}.tar.gz"
assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
checksums = {line.split()[-1].lstrip("*"): line.split()[0]
             for line in fetch(assets["SHA256SUMS.txt"]).decode().splitlines() if line.strip()}
blob = fetch(assets[name])
if hashlib.sha256(blob).hexdigest() != checksums[name]:
    raise RuntimeError("Jubarte release checksum mismatch")
with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
    members = [member for member in archive if Path(member.name).name == "jubarte" and member.isfile()]
    if len(members) != 1:
        raise RuntimeError("release must contain exactly one Jubarte CLI")
    binary = archive.extractfile(members[0]).read()
dest = Path("/usr/local/bin/jubarte")
dest.write_bytes(binary)
dest.chmod(0o755)
Path("/app/tool-versions.json").write_text(json.dumps({"jubarte_release": version,
    "jubarte_archive_sha256": checksums[name], "jubarte_release_commit": release.get("target_commitish"),
    "jubarte_release_url": release["html_url"]}))
print(f"installed checksum-verified Jubarte {version} ({arch})")
