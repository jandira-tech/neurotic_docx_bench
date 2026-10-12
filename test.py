import http.client
import json
import os
import sys
import uuid
from pathlib import Path


def load_env(path):
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env(Path(__file__).resolve().parent / ".env")

# This value is a GroupDocs Cloud JWT. api.groupdocs.cloud accepts it as a
# bearer. The RapidAPI host rejects it.
TOKEN = os.environ["RAPID_API_TOKEN"].removeprefix("Bearer ")
HOST = "api.groupdocs.cloud"
SOURCE = Path(sys.argv[1])
TARGET = Path(sys.argv[2])


def call(method, path, body=None, headers=None):
    conn = http.client.HTTPSConnection(HOST)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    text = data.decode("utf-8", "replace").replace(TOKEN, "[redacted]")
    print(method, path, response.status, flush=True)
    print(text[:1500], flush=True)
    return response.status, data


def upload(remote, path):
    boundary = "----groupdocs" + uuid.uuid4().hex
    content = path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="File"; filename="{path.name}"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n"
        "\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    status, _data = call(
        "PUT",
        f"/v2.0/comparison/storage/file/{remote}",
        body,
        {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    if status != 200:
        raise SystemExit(status)


run = "test-" + uuid.uuid4().hex[:8]
upload(f"{run}/source.docx", SOURCE)
upload(f"{run}/target.docx", TARGET)

payload = {
    "SourceFile": {"FilePath": f"{run}/source.docx"},
    "TargetFiles": [{"FilePath": f"{run}/target.docx"}],
    "OutputPath": f"{run}/result.docx",
    "Settings": {
        "CloneMetadata": "Default",
        "DetailsLevel": "Low",
        "PaperSize": "Default",
        "PasswordSaveOption": "None",
        "WordsSeparatorChars": [],
    },
}
status, data = call(
    "POST",
    "/v2.0/comparison/comparisons",
    json.dumps(payload),
    {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
)
if status != 200:
    raise SystemExit(status)

status, result = call(
    "GET",
    f"/v2.0/comparison/storage/file/{run}/result.docx",
    headers={"Authorization": f"Bearer {TOKEN}"},
)
if status != 200:
    raise SystemExit(status)
out = Path("/tmp") / f"{run}-result.docx"
out.write_bytes(result)
print("wrote", out, "bytes", len(result), flush=True)
