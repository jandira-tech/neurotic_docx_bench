import unittest

from tests.factory import encode_form
from word_endpoint.multipart import MultipartError, parse_multipart


class MultipartTests(unittest.TestCase):
    def test_reads_two_files_and_ignores_the_filename(self):
        content_type, body = encode_form(
            [
                ("original", 'evil"; filename="other.docx', b"aaa"),
                ("revised", "b.docx", b"bbb"),
            ]
        )
        files = parse_multipart(content_type, b"preamble\r\n" + body, 1000)
        self.assertEqual(files, {"original": b"aaa", "revised": b"bbb"})

    def test_rejects_base64_and_short_boundaries(self):
        content_type, body = encode_form([("document", "a.docx", b"hello")])
        mutated = body.replace(
            b"Content-Type: application/octet-stream\r\n",
            b"Content-Type: application/octet-stream\r\nContent-Transfer-Encoding: base64\r\n",
        )
        with self.assertRaises(MultipartError) as caught:
            parse_multipart(content_type, mutated, 1000)
        self.assertEqual(caught.exception.code, "bad_multipart")
        with self.assertRaises(MultipartError):
            parse_multipart("multipart/form-data; boundary=short", body, 1000)

    def test_rejects_too_many_parts_and_oversize_parts(self):
        content_type, body = encode_form(
            [
                ("one", "a.docx", b"a"),
                ("two", "b.docx", b"b"),
                ("three", "c.docx", b"c"),
                ("four", "d.docx", b"d"),
            ]
        )
        with self.assertRaises(MultipartError) as caught:
            parse_multipart(content_type, body, 1000)
        self.assertEqual(caught.exception.code, "too_many_parts")
        content_type, body = encode_form([("document", "a.docx", b"abcdef")])
        with self.assertRaises(MultipartError) as caught:
            parse_multipart(content_type, body, 3)
        self.assertEqual(caught.exception.code, "too_large")


if __name__ == "__main__":
    unittest.main()
