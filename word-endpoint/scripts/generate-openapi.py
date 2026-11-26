"""Generate docs/openapi.json and docs/errors.md from the live routes and PUBLIC error table."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apispec import APISpec
from word_endpoint.responses import PUBLIC

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
JSON_MEDIA = "application/json; charset=utf-8"
DEV_DEPENDENCIES = ("apispec", "openapi-spec-validator")

POST_COMMON_CODES = (
    "query_rejected",
    "not_found",
    "method_not_allowed",
    "unauthorized",
    "length_required",
    "unsupported_encoding",
    "too_large",
    "rate_limited",
    "bad_multipart",
    "too_many_parts",
    "busy",
    "timeout",
    "word_failed",
)
GUARD_CODES = (
    "not_docx",
    "encrypted",
    "unsafe_package",
    "macros",
    "active_content",
    "external_content",
    "password_protected",
    "corrupt",
)
COMPARE_CODES = POST_COMMON_CODES + GUARD_CODES + (
    "unexpected_field",
    "missing_compare_files",
    "compare_failed",
    "no_output",
)
CONVERT_CODES = POST_COMMON_CODES + GUARD_CODES + (
    "unexpected_field",
    "missing_document",
    "convert_failed",
    "no_output",
)

ERROR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["error", "code", "request_id"],
    "properties": {
        "error": {"type": "string", "description": "Human-readable failure description."},
        "code": {"type": "string", "enum": sorted(PUBLIC), "description": "Machine-readable status code."},
        "request_id": {"type": "string", "description": "Identifier to correlate with server logs."},
    },
}

LIVE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status"],
    "properties": {"status": {"type": "string", "const": "ok"}},
}

HEALTH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "ready", "workers"],
    "properties": {
        "status": {"type": "string", "description": "Overall HTTP status."},
        "ready": {"type": "boolean", "description": "True when both Word workers are serving."},
        "workers": {
            "type": "object",
            "description": "Per-lane worker state, keyed by lane name.",
            "additionalProperties": {"type": "object"},
        },
    },
}

DOCX_UPLOAD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["original", "revised"],
    "properties": {
        "original": {"type": "string", "format": "binary", "description": "Original .docx (max 20 MB)."},
        "revised": {"type": "string", "format": "binary", "description": "Revised .docx (max 20 MB)."},
    },
}

DOCUMENT_UPLOAD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["document"],
    "properties": {
        "document": {"type": "string", "format": "binary", "description": "Source .docx (max 20 MB)."},
    },
}


def error_response(status: int, codes: tuple[str, ...]) -> dict:
    response = {
        "description": "Error body. code is one of: " + ", ".join(codes) + ".",
        "content": {JSON_MEDIA: {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    if status in (429, 503):
        response["headers"] = {
            "Retry-After": {
                "schema": {"type": "integer", "const": 5},
                "description": "Seconds to wait before retrying.",
            }
        }
    return response


def error_responses(codes: tuple[str, ...]) -> dict[str, dict]:
    by_status: dict[int, list[str]] = {}
    for code in codes:
        status = PUBLIC[code][0]
        by_status.setdefault(status, []).append(code)
    return {str(status): error_response(status, tuple(sorted(by_status[status], key=lambda c: PUBLIC_ORDER[c])))
            for status in sorted(by_status)}


PUBLIC_ORDER = {code: index for index, code in enumerate(PUBLIC)}


def file_response(media: str, filename: str, description: str) -> dict:
    return {
        "description": description,
        "headers": {
            "X-Request-Id": {"schema": {"type": "string"}, "description": "Request identifier echoed by the server."},
            "Content-Disposition": {
                "schema": {"type": "string", "const": f'attachment; filename="{filename}"'},
                "description": "Download filename.",
            },
        },
        "content": {media: {"schema": {"type": "string", "format": "binary"}}},
    }


def upload_body(schema: dict, fields: tuple[str, ...]) -> dict:
    return {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": schema,
                "encoding": {field: {"contentType": DOCX_MEDIA} for field in fields},
            }
        },
    }


def build_spec() -> APISpec:
    spec = APISpec(
        title="Word endpoint",
        version="1.0.0",
        openapi_version="3.1.0",
        info={"description": (
            "Loopback Microsoft Word automation API. Listens on 127.0.0.1 only; callers "
            "authenticate with a bearer token sent in the Authorization header. Query "
            "strings are rejected so the token never reaches tunnel logs."
        )},
        servers=[{"url": "http://127.0.0.1:8787"}],
        security=[{"bearerAuth": []}],
        tags=[
            {"name": "jobs", "description": "Word compare and convert jobs."},
            {"name": "health", "description": "Liveness and readiness probes."},
        ],
    )
    spec.components.security_scheme("bearerAuth", {
        "type": "http",
        "scheme": "bearer",
        "description": "Token created in .env on first start (WORD_API_TOKEN).",
    })
    spec.components.schema("Error", ERROR_SCHEMA)
    spec.components.schema("Live", LIVE_SCHEMA)
    spec.components.schema("Health", HEALTH_SCHEMA)

    spec.path(path="/live", operations={
        "get": {
            "tags": ["health"],
            "summary": "HTTP liveness probe.",
            "description": "Returns 200 whenever the HTTP listener answers.",
            "security": [],
            "responses": {"200": {
                "description": "Service is alive.",
                "content": {JSON_MEDIA: {"schema": {"$ref": "#/components/schemas/Live"}}},
            }},
        },
    })
    spec.path(path="/health", operations={
        "get": {
            "tags": ["health"],
            "summary": "HTTP liveness with worker detail.",
            "description": "Preserved for existing supervisors; includes a ready flag and both worker states.",
            "security": [],
            "responses": {"200": {
                "description": "Service state.",
                "content": {JSON_MEDIA: {"schema": {"$ref": "#/components/schemas/Health"}}},
            }},
        },
    })
    spec.path(path="/ready", operations={
        "get": {
            "tags": ["health"],
            "summary": "Word readiness probe.",
            "description": "Returns 503 during worker startup or recovery.",
            "security": [],
            "responses": {
                "200": {
                    "description": "Both Word workers are serving.",
                    "content": {JSON_MEDIA: {"schema": {"$ref": "#/components/schemas/Health"}}},
                },
                "503": {
                    "description": "Workers are starting or recovering.",
                    "content": {JSON_MEDIA: {"schema": {"$ref": "#/components/schemas/Health"}}},
                },
            },
        },
    })
    spec.path(path="/v1/compare", operations={
        "post": {
            "tags": ["jobs"],
            "summary": "Compare two .docx files.",
            "description": "Returns a blackline .docx with tracked changes. Exactly two form fields are accepted.",
            "requestBody": upload_body(DOCX_UPLOAD_SCHEMA, ("original", "revised")),
            "responses": {
                "200": file_response(
                    DOCX_MEDIA,
                    "comparison.docx",
                    "Comparison document with tracked changes.",
                ),
                **error_responses(COMPARE_CODES),
            },
        },
    })
    spec.path(path="/v1/compare-pdf", operations={
        "post": {
            "tags": ["jobs"],
            "summary": "Compare two .docx files and export the markup as PDF.",
            "description": "Word exports its live comparison result directly; markup is preserved in the PDF.",
            "requestBody": upload_body(DOCX_UPLOAD_SCHEMA, ("original", "revised")),
            "responses": {
                "200": file_response(
                    "application/pdf",
                    "comparison.pdf",
                    "Comparison PDF including tracked-change and comment markup.",
                ),
                **error_responses(COMPARE_CODES),
            },
        },
    })
    spec.path(path="/v1/convert", operations={
        "post": {
            "tags": ["jobs"],
            "summary": "Convert one .docx file to PDF.",
            "description": "PDF export omits document properties and always includes markup when present.",
            "requestBody": upload_body(DOCUMENT_UPLOAD_SCHEMA, ("document",)),
            "responses": {
                "200": file_response(
                    "application/pdf",
                    "document.pdf",
                    "PDF rendered from the uploaded document.",
                ),
                **error_responses(CONVERT_CODES),
            },
        },
    })
    return spec


def write_errors_markdown(path: Path) -> None:
    lines = [
        "# Error messages",
        "",
        "Every failure is JSON with `error` (message), `code` and `request_id`.",
        "`code` never leaks internal details; unknown failures surface as `word_failed`.",
        "`busy` and `rate_limited` also carry `Retry-After: 5`.",
        "",
        "| Code | HTTP | Message |",
        "| --- | --- | --- |",
    ]
    for code, (status, message) in PUBLIC.items():
        lines.append(f"| `{code}` | {status} | {message} |")
    lines += [
        "",
        "Generated from `word_endpoint/responses.py` by `scripts/generate-openapi.py`:",
        "",
        "```sh",
        "uv run scripts/generate-openapi.py",
        "```",
        "",
        "Dependencies: " + ", ".join(DEV_DEPENDENCIES) + " (dev dependencies).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    try:
        from openapi_spec_validator import validate
    except ImportError:
        from openapi_spec_validator import validate_spec as validate

    spec = build_spec()
    document = spec.to_dict()
    validate(document)

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    json_path = docs / "openapi.json"
    json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    write_errors_markdown(docs / "errors.md")

    print(f"validated OpenAPI {document['openapi']} with {len(document['paths'])} paths "
          f"and {len(document['components']['schemas'])} schemas")
    print(f"wrote {json_path.relative_to(ROOT)} and docs/errors.md")


if __name__ == "__main__":
    main()
