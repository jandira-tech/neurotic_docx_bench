# Error messages

Every failure is JSON with `error` (message), `code` and `request_id`.
`code` never leaks internal details; unknown failures surface as `word_failed`.
`busy` and `rate_limited` also carry `Retry-After: 5`.

| Code | HTTP | Message |
| --- | --- | --- |
| `unauthorized` | 401 | Unauthorized. |
| `not_found` | 404 | Not found. |
| `method_not_allowed` | 405 | Method not allowed. |
| `query_rejected` | 400 | Query strings are not accepted. Send the token in the Authorization header. |
| `length_required` | 411 | Content-Length is required. |
| `unsupported_encoding` | 415 | Compressed or chunked uploads are not accepted. |
| `too_large` | 413 | The upload is too large. |
| `rate_limited` | 429 | Too many requests. |
| `bad_multipart` | 400 | The upload form is invalid. Send multipart form data. |
| `too_many_parts` | 400 | Too many form fields. |
| `unexpected_field` | 400 | Send only the files this endpoint accepts. |
| `missing_compare_files` | 400 | Attach both 'original' and 'revised' .docx files. |
| `missing_document` | 400 | Attach the .docx file in the 'document' field. |
| `not_docx` | 400 | Upload a .docx file. Other formats, including macro-enabled documents, are rejected. |
| `encrypted` | 400 | Encrypted documents are not accepted. |
| `macros` | 400 | Documents that contain macros are not accepted. |
| `active_content` | 400 | Documents that contain active content, such as DDE fields or ActiveX, are not accepted. |
| `external_content` | 400 | Documents that link to external files, templates, or data are not accepted. |
| `unsafe_package` | 400 | The document package failed safety checks. |
| `password_protected` | 400 | Password-protected documents are not accepted. |
| `corrupt` | 400 | Word could not open the document. |
| `compare_failed` | 500 | Word could not compare these documents. |
| `convert_failed` | 500 | Word could not convert this document. |
| `no_output` | 500 | Word did not produce a file. |
| `word_failed` | 500 | Word failed while processing the document. |
| `busy` | 503 | The converter is busy. Try again shortly. |
| `timeout` | 504 | The document took too long to process. |

Generated from `word_endpoint/responses.py` by `scripts/generate-openapi.py`:

```sh
uv run scripts/generate-openapi.py
```

Dependencies: apispec, openapi-spec-validator (dev dependencies).
