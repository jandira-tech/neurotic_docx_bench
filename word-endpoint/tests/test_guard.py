import io
import unittest
import zipfile

from tests.factory import make_docx, pack, standard_files
from word_endpoint.guard import GuardError, prepare_docx, sanitize_output_docx, validate_docx

DDE = (
    "<w:p>"
    "<w:r><w:fldChar w:fldCharType=\"begin\"/></w:r>"
    "<w:r><w:instrText>DDEAUTO c:\\\\Windows\\\\System32\\\\cmd.exe</w:instrText></w:r>"
    "<w:r><w:fldChar w:fldCharType=\"end\"/></w:r>"
    "</w:p>"
)


class GuardTests(unittest.TestCase):
    def test_accepts_a_plain_document(self):
        validate_docx(make_docx(["The fee is 100 dollars."]))

    def test_accepts_prose_that_mentions_dde(self):
        validate_docx(make_docx(["DDE is discussed in this paragraph."]))

    def test_accepts_a_hyperlink_field_and_https_relationship(self):
        files = standard_files(
            ["See the site."],
            extra_body=(
                "<w:p><w:r><w:instrText>HYPERLINK \"https://example.com\"</w:instrText></w:r></w:p>"
            ),
        )
        files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
            "</Relationships>",
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.com" TargetMode="External"/>'
            "</Relationships>",
        )
        validate_docx(pack(files))

    def test_accepts_a_directory_entry(self):
        files = standard_files(["Hello"])
        files["word/"] = b""
        validate_docx(pack(files))

    def test_rejects_dde_field(self):
        with self.assertRaises(GuardError) as caught:
            validate_docx(make_docx(["Hello"], DDE))
        self.assertEqual(caught.exception.code, "active_content")

    def test_rejects_dde_split_across_instructions(self):
        extra = (
            "<w:p><w:r><w:instrText>DD</w:instrText></w:r>"
            "<w:r><w:instrText>EAUTO evil</w:instrText></w:r></w:p>"
        )
        with self.assertRaises(GuardError) as caught:
            validate_docx(make_docx(["Hello"], extra))
        self.assertEqual(caught.exception.code, "active_content")

    def test_rejects_encoded_dde(self):
        extra = "<w:p><w:r><w:instrText>&#68;&#68;&#69; calc</w:instrText></w:r></w:p>"
        with self.assertRaises(GuardError) as caught:
            validate_docx(make_docx(["Hello"], extra))
        self.assertEqual(caught.exception.code, "active_content")

    def test_rejects_external_image(self):
        files = standard_files(["Chart"])
        files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
            "</Relationships>",
            '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="https://evil.example/a.png" TargetMode="External"/>'
            "</Relationships>",
        )
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "external_content")

    def test_rejects_attached_template_and_sanitize_removes_it(self):
        files = standard_files(["Hello"])
        files["word/settings.xml"] = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:attachedTemplate r:id="rId1"/>
