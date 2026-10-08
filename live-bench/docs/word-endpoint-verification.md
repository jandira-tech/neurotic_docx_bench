<!-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Word endpoint verification — 8 October 2026

The configured HTTPS endpoint is `https://docx.rodrigues.ai`. Authentication uses the
existing `WORD_API_TOKEN` from the private `.env`; its value is not published. The
Word server's `PORT=8787` does not alter this public HTTPS URL.

The live adapter and the existing `predict_redline/methodology/endpoint_word.py`
client agree on the request contract:

| Operation | Method and path | Multipart file fields | Successful artifact |
| --- | --- | --- | --- |
| Conversion | `POST /v1/convert` | `document` | PDF |
| Comparison | `POST /v1/compare` | `original`, `revised` | DOCX with tracked changes |

Controlled inputs containing “Delivery shall occur on Monday.” and its Tuesday
revision returned **200** for conversion (14,874-byte PDF) and comparison
(16,280-byte DOCX). The benchmark's independent functional lens reported
`accept_ok`, `reject_ok`, `accept_strict`, and `reject_strict` all true on the Word
redline, confirming that the original and revised inputs were handled in the right order.

Ordinary python-docx template controls initially returned **400** with
`code=unsafe_package` from both operations. Repackaging with no compression retained
the rejection. Removing only the unused `customXml/` template content and its
relationships made conversion and comparison both return **200** (39,843-byte PDF
and 28,379-byte DOCX). This isolates a package-feature rejection, rather than a wrong
endpoint or wrong multipart field. It does not identify which internal Word API
safety rule made that decision.

The first three real production reviews also recorded these exact error codes when
Word rejected a source or predecessor. Review 2 independently received a successful
Word conversion while comparison was rejected. Corpus packages are never rewritten
to make Word accept them: each tool's rejection stays in the execution trace and the
conversion/redline fallback policy applies independently. These controls are not
published as corpus benchmark scores.
