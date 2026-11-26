"""Client-facing status codes. Unknown codes never leave the process."""

PUBLIC: dict[str, tuple[int, str]] = {
    "unauthorized": (401, "Unauthorized."),
    "not_found": (404, "Not found."),
    "method_not_allowed": (405, "Method not allowed."),
    "bad_request": (400, "The request line could not be read."),
    "uri_too_long": (414, "The request line is too long."),
    "headers_too_large": (431, "The request headers are too large."),
    "not_implemented": (501, "This method is not supported."),
    "http_version": (505, "Only HTTP/1.0 and HTTP/1.1 are supported."),
    "query_rejected": (
        400,
        "Query strings are not accepted. Send the token in the Authorization header.",
    ),
    "length_required": (411, "Content-Length is required."),
    "unsupported_encoding": (415, "Compressed or chunked uploads are not accepted."),
    "too_large": (413, "The upload is too large."),
    "rate_limited": (429, "Too many requests."),
    "bad_multipart": (400, "The upload form is invalid. Send multipart form data."),
    "too_many_parts": (400, "Too many form fields."),
    "unexpected_field": (400, "Send only the files this endpoint accepts."),
    "missing_compare_files": (
        400,
        "Attach both 'original' and 'revised' .docx files.",
    ),
    "missing_document": (400, "Attach the .docx file in the 'document' field."),
    "not_docx": (
        400,
        "Upload a .docx file. Other formats, including macro-enabled documents, are rejected.",
    ),
    "encrypted": (400, "Encrypted documents are not accepted."),
    "macros": (400, "Documents that contain macros are not accepted."),
    "active_content": (
        400,
        "Documents that contain active content, such as DDE fields or ActiveX, are not accepted.",
    ),
    "external_content": (
        400,
        "Documents that link to external files, templates, or data are not accepted.",
    ),
    "unsafe_package": (400, "The document package failed safety checks."),
    "password_protected": (400, "Password-protected documents are not accepted."),
    "corrupt": (400, "Word could not open the document."),
    "compare_failed": (500, "Word could not compare these documents."),
    "convert_failed": (500, "Word could not convert this document."),
    "no_output": (500, "Word did not produce a file."),
    "word_failed": (500, "Word failed while processing the document."),
    "busy": (503, "The converter is busy. Try again shortly."),
    "timeout": (504, "The document took too long to process."),
}


def public_code(code: str) -> str:
    if code in PUBLIC:
        return code
    return "word_failed"