</w:settings>
"""
        files["word/_rels/settings.xml.rels"] = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" Target="C:\\Users\\Administrator\\AppData\\Roaming\\Microsoft\\Templates\\Normal.dotm" TargetMode="External"/>
</Relationships>
"""
        raw = pack(files)
        with self.assertRaises(GuardError) as caught:
            validate_docx(raw)
        self.assertEqual(caught.exception.code, "external_content")
        cleaned = sanitize_output_docx(raw)
        validate_docx(cleaned)
        self.assertNotIn(b"Administrator", cleaned)
        self.assertNotIn(b"attachedTemplate", cleaned)

    def test_a_percent_encoded_part_name_is_scrubbed_like_the_plain_one(self):
        # Validation reads word/%73ettings.xml as word/settings.xml, so the
        # path scrub must select parts by that decoded name too.
        from pathlib import Path
        from xml.sax.saxutils import escape
        home = escape(str(Path.home()))
        for name in ("word/settings.xml", "word/%73ettings.xml", "%64ocProps/app.xml", "docProps/app.%78ml"):
            with self.subTest(name):
                files = standard_files(["Hello"])
                if name.endswith("ettings.xml"):
                    settings = files.pop("word/settings.xml")
                    files[name] = settings.replace("</w:settings>", f"<!-- {home}/Normal.dotm --></w:settings>")
                else:
                    files[name] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                   f"<Properties><Template>{home}/Normal.dotm</Template></Properties>")
                cleaned = sanitize_output_docx(pack(files))
                with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
                    text = archive.read(name).decode("utf-8")
                self.assertIn("Normal.dotm", text)
                self.assertNotIn(home.lower(), text.lower())

    def test_template_strip_leaves_markup_between_comments_alone(self):
        # A non-Word writer can put tag-shaped text in comments. A pattern that
        # ran over comments would match <w:linkStyles> in the first comment and
        # </w:linkStyles> in the second, deleting the live w:trackRevisions.
        rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        files = standard_files(["Hello"])
        files["word/settings.xml"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="{rel}">
  <w:attachedTemplate r:id="rId1"/>
  <!-- <w:linkStyles> -->
  <w:trackRevisions/>
  <!-- </w:linkStyles> -->
</w:settings>
"""
        files["word/_rels/settings.xml.rels"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <!-- <Relationship Id="rIdX" Type="{rel}/attachedTemplate"> -->
  <Relationship Id="rId2" Type="{rel}/styles" Target="styles.xml"/>
  <!-- </Relationship> -->
  <Relationship Id="rId1" Type="{rel}/attachedTemplate" Target="file:///C:/Normal.dotm" TargetMode="External"/>
</Relationships>
"""
        cleaned = prepare_docx(pack(files))
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            settings = archive.read("word/settings.xml").decode("utf-8")
            rels = archive.read("word/_rels/settings.xml.rels").decode("utf-8")
        self.assertIn("<w:trackRevisions/>", settings)
        self.assertNotIn('<w:attachedTemplate r:id="rId1"/>', settings)
        self.assertIn('Id="rId2"', rels)
        self.assertNotIn('Id="rId1"', rels)

    def test_template_elements_holding_only_comments_are_still_detached(self):
        # The schema gives these elements no content, but a comment or a
        # processing instruction between the tags is still well-formed.
        rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        files = standard_files(["Hello"])
        files["word/settings.xml"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="{rel}">
  <w:attachedTemplate r:id="rId1"><!--note--></w:attachedTemplate>
  <w:linkStyles> <!--note--> <?pi x?> </w:linkStyles>
  <w:trackRevisions/>
</w:settings>
"""
        files["word/_rels/settings.xml.rels"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{rel}/attachedTemplate" Target="file:///C:/Normal.dotm" TargetMode="External"><!--x--></Relationship>
</Relationships>
"""
        cleaned = prepare_docx(pack(files))
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            settings = archive.read("word/settings.xml").decode("utf-8")
            rels = archive.read("word/_rels/settings.xml.rels").decode("utf-8")
        self.assertNotIn("attachedTemplate", settings)
        self.assertNotIn("linkStyles", settings)
        self.assertIn("<w:trackRevisions/>", settings)
        self.assertNotIn('Id="rId1"', rels)

    def test_unterminated_comments_are_refused_in_linear_time(self):
        # Each "<!--" without a terminator made the comment-skipping regex
        # search to the end of the part again: 64 KB took 2.6 s, 128 KB ~10 s.
        import time
        files = standard_files(["Hello"])
        files["customXml/item1.xml"] = "<root>" + "<!--" * (128 * 256)
        started = time.perf_counter()
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "unsafe_package")
        self.assertLess(time.perf_counter() - started, 1.0)

    def test_template_stripping_is_linear_in_tag_shaped_cdata(self):
        # The paired form allowed comments between the tags, and a lazy
        # "<!--.*?-->" searched to the end of the part from every
        # "<w:attachedTemplate>" + "<!--" inside a CDATA section: 3.4 KB took
        # 4.3 s (MiniMax review). Non-markup spans now read as blank space.
        import time
        w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        files = standard_files(["Hello"])
        files["word/settings.xml"] = (
            f'<?xml version="1.0"?><w:settings xmlns:w="{w}" xmlns:r="{r}">'
            '<w:attachedTemplate r:id="rId1"/><w:t><![CDATA['
            + ("<w:attachedTemplate>" + "<!--" * 20) * 4000
            + "]]></w:t></w:settings>"
        )
        files["word/_rels/settings.xml.rels"] = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" '
            'Target="file:///C:/templates/evil.dotm" TargetMode="External"/></Relationships>'
        )
        started = time.perf_counter()
        cleaned = prepare_docx(pack(files))
        self.assertLess(time.perf_counter() - started, 1.0)
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            settings = archive.read("word/settings.xml").decode()
            rels = archive.read("word/_rels/settings.xml.rels").decode()
        self.assertNotIn('<w:attachedTemplate r:id="rId1"/>', settings)
        self.assertIn("<![CDATA[<w:attachedTemplate><!--", settings)
        self.assertNotIn("evil.dotm", rels)

    def _settings_rels_with_cdata(self, cdata):
        # A hyperlink relationship holding a CDATA section, beside a template
        # relationship. The schema gives Relationship no content, but the
        # guard must not read the CDATA as attributes either way.
        files = standard_files(["Hello"])
        files["word/_rels/settings.xml.rels"] = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="safe" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            f'Target="https://example.com" TargetMode="External"><![CDATA[{cdata}]]></Relationship>'
            '<Relationship Id="tpl" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" '
            'Target="file:///C:/templates/evil.dotm" TargetMode="External"/></Relationships>'
        )
        return files

    def test_template_relationship_check_is_linear_in_cdata_content(self):
        # Blanking non-markup spans let the paired Relationship form match an
        # element holding CDATA, and the Type lookup then ran an unanchored
        # attribute regex over the CDATA: 16,000 "A"s took 1.3 s (codex
        # review of 782c8b3f). Only the opening tag holds attributes.
        import time
        files = self._settings_rels_with_cdata("A" * 32000)
        started = time.perf_counter()
        cleaned = prepare_docx(pack(files))
        self.assertLess(time.perf_counter() - started, 0.5)
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            rels = archive.read("word/_rels/settings.xml.rels").decode()
        self.assertNotIn("evil.dotm", rels)
        self.assertIn('Id="safe"', rels)
        self.assertIn("A" * 32000, rels)

    def test_cdata_inside_a_relationship_is_not_read_as_its_type(self):
        files = self._settings_rels_with_cdata(' Type="/attachedTemplate" ')
        cleaned = prepare_docx(pack(files))
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            rels = archive.read("word/_rels/settings.xml.rels").decode()
        self.assertIn('Id="safe"', rels)
        self.assertNotIn("evil.dotm", rels)

    def test_only_an_attribute_named_type_gives_a_relationship_its_type(self):
        # Attribute names may hold "_", "-" and "."; a scan that skipped such a
        # name read "Type" out of its quoted value, or out of "X-Type", and
        # deleted the relationship (codex review of 02c2a796).
        hyperlink = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
        files = standard_files(["Hello"])
        files["word/_rels/settings.xml.rels"] = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="under" _=" Type=\'/attachedTemplate\' " Type="{hyperlink}" Target="https://example.com/a" TargetMode="External"/>'
            f'<Relationship Id="dashed" X-Type="/attachedTemplate" Type="{hyperlink}" Target="https://example.com/b" TargetMode="External"/>'
            f'<Relationship Id="dotted" a.b="x" Type="{hyperlink}" Target="https://example.com/c" TargetMode="External"/>'
            '<Relationship Id="tpl" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" '
            'Target="file:///C:/templates/evil.dotm" TargetMode="External"/></Relationships>'
        )
        cleaned = prepare_docx(pack(files))
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            rels = archive.read("word/_rels/settings.xml.rels").decode()
        for kept in ('Id="under"', 'Id="dashed"', 'Id="dotted"'):
            self.assertIn(kept, rels)
        self.assertNotIn("evil.dotm", rels)

    def test_percent_encoded_member_names_get_the_plain_name_checks(self):
        # Relationship targets and ZIP names are compared decoded, so a name
        # check on the raw spelling alone misses word/media/payload%2Eexe.
        rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        cases = {
            "word/media/payload%2Eexe": "active_content",
            "word/vba%50roject.bin": "macros",
            "word/media/%2E%2E/escape.png": "unsafe_package",
            "word/media/a%5Cb.png": "unsafe_package",
            "word/media/nul%00.png": "unsafe_package",
        }
        for name, code in cases.items():
            for referenced in (False, True):
                with self.subTest(name=name, referenced=referenced):
                    files = standard_files(["Hello"])
                    files[name] = b"MZ" + bytes(100)
                    if referenced:
                        target = name.removeprefix("word/")
                        files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
                            "</Relationships>",
                            f'<Relationship Id="rId99" Type="{rel}/image" Target="{target}"/></Relationships>')
                    with self.assertRaises(GuardError) as caught:
                        validate_docx(pack(files))
                    self.assertEqual(caught.exception.code, code)

    def test_a_relationship_part_with_an_encoded_extension_is_checked(self):
        # word/_rels/document%2Erels is a .rels part once decoded; the suffix
        # check read the raw name, so its external target was never looked at.
        files = standard_files(["Hello"])
        files["word/_rels/document%2Erels"] = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" '
            'Target="file:///C:/Windows/System32/evil.dll" TargetMode="External"/></Relationships>'
        )
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "external_content")

    def test_relationships_resolve_from_a_percent_encoded_source_folder(self):
        rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="{rel}/customXmlProps" Target="{{}}"/></Relationships>')
        for target, ok in (("other.xml", True), ("missing.xml", False)):
            with self.subTest(target=target):
                files = standard_files(["Hello"])
                files["customXml/caf%C3%A9/item.xml"] = "<a/>"
                files["customXml/caf%C3%A9/other.xml"] = "<b/>"
                files["customXml/caf%C3%A9/_rels/item.xml.rels"] = rels.format(target)
                if ok:
                    validate_docx(pack(files))
                else:
                    with self.assertRaises(GuardError) as caught:
                        validate_docx(pack(files))
                    self.assertEqual(caught.exception.reason, "missing_relationship_target")

    def test_doctype_text_inside_cdata_or_a_comment_is_not_a_declaration(self):
        files = standard_files(["Hello"])
        files["customXml/item1.xml"] = (
            '<?xml version="1.0"?><root><![CDATA[<!DOCTYPE html><p>x</p>]]>'
            "<!-- <!ENTITY e 'x'> --></root>"
        )
        validate_docx(pack(files))
        for declared in ('<!DOCTYPE root [<!ENTITY e "x">]><root/>',
                         "<!-- note --><!DOCTYPE root><root/>",
                         '<?xml version="1.0"?><!DOCTYPE root SYSTEM "http://example.com/x.dtd"><root/>'):
            with self.subTest(declared=declared):
                files["customXml/item1.xml"] = declared
                with self.assertRaises(GuardError) as caught:
                    validate_docx(pack(files))
                self.assertEqual(caught.exception.code, "unsafe_package")

    def test_relationship_targets_match_percent_encoded_and_plain_zip_names(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        for stored in ("word/media/caf%C3%A9.png", "word/media/caf\u00e9.png"):
            with self.subTest(stored=stored):
                files = standard_files(["Hello"])
                files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
                    "</Relationships>",
                    '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"'
                    ' Target="media/caf%C3%A9.png"/></Relationships>',
                )
                files[stored] = png
                validate_docx(pack(files))
        # Both spellings at once are one part stored twice.
        files["word/media/caf%C3%A9.png"] = png
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.reason, "duplicate_member")

    def test_rejects_macros_and_executables(self):
        files = standard_files(["Hello"])
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace(
            "</Types>",
            '<Override PartName="/word/vbaProject.bin" ContentType="application/vnd.ms-office.vbaProject"/>'
            "</Types>",
        )
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "macros")
        files = standard_files(["Hello"])
        files["word/embeddings/payload.exe"] = b"MZ"
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "active_content")

    def test_rejects_non_docx_and_encryption_marker(self):
        with self.assertRaises(GuardError) as caught:
            validate_docx(b"this is not a document")
        self.assertEqual(caught.exception.code, "not_docx")
        files = standard_files(["Hello"])
        files["EncryptionInfo"] = b"secret"
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "encrypted")

    def test_rejects_parent_path_and_too_many_entries(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("../evil.xml")
            archive.writestr(info, "<a/>")
        with self.assertRaises(GuardError) as caught:
            validate_docx(buffer.getvalue())
        self.assertIn(caught.exception.code, {"unsafe_package", "not_docx"})
        files = standard_files(["Hello"])
        for index in range(4096):
            files[f"word/media/item{index}.txt"] = "x"
        with self.assertRaises(GuardError) as caught:
            validate_docx(pack(files))
        self.assertEqual(caught.exception.code, "unsafe_package")

    def test_rejects_oversized_blob(self):
        blob = b"PK\x03\x04" + b"a" * (20 * 1024 * 1024)
        with self.assertRaises(GuardError) as caught:
            validate_docx(blob)
        self.assertEqual(caught.exception.code, "too_large")


if __name__ == "__main__":
    unittest.main()
