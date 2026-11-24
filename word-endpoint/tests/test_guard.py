import io
import unittest
import zipfile

from tests.factory import make_docx, pack, standard_files
from word_endpoint.guard import GuardError, sanitize_output_docx, validate_docx

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
