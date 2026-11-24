"""Reject documents that could make Word run code or open something outside the file.

The checks are structural: zip limits, package layout, macros, DDE-style fields,
and relationships that point outside the package. XML is parsed only after
rejecting DTDs and entity declarations; package expansion is strictly bounded.
"""

from __future__ import annotations

import io
import base64
import binascii
import posixpath
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

from purexml import (AttributesExceeded, DepthExceeded, DTDForbidden,
                     EntitiesForbidden, ExternalReferenceForbidden, Limits)
from purexml import ElementTree as SafeET

from word_endpoint.paths import WORK_ROOT

MAX_DOCX_BYTES = 20 * 1024 * 1024
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_XML_BYTES = 32 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_XML_DEPTH = 1000
MAX_XML_ATTRIBUTES = 256
# Raw XML bytes are already capped before decoding; avoid re-encoding text
# to apply a second byte limit that could reject accepted UTF-16 documents.
_XML_LIMITS = Limits(max_depth=MAX_XML_DEPTH, max_attributes=MAX_XML_ATTRIBUTES)

_BANNED_NAME_PARTS = ("vbaproject", "vbadata", "activex", "macroenabled")
_DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".js", ".jse", ".vbs", ".vbe", ".ps1", ".bat", ".cmd",
    ".msi", ".scr", ".hta", ".com", ".lnk", ".jar", ".wsf", ".wsh", ".cpl",
    ".docm", ".dotm", ".xlsm", ".xlsb", ".pptm", ".xlam", ".ppam", ".rtf",
    ".html", ".htm", ".mht", ".mhtml",
}
_FORBIDDEN_FIELD = re.compile(
    r"(?i)\b(DDEAUTO|DDE|INCLUDETEXT|INCLUDEPICTURE|INCLUDEHTML|MACROBUTTON|DATABASE|IMPORT|LINK|RD)\b"
)
_ATTR = re.compile(r"""([A-Za-z0-9:]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_ENTITY = re.compile(r"&([^;]{1,16});")
_TAG_ATTRIBUTES = r'''(?:[^'">]|"[^"]*"|'[^']*')*'''
_TEMPLATE_TAG = re.compile(
    rf"<(?:[\w.-]+:)?(?:attachedTemplate|linkStyles)\b{_TAG_ATTRIBUTES}/>"
    rf"|<(?:[\w.-]+:)?(?:attachedTemplate|linkStyles)\b{_TAG_ATTRIBUTES}>.*?</(?:[\w.-]+:)?(?:attachedTemplate|linkStyles)>",
    re.I | re.S,
)
_TEMPLATE_REL = re.compile(
    rf"<(?:[\w.-]+:)?Relationship\b{_TAG_ATTRIBUTES}/>"
    rf"|<(?:[\w.-]+:)?Relationship\b{_TAG_ATTRIBUTES}>.*?</(?:[\w.-]+:)?Relationship>",
    re.I | re.S,
)
_NAMED = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


class GuardError(Exception):
    def __init__(self, code: str, reason: str | None = None, part: str | None = None):
        super().__init__(code)
        self.code = code
        self.reason = reason or code
        self.part = part


class PreparedDocx(bytes):
    """An internal marker for bytes already validated and detached from templates."""


def validate_docx(data: bytes, *, allow_attached_template: bool = False,
                  max_bytes: int = MAX_DOCX_BYTES) -> set[str]:
    if not isinstance(data, (bytes, bytearray)):
        raise GuardError("not_docx")
    blob = bytes(data)
    if len(blob) > max_bytes:
        raise GuardError("too_large", "compressed_size")
    if len(blob) < 64 or not blob.startswith(b"PK\x03\x04"):
        raise GuardError("not_docx")
    try:
        return _validate(blob, allow_attached_template)
    except GuardError:
        raise
    except RuntimeError as exc:
        message = str(exc).lower()
        if "password" in message or "encrypted" in message:
            raise GuardError("encrypted") from exc
        raise GuardError("unsafe_package") from exc
    except (zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error, ValueError, ET.ParseError) as exc:
        raise GuardError("unsafe_package", "invalid_zip_or_xml") from exc


def prepare_docx(data: bytes) -> bytes:
    """Validate uploads and revalidate template-detached copies before Word opens them."""
    template_parts = validate_docx(data, allow_attached_template=True)
    if not template_parts:
        return PreparedDocx(data)
    cleaned = _strip_template_stamp(data, scrub=False, template_parts=template_parts)
    # Text-based stripping can expose markup hidden in XML comments.
    validate_docx(cleaned)
    return PreparedDocx(cleaned)


def sanitize_output_docx(data: bytes) -> bytes:
    """Drop the local template path Word stamps onto a file it saves."""
    template_parts = validate_docx(data, allow_attached_template=True, max_bytes=80 * 1024 * 1024)
    cleaned = _strip_template_stamp(data, template_parts=template_parts)
    validate_docx(cleaned, max_bytes=80 * 1024 * 1024)
    return cleaned


def _validate(data: bytes, allow_attached_template: bool) -> set[str]:
    template_parts = set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        _check_infos(infos)
        by_name = {info.filename.lower(): info for info in infos}
        for required in ("[content_types].xml", "_rels/.rels"):
            if required not in by_name:
                raise GuardError("not_docx")
        content_types = _read_text(archive, by_name["[content_types].xml"])
        defaults, overrides = _check_content_types(content_types)
        main_part = _check_package_root(_read_text(archive, by_name["_rels/.rels"]))
        main_mime = overrides.get(main_part, defaults.get(Path(main_part).suffix.lstrip("."), ""))
        if main_part not in by_name or main_mime != "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml":
            raise GuardError("not_docx", "missing_document_content_type")
        members = set(by_name)
        for info in infos:
            name = info.filename.lower()
            mime = overrides.get(name, defaults.get(Path(name).suffix.lstrip("."), ""))
            svg = name.endswith(".svg") or mime == "image/svg+xml"
            xml = name.endswith((".xml", ".rels", ".vml")) or mime.endswith("+xml") or mime in {"application/xml", "text/xml"} or "vmldrawing" in mime
            if xml or svg:
                try:
                    if svg:
                        _scan_svg(_read_text(archive, info))
                        continue
                    has_template = _scan_part(
                        _read_text(archive, info),
                        allow_attached_template=allow_attached_template,
                        part_name=info.filename, members=members,
                        word_content=name.startswith("word/") or "wordprocessingml" in mime or "vmldrawing" in mime,
                    )
                    if has_template:
                        template_parts.add(info.filename)
                except GuardError as exc:
                    exc.part = info.filename
                    raise
    return template_parts


def _check_infos(infos: list[zipfile.ZipInfo]) -> None:
    if len(infos) > MAX_ENTRIES:
        raise GuardError("unsafe_package", "entry_count")
    seen: set[str] = set()
    total = 0
    for info in infos:
        name = info.filename
        _check_entry_name(name)
        key = name.lower()
        if key in seen:
            raise GuardError("unsafe_package", "duplicate_member")
        seen.add(key)
        if info.flag_bits & 0x1 or info.flag_bits & 0x40:
            raise GuardError("encrypted")
        if info.file_size < 0 or info.compress_size < 0:
            raise GuardError("unsafe_package")
        if info.file_size > MAX_MEMBER_BYTES:
            raise GuardError("too_large", "member_size", name)
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise GuardError("too_large", "expanded_package_size")
        # Compression ratios reject legitimate repetitive Word XML. Absolute
        # expanded/member limits and capped reads bound decompression instead.
        base = key.split("/")[-1]
        if base in {"encryptioninfo", "encryptedpackage"}:
            raise GuardError("encrypted")


def _check_entry_name(name: str) -> None:
    if not name or len(name) > 180 or name.startswith(("/", "\\")) or "\\" in name:
        raise GuardError("unsafe_package")
    if any(ord(character) < 32 for character in name):
        raise GuardError("unsafe_package")
    # Word writes directory entries such as "word/". Those are not files.
    if name.endswith("/"):
        name = name[:-1]
    if not name:
        raise GuardError("unsafe_package")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise GuardError("unsafe_package")
    lowered = name.lower()
    if any(fragment in lowered for fragment in _BANNED_NAME_PARTS):
        if "activex" in lowered:
            raise GuardError("active_content")
        raise GuardError("macros")
    suffix = Path(lowered).suffix
    if suffix in _DANGEROUS_EXTENSIONS:
        raise GuardError("active_content")


def _check_content_types(text: str) -> tuple[dict[str, str], dict[str, str]]:
    root = _parse_xml(text)
    defaults, overrides = {}, {}
    for node in root:
        mime = node.get("ContentType", "").lower()
        if any(marker in mime for marker in ("macroenabled", "vbaproject", "vbadata")):
            raise GuardError("macros", "macro_content_type")
        if "activex" in mime:
            raise GuardError("active_content", "activex_content_type")
        local = node.tag.rsplit("}", 1)[-1]
        if local == "Default":
            defaults[node.get("Extension", "").lower()] = mime
        elif local == "Override":
            part = urllib.parse.unquote(node.get("PartName", "")).lstrip("/").lower()
            overrides[part] = mime
    return defaults, overrides


def _check_package_root(text: str) -> str:
    office = [
        item
        for item in _relationships(_parse_xml(text))
        if item.get("type", "").lower().endswith("/officedocument")
    ]
    if len(office) != 1:
        raise GuardError("not_docx")
    target = office[0].get("target", "")
    if _is_external(office[0].get("targetmode", "").lower(), target):
        raise GuardError("external_content")
    target = urllib.parse.unquote(target)
    return posixpath.normpath(target.lstrip("/")).lower()


def _scan_part(text: str, *, allow_attached_template: bool,
               part_name: str = "word/document.xml", members: set[str] | None = None,
               word_content: bool = True) -> bool:
    try:
        root = _parse_xml(text)
    except ET.ParseError as exc:
        raise GuardError("unsafe_package", "invalid_xml") from exc
    has_template = False
    for node in root.iter():
        if not _word_element(node):
            continue
        local = node.tag.rsplit("}", 1)[-1]
        if local in {"entryMacro", "exitMacro"}:
            raise GuardError("macros", "macro_form_field")
        if local in {"subDoc", "mailMerge", "frameset", "control", "ocx"}:
            raise GuardError("active_content", "active_word_element")
        if local == "attachedTemplate":
            if not allow_attached_template:
                raise GuardError("external_content", "attached_template")
            has_template = True
        elif local == "linkStyles" and allow_attached_template:
            # Keep the uploaded styles; detaching a template must not cause
            # Word to import this server's default Normal.dotm styles.
            has_template = True
    if word_content:
        _scan_fields(root)
    if part_name.lower().endswith(".rels"):
        for item in _relationships(root):
            _check_relationship(item, allow_attached_template, part_name, members)
            has_template = has_template or item.get("type", "").lower().endswith("/attachedtemplate")
    return has_template


def _word_element(node: ET.Element) -> bool:
    return node.tag.startswith(("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}",
                                "{http://purl.oclc.org/ooxml/wordprocessingml/main}"))


def _scan_fields(root: ET.Element) -> None:
    # Inspect the command, not quoted field arguments (e.g. a TOC bookmark
    # named LINK). Join split instruction runs only inside their own field.
    stack: list[list[str]] = []
    orphan: list[str] = []
    for node in root.iter():
        if not _word_element(node):
            continue
        local = node.tag.rsplit("}", 1)[-1]
        if local == "p":
            _check_field_command("".join(orphan))
            orphan = []
        elif local == "fldChar":
            kind = next((v for k, v in node.attrib.items() if k.rsplit("}", 1)[-1] == "fldCharType"), "")
            if kind == "begin":
                stack.append([])
            elif kind in {"separate", "end"} and stack:
                _check_field_command("".join(stack[-1]))
                if kind == "end":
                    stack.pop()
        elif local == "instrText":
            (stack[-1] if stack else orphan).append(node.text or "")
        elif local == "fldSimple":
            for key, value in node.attrib.items():
                if key.rsplit("}", 1)[-1] == "instr":
                    _check_field_command(value)
    for field in stack + [orphan]:
        _check_field_command("".join(field))


def _check_field_command(text: str) -> None:
    if _FORBIDDEN_FIELD.match(text.lstrip()):
        raise GuardError("active_content", "forbidden_field_command")


def _scan_svg(text: str) -> None:
    root = _parse_xml(text, code="active_content", reason="svg_dtd")
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise GuardError("active_content", "invalid_svg")
    for node in root.iter():
        local = node.tag.rsplit("}", 1)[-1].lower()
        if local in {"script", "foreignobject", "iframe", "object", "embed", "animate", "set", "animatetransform", "animatemotion"}:
            raise GuardError("active_content", "active_svg")
        for key, value in node.attrib.items():
            attr = key.rsplit("}", 1)[-1].lower()
            if attr.startswith("on"):
                raise GuardError("active_content", "svg_event_handler")
            if attr in {"href", "src"} and not value.startswith("#") and not _embedded_raster(value):
                raise GuardError("external_content", "svg_external_reference")
        # CSS escapes and imports are unnecessary for static Office drawings.
        styles = [node.text or ""] if local == "style" else []
        styles.extend(v for k, v in node.attrib.items() if k.lower() == "style")
        styles.extend(v for v in node.attrib.values() if "url(" in v.lower())
        for style in styles:
            urls = re.findall(r"url\((.*?)\)", style, re.I)
            if "\\" in style or "@" in style or any(not url.strip().strip("\"'").startswith("#") for url in urls):
                raise GuardError("active_content", "svg_external_style")


def _embedded_raster(value: str) -> bool:
    """Accept static raster data URIs, never nested SVG/HTML or another URI."""
    header, separator, encoded = value.partition(",")
    signatures = {
        "data:image/png;base64": (b"\x89PNG\r\n\x1a\n",),
        "data:image/jpeg;base64": (b"\xff\xd8\xff",),
        "data:image/gif;base64": (b"GIF87a", b"GIF89a"),
    }
    if not separator or header.lower() not in signatures:
        return False
    try:
        data = base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
    except (ValueError, binascii.Error):
        return False
    return data.startswith(signatures[header.lower()])


def _check_relationship(item: dict[str, str], allow_attached_template: bool,
                        part_name: str = "word/_rels/document.xml.rels",
                        members: set[str] | None = None) -> None:
    rel_type = item.get("type", "").lower()
    target = item.get("target", "")
    mode = item.get("targetmode", "").lower()
    if rel_type.endswith("/attachedtemplate"):
        if not allow_attached_template:
            raise GuardError("external_content")
        return
    if _is_external(mode, target):
        if rel_type.endswith("/hyperlink") and _allowed_hyperlink(target):
            return
        raise GuardError("external_content")
    if mode not in {"", "internal"}:
        raise GuardError("unsafe_package", "invalid_target_mode")
    # OPC relationship targets are relative to the source PART, not its
    # _rels directory. ../customXml/item1.xml stays inside the package.
    decoded = urllib.parse.unquote(target)
    parsed = urllib.parse.urlsplit(decoded)
    if parsed.scheme or parsed.netloc or "\\" in decoded or any(ord(c) < 32 for c in decoded):
        raise GuardError("unsafe_package", "invalid_internal_uri")
    if parsed.query:
        raise GuardError("unsafe_package", "internal_uri_query")
    source = "" if part_name.lower() == "_rels/.rels" else posixpath.join(
        posixpath.dirname(posixpath.dirname(part_name)), posixpath.basename(part_name)[:-5]
    )
    base = [] if parsed.path.startswith("/") else posixpath.dirname(source).split("/")
    parts = [p for p in base if p]
    for segment in parsed.path.split("/"):
        if segment in {"", "."}:
            continue
        if segment == "..":
            if not parts:
                raise GuardError("unsafe_package", "relationship_escapes_package")
            parts.pop()
        else:
            parts.append(segment)
    resolved = "/".join(parts) if parsed.path else source
    if members is not None and resolved.lower() not in members:
        raise GuardError("unsafe_package", "missing_relationship_target")


def _parse_xml(text: str, *, code: str = "unsafe_package",
               reason: str = "xml_dtd_or_entity") -> ET.Element:
    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise GuardError(code, reason)
    try:
        return SafeET.fromstring(text, forbid_dtd=True, forbid_entities=True,
                                 forbid_external=True, limits=_XML_LIMITS)
    except (DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden) as exc:
        raise GuardError(code, reason) from exc
    except DepthExceeded as exc:
        raise GuardError("unsafe_package", "xml_depth") from exc
    except AttributesExceeded as exc:
        raise GuardError("unsafe_package", "xml_attributes") from exc


def _relationships(root: ET.Element) -> list[dict[str, str]]:
    return [{key.lower(): value for key, value in node.attrib.items()}
            for node in root if node.tag.rsplit("}", 1)[-1] == "Relationship"]


def decode_entities(value: str, *, allow_markup: bool) -> str:
    if value.count("&") > 10000:
        raise GuardError("unsafe_package")
    # XML decodes entities once. Repeated decoding rejects ordinary URLs
    # containing literal &lt; and changes the actual meaning of field text.
    current = _ENTITY.sub(lambda match: _decode_entity(match.group(1)), value)
    if not allow_markup and ("<" in current or ">" in current):
        raise GuardError("unsafe_package")
    return current


def _decode_entity(token: str) -> str:
    if token[:2].lower() == "#x":
        digits = token[2:]
        base = 16
    elif token.startswith("#"):
        digits = token[1:]
        base = 10
    else:
        if token not in _NAMED:
            raise GuardError("unsafe_package")
        return _NAMED[token]
    if not digits or len(digits) > 6:
        raise GuardError("unsafe_package")
    try:
        code = int(digits, base)
    except ValueError as exc:
        raise GuardError("unsafe_package") from exc
    if code < 0 or code > 0x10FFFF:
        raise GuardError("unsafe_package")
    return chr(code)


def _is_external(mode: str, target: str) -> bool:
    if mode == "external":
        return True
    value = target.strip().lower()
    if "://" in value or value.startswith(("file:", "ftp:", "mailto:", "//", "\\\\")):
        return True
    return len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in "\\/"


def _allowed_hyperlink(target: str) -> bool:
    value = target.strip()
    if not value or any(ord(character) < 32 for character in value):
        return False
    return value.lower().startswith(("https://", "http://", "mailto:"))


def _read_text(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    blob = _read_capped(archive, info, MAX_XML_BYTES)
    try:
        return blob.decode(_xml_encoding(blob))
    except UnicodeDecodeError as exc:
        raise GuardError("unsafe_package") from exc


def _xml_encoding(blob: bytes) -> str:
    if blob.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if blob.startswith(b"<\x00"):
        return "utf-16-le"
    if blob.startswith(b"\x00<"):
        return "utf-16-be"
    return "utf-8-sig"


def _read_capped(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    if info.file_size > limit:
        raise GuardError("too_large")
    with archive.open(info, "r") as handle:
        blob = handle.read(limit + 1)
    if len(blob) > limit:
        raise GuardError("too_large")
    return blob


def _path_needles() -> list[str]:
    needles: list[str] = []
    for root in (WORK_ROOT, Path.home()):
        text = str(root)
        if len(text) >= 8:
            needles.append(text)
            needles.append(text.replace("\\", "/"))
    return needles


def _scrub_paths(text: str) -> str:
    for needle in _path_needles():
        text = re.sub(re.escape(needle), "", text, flags=re.I)
    return text


def _strip_markup(text: str) -> str:
    text = _TEMPLATE_TAG.sub("", text)

    def drop_template(match: re.Match[str]) -> str:
        for attr in _ATTR.finditer(match.group(0)):
            if attr.group(1).lower() == "type":
                value = attr.group(2) if attr.group(2) is not None else attr.group(3)
                if decode_entities(value, allow_markup=True).lower().endswith("/attachedtemplate"):
                    return ""
        return match.group(0)

    return _TEMPLATE_REL.sub(drop_template, text)


def _strip_template_stamp(data: bytes, *, scrub: bool = True,
                          template_parts: set[str] | None = None) -> bytes:
    template_parts = template_parts or set()
    updates: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        for info in source.infolist():
            _check_entry_name(info.filename)
            lowered = info.filename.lower()
            candidate = info.filename in template_parts
            candidate = candidate or (scrub and lowered in {"word/settings.xml", "word/_rels/settings.xml.rels"})
            if candidate or (scrub and lowered.startswith("docprops/") and lowered.endswith(".xml")):
                blob = _read_capped(source, info, MAX_XML_BYTES)
                encoding = _xml_encoding(blob)
                text = blob.decode(encoding)
                original = text
                if info.filename in template_parts:
                    text = _strip_markup(text)
                if scrub and (lowered.startswith("docprops/") or lowered in {
                    "word/settings.xml",
                    "word/_rels/settings.xml.rels",
                }):
                    text = _scrub_paths(text)
                if text != original:
                    updates[info.filename] = text.encode(encoding if encoding != "utf-8-sig" else "utf-8")
        if not updates:
            return data
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as dest:
            for info in source.infolist():
                blob = updates.get(info.filename)
                if blob is None:
                    blob = _read_capped(source, info, MAX_MEMBER_BYTES)
                dest.writestr(info.filename, blob)
        return output.getvalue()
