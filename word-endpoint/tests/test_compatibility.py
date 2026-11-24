"""Real OPC structures previously mistaken for unsafe document packages."""

import io
import unittest
import zipfile
from unittest.mock import patch

from tests.factory import pack, standard_files
from word_endpoint.guard import GuardError, prepare_docx, sanitize_output_docx, validate_docx

REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"


def relationship(files, target, kind="customXml", mode=""):
    files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
        "</Relationships>", f'<Relationship Id="rId99" Type="{REL_TYPE}{kind}" Target="{target}" {mode}/></Relationships>')


class CompatibilityTests(unittest.TestCase):
    def test_xml_nesting_limit_preserves_part_diagnostics(self):
        from word_endpoint.guard import MAX_XML_DEPTH
        for depth in (MAX_XML_DEPTH, MAX_XML_DEPTH + 1):
            with self.subTest(depth=depth):
                files = standard_files(['Hello'])
                files['customXml/limits.xml'] = '<n>' * depth + '</n>' * depth
                if depth == MAX_XML_DEPTH:
                    validate_docx(pack(files))
                else:
                    with self.assertRaises(GuardError) as caught:
                        validate_docx(pack(files))
                    self.assertEqual(caught.exception.code, 'unsafe_package')
                    self.assertEqual(caught.exception.reason, 'xml_depth')
                    self.assertEqual(caught.exception.part, 'customXml/limits.xml')

    def test_xml_attribute_limit_preserves_part_diagnostics(self):
        from word_endpoint.guard import MAX_XML_ATTRIBUTES
        for count in (MAX_XML_ATTRIBUTES, MAX_XML_ATTRIBUTES + 1):
            with self.subTest(count=count):
                files = standard_files(['Hello'])
                attributes = ' '.join(f'a{i}="value"' for i in range(count))
                files['customXml/limits.xml'] = f'<n {attributes}/>'
                if count == MAX_XML_ATTRIBUTES:
                    validate_docx(pack(files))
                else:
                    with self.assertRaises(GuardError) as caught:
                        validate_docx(pack(files))
                    self.assertEqual(caught.exception.code, 'unsafe_package')
                    self.assertEqual(caught.exception.reason, 'xml_attributes')
                    self.assertEqual(caught.exception.part, 'customXml/limits.xml')

    def test_internal_parent_relationship_is_resolved_inside_package(self):
        files = standard_files(["A contract with custom metadata"])
        relationship(files, "../customXml/item1.xml")
        files["customXml/item1.xml"] = '<metadata><control>ordinary custom XML</control></metadata>'
        validate_docx(pack(files))

    def test_plain_upload_is_scanned_once_and_not_repacked(self):
        files = standard_files(["Hello"])
        blob = pack(files)
        import word_endpoint.guard as guard
        with patch.object(guard.zipfile, "ZipFile", wraps=zipfile.ZipFile) as opened:
            self.assertEqual(prepare_docx(blob), blob)
        self.assertEqual(opened.call_count, 1)

    def test_template_stripping_rejects_comment_hidden_dde(self):
        payload = ('<w:attachedTemplate><!-- </w:attachedTemplate>'
                   '<w:p><w:r><w:instrText>DDEAUTO synthetic</w:instrText></w:r></w:p>'
                   '<w:attachedTemplate> --></w:attachedTemplate>')
        blob = pack(standard_files(['Harmless regression fixture'], payload))
        # The original XML comment hides the field from structural scanning.
        self.assertEqual(validate_docx(blob, allow_attached_template=True), {'word/document.xml'})
        for sanitize in (prepare_docx, sanitize_output_docx):
            with self.subTest(sanitize=sanitize.__name__), self.assertRaises(GuardError) as caught:
                sanitize(blob)
            self.assertEqual(caught.exception.code, 'active_content')
            self.assertEqual(caught.exception.reason, 'forbidden_field_command')

    def test_prepared_copy_rejects_leftover_template_markup(self):
        blob = pack(standard_files(['Hello'], '<w:attachedTemplate/>'))
        with patch('word_endpoint.guard._strip_template_stamp', return_value=blob):
            with self.assertRaises(GuardError) as caught:
                prepare_docx(blob)
        self.assertEqual(caught.exception.code, 'external_content')

    def test_sanitized_copy_preserves_output_size_limit(self):
        files = standard_files(['Output with template'])
        files['word/settings.xml'] = files['word/settings.xml'].replace('</w:settings>', '<w:attachedTemplate/></w:settings>')
        files['[Content_Types].xml'] = files['[Content_Types].xml'].replace('</Types>', '<Default Extension="bin" ContentType="application/octet-stream"/></Types>')
        import random
        files['word/media/data.bin'] = random.Random(0).randbytes(21 * 1024 * 1024)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        blob = buffer.getvalue()
        self.assertGreater(len(blob), 20 * 1024 * 1024)
        self.assertGreater(len(sanitize_output_docx(blob)), 20 * 1024 * 1024)

    def test_root_absolute_and_percent_encoded_package_targets(self):
        for target in ("/customXml/item%201.xml", "../customXml/item%201.xml"):
            with self.subTest(target=target):
                files = standard_files(["Hello"])
                files["customXml/item 1.xml"] = "<data/>"
                relationship(files, target)
                validate_docx(pack(files))

    def test_escape_and_missing_internal_targets_remain_rejected(self):
        for target, reason in (("../../outside.xml", "relationship_escapes_package"),
                               ("%2e%2e/%2e%2e/outside.xml", "relationship_escapes_package"),
                               ("missing.xml", "missing_relationship_target")):
            with self.subTest(target=target):
                files = standard_files(["Hello"])
                relationship(files, target)
                with self.assertRaises(GuardError) as caught:
                    validate_docx(pack(files))
                self.assertEqual(caught.exception.reason, reason)
                self.assertEqual(caught.exception.part, "word/_rels/document.xml.rels")

    def test_highly_compressed_legitimate_document_is_accepted(self):
        files = standard_files(["Boilerplate clause."] * 25000)
        blob = pack(files)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            info = z.getinfo("word/document.xml")
            self.assertGreater(info.file_size / info.compress_size, 100)
        validate_docx(blob)

    def test_more_than_500_parts_are_accepted(self):
        import base64
        files = standard_files(["Illustrated contract"])
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
        pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7ZkAAAAASUVORK5CYII=")
        for i in range(550):
            files[f"word/media/image{i}.png"] = pixel
        validate_docx(pack(files))

    def test_utf16_word_xml_is_accepted(self):
        files = standard_files(["Unicode document"])
        files["word/document.xml"] = files["word/document.xml"].replace('encoding="UTF-8"', 'encoding="UTF-16"').encode("utf-16")
        validate_docx(pack(files))

    def test_utf16_without_bom_is_accepted(self):
        for encoding in ("utf-16-le", "utf-16-be"):
            files = standard_files(["Unicode document"])
            files["word/document.xml"] = files["word/document.xml"].replace('encoding="UTF-8"', f'encoding="{encoding}"').encode(encoding)
            with self.subTest(encoding=encoding):
                validate_docx(pack(files))

    def test_template_is_detached_without_changing_document_content(self):
        files = standard_files(["The original contractual text"])
        files["word/settings.xml"] = files["word/settings.xml"].replace("</w:settings>",
            f'<w:attachedTemplate xmlns:r="{REL_TYPE[:-1]}" r:id="rIdTemplate"/><w:linkStyles/></w:settings>')
        files["word/_rels/settings.xml.rels"] = f'<p:Relationships xmlns:p="http://schemas.openxmlformats.org/package/2006/relationships"><p:Relationship Id="rIdTemplate" Type="{REL_TYPE}attachedTemplate" Target="file:///C:/Templates/contract.dotx" TargetMode="External"/></p:Relationships>'
        raw = pack(files)
        cleaned = prepare_docx(raw)
        validate_docx(cleaned)
        with zipfile.ZipFile(io.BytesIO(cleaned)) as z:
            self.assertEqual(z.read("word/document.xml"), files["word/document.xml"].encode())
            self.assertNotIn(b"attachedTemplate", z.read("word/settings.xml"))
            self.assertNotIn(b"linkStyles", z.read("word/settings.xml"))
            self.assertNotIn(b"contract.dotx", z.read("word/_rels/settings.xml.rels"))

    def test_template_with_legal_xml_prefix_and_quoted_greater_than_is_detached(self):
        files = standard_files(["Hello"])
        files["word/settings.xml"] = files["word/settings.xml"].replace("</w:settings>", '<x-word:attachedTemplate xmlns:x-word="http://schemas.openxmlformats.org/wordprocessingml/2006/main" hint="a>b"/></w:settings>')
        files["word/_rels/settings.xml.rels"] = f'<p:Relationships xmlns:p="http://schemas.openxmlformats.org/package/2006/relationships"><p:Relationship Id="rId1" Type="{REL_TYPE}attachedTemplate" Target="file:///C:/a>b.dotx" TargetMode="External"/></p:Relationships>'
        validate_docx(prepare_docx(pack(files)))

    def test_field_arguments_may_mention_dangerous_command_names(self):
        files = standard_files(["Hello"], '<w:p><w:r><w:instrText> REF LINK </w:instrText></w:r></w:p><w:p><w:fldSimple w:instr="IF 1 &lt; 2 &quot;DDE&quot; &quot;LINK&quot;"/></w:p>')
        validate_docx(pack(files))

    def test_split_field_is_checked_as_one_command(self):
        files = standard_files(["Hello"], '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>DD</w:instrText></w:r><w:r><w:instrText>EAUTO calc</w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
        with self.assertRaises(GuardError):
            validate_docx(pack(files))

    def test_literal_entity_text_in_a_hyperlink_is_accepted(self):
        files = standard_files(["Hello"])
        relationship(files, "https://example.com/?q=&amp;lt;name&amp;gt;", "hyperlink", 'TargetMode="External"')
        validate_docx(pack(files))

    def test_static_svg_is_accepted_but_active_or_external_svg_is_rejected(self):
        files = standard_files(["An Office icon"])
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("</Types>", '<Default Extension="svg" ContentType="image/svg+xml"/></Types>')
        files["word/media/image.svg"] = '<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="paint"/></defs><path d="M0 0L10 10" fill="url(&quot;#paint&quot;)"/></svg>'
        validate_docx(pack(files))
        for inner in ('<script>alert(1)</script>', '<image href="https://example.com/image"/>', '<path onclick="run()"/>'):
            files["word/media/image.svg"] = f'<svg xmlns="http://www.w3.org/2000/svg">{inner}</svg>'
            with self.subTest(inner=inner), self.assertRaises(GuardError):
                validate_docx(pack(files))

    def test_dtd_is_rejected_before_relationship_parsing(self):
        files = standard_files(["Hello"])
        files["_rels/.rels"] = '<!DOCTYPE Relationships [<!ENTITY x "word/document.xml">]>' + files["_rels/.rels"].split("?>", 1)[1].replace('Target="word/document.xml"', 'Target="&x;"')
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.reason, "xml_dtd_or_entity")

    def test_dtd_and_entity_rejection_preserves_part_diagnostics(self):
        cases = (
            ('[Content_Types].xml', 'unsafe_package', 'xml_dtd_or_entity', None),
            ('_rels/.rels', 'unsafe_package', 'xml_dtd_or_entity', None),
            ('word/document.xml', 'unsafe_package', 'xml_dtd_or_entity', 'word/document.xml'),
            ('word/_rels/document.xml.rels', 'unsafe_package', 'xml_dtd_or_entity', 'word/_rels/document.xml.rels'),
            ('word/media/image.svg', 'active_content', 'svg_dtd', 'word/media/image.svg'),
        )
        for part, code, reason, reported_part in cases:
            for declaration in ('<!DOCTYPE payload>', '<!ENTITY payload "value">'):
                with self.subTest(part=part, declaration=declaration):
                    files = standard_files(['Hello'])
                    files[part] = declaration + files.get(part, '<svg xmlns="http://www.w3.org/2000/svg"/>')
                    with self.assertRaises(GuardError) as caught:
                        validate_docx(pack(files))
                    self.assertEqual(caught.exception.code, code)
                    self.assertEqual(caught.exception.reason, reason)
                    self.assertEqual(caught.exception.part, reported_part)

    def test_malformed_xml_preserves_part_diagnostics(self):
        cases = (
            ('[Content_Types].xml', 'invalid_zip_or_xml', None),
            ('_rels/.rels', 'invalid_zip_or_xml', None),
            ('word/document.xml', 'invalid_xml', 'word/document.xml'),
            ('word/_rels/document.xml.rels', 'invalid_xml', 'word/_rels/document.xml.rels'),
            ('word/media/image.svg', 'invalid_zip_or_xml', None),
        )
        for part, reason, reported_part in cases:
            with self.subTest(part=part):
                files = standard_files(['Hello'])
                files[part] = '<unclosed>'
                with self.assertRaises(GuardError) as caught:
                    validate_docx(pack(files))
                self.assertEqual(caught.exception.code, 'unsafe_package')
                self.assertEqual(caught.exception.reason, reason)
                self.assertEqual(caught.exception.part, reported_part)

    def test_svg_can_embed_static_raster_data_but_not_nested_svg(self):
        import base64
        files = standard_files(["An embedded image"])
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("</Types>", '<Default Extension="svg" ContentType="image/svg+xml"/></Types>')
        png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7ZkAAAAASUVORK5CYII="
        files["word/media/image.svg"] = f'<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,{png}"/></svg>'
        validate_docx(pack(files))
        for mime, data in (("image/svg+xml", b'<svg><script/></svg>'), ("image/png", b"<html><script/></html>")):
            encoded = base64.b64encode(data).decode()
            files["word/media/image.svg"] = f'<svg xmlns="http://www.w3.org/2000/svg"><image href="data:{mime};base64,{encoded}"/></svg>'
            with self.subTest(mime=mime), self.assertRaises(GuardError):
                validate_docx(pack(files))

    def test_content_type_character_references_are_interpreted_as_xml(self):
        files = standard_files(["Hello"])
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("/word/document.xml", "/word/&#100;ocument.xml")
        validate_docx(pack(files))
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("</Types>", '<Override PartName="/word/payload.bin" ContentType="application/vnd.ms-office.vbaPr&#111;ject"/></Types>')
        files["word/payload.bin"] = b"payload"
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "macros")

    def test_main_document_can_live_at_another_valid_package_path(self):
        files = standard_files(["A valid Word main part with a different URI"])
        files["docs/main.xml"] = files.pop("word/document.xml")
        files["_rels/.rels"] = files["_rels/.rels"].replace("word/document.xml", "docs/main.xml")
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("/word/document.xml", "/docs/main.xml")
        files["docs/_rels/main.xml.rels"] = files.pop("word/_rels/document.xml.rels").replace('Target="styles.xml"', 'Target="../word/styles.xml"').replace('Target="settings.xml"', 'Target="../word/settings.xml"')
        validate_docx(pack(files))
        files["docs/main.xml"] = files["docs/main.xml"].replace("</w:body>", '<w:p><w:fldSimple w:instr="DDEAUTO calc"/></w:p></w:body>')
        with self.assertRaises(GuardError):
            validate_docx(pack(files))

    def test_xml_and_svg_with_nonstandard_extensions_are_still_scanned(self):
        for mime, payload in (("application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml", '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:footnote w:id="1"><w:p><w:fldSimple w:instr="DDEAUTO calc"/></w:p></w:footnote></w:footnotes>'),
                              ("image/svg+xml", '<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')):
            files = standard_files(["Hello"])
            files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("</Types>", f'<Override PartName="/extras/payload.bin" ContentType="{mime}"/></Types>')
            files["extras/payload.bin"] = payload
            with self.subTest(mime=mime), self.assertRaises(GuardError):
                validate_docx(pack(files))


if __name__ == "__main__":
    unittest.main()
