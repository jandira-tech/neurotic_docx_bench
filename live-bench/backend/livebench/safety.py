# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded OOXML preflight before any parser, local tool or Word request."""

from io import BytesIO
from zipfile import BadZipFile, ZipFile

from lxml import etree

from livebench.models import MAX_FILE_BYTES

MAX_ENTRIES = 4096
MAX_EXPANDED = 128 * 1024 * 1024
MAX_PART = MAX_FILE_BYTES
MAX_XML = 8 * 1024 * 1024
MAX_DEPTH = 96
MAX_ATTRIBUTES = 256


class UnsafeDocument(ValueError):
    pass


def inspect_xml(data: bytes):
    if len(data) > MAX_XML:
        raise UnsafeDocument("XML expansion exceeds safe size limit")
    normalized = data.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in normalized or b"<!ENTITY" in normalized:
        raise UnsafeDocument("DTD and entity declarations are forbidden")
    depth = 0
    events = etree.iterparse(
        BytesIO(data),
        events=("start", "end"),
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
        recover=False,
    )
    for event, element in events:
        if event == "start":
            depth += 1
            if depth > MAX_DEPTH or len(element.attrib) > MAX_ATTRIBUTES:
                raise UnsafeDocument("XML nesting or attributes exceed safe limits")
        else:
            depth -= 1
            element.clear()


def inspect_docx(blob: bytes) -> dict:
    if len(blob) > MAX_FILE_BYTES:
        raise UnsafeDocument("DOCX exceeds 20 MB file size limit")
    try:
        with ZipFile(BytesIO(blob)) as package:
            entries = package.infolist()
            if not 1 <= len(entries) <= MAX_ENTRIES:
                raise UnsafeDocument("ZIP entry count exceeds safe limits")
            names = [entry.filename for entry in entries]
            if len(set(names)) != len(names):
                raise UnsafeDocument("ZIP contains duplicate entry names")
            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                raise UnsafeDocument("DOCX is missing required package parts")
            # Validate the manifest before using it to classify nonstandard XML part names.
            with package.open("[Content_Types].xml") as stream:
                types_blob = stream.read(MAX_XML + 1)
            inspect_xml(types_blob)
            types = etree.fromstring(types_blob, etree.XMLParser(resolve_entities=False, no_network=True))
            defaults = {
                e.get("Extension", "").lower(): e.get("ContentType", "")
                for e in types
                if etree.QName(e).localname == "Default"
            }
            overrides = {
                e.get("PartName", "").lstrip("/"): e.get("ContentType", "")
                for e in types
                if etree.QName(e).localname == "Override"
            }
            total, xml_parts = 0, 0
            for entry in entries:
                if entry.filename.startswith(("/", "\\")) or ".." in entry.filename.replace("\\", "/").split(
                    "/"
                ):
                    raise UnsafeDocument("ZIP contains unsafe entry names")
                if entry.flag_bits & 1:
                    raise UnsafeDocument("encrypted ZIP parts cannot be checked")
                total += entry.file_size
                if entry.file_size > MAX_PART or total > MAX_EXPANDED:
                    raise UnsafeDocument("ZIP expanded size exceeds safe limits")
                if entry.file_size > 1024 * 1024 and entry.file_size / max(entry.compress_size, 1) > 300:
                    raise UnsafeDocument("ZIP compression ratio exceeds safe limits")
                content_type = overrides.get(
                    entry.filename, defaults.get(entry.filename.rsplit(".", 1)[-1].lower(), "")
                )
                with package.open(entry) as stream:
                    prefix = stream.read(512).replace(b"\x00", b"").lstrip(b"\xef\xbb\xbf\xff\xfe \t\r\n")
                is_xml = (
                    entry.filename.lower().endswith((".xml", ".rels"))
                    or "xml" in content_type.lower()
                    or prefix.startswith(b"<")
                )
                if is_xml:
                    if entry.file_size > MAX_XML:
                        raise UnsafeDocument("XML part exceeds safe size limit")
                    with package.open(entry) as stream:
                        data = stream.read(MAX_XML + 1)
                    inspect_xml(data)
                    xml_parts += 1
            return {
                "status": "safe",
                "zip_entries": len(entries),
                "expanded_bytes": total,
                "xml_parts": xml_parts,
                "policy": "ooxml-bounded-v1",
            }
    except (BadZipFile, etree.XMLSyntaxError, RuntimeError, EOFError) as exc:
        raise UnsafeDocument(f"invalid DOCX package: {type(exc).__name__}") from None
