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
        for boundary in ("x" * 71, "ends-in-space ", ""):
            with self.subTest(boundary=boundary), self.assertRaises(MultipartError):
                parse_multipart(f'multipart/form-data; boundary="{boundary}"', body, 1000)

    def test_accepts_any_rfc_2046_boundary_length(self):
        # RFC 2046 allows 1 to 70 characters; boundary=docx is a valid upload.
        for boundary in ("d", "docx", "x" * 70, "with space-inside"):
            with self.subTest(boundary=boundary):
                body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"\r\n\r\n"
                        f"hello\r\n--{boundary}--\r\n").encode()
                files = parse_multipart(f'multipart/form-data; boundary="{boundary}"', body, 1000)
                self.assertEqual(files, {"document": b"hello"})

    def test_a_boundary_with_separators_must_be_quoted(self):
        # RFC 2045 and RFC 9110: an unquoted parameter value is a token, so a
        # boundary holding "," ":" "/" "(" ")" "=" or "?" comes quoted.
        # Parsers that read such a bare value differently would disagree with
        # this one about where the body's parts start.
        for boundary in ("a,b", "a:b", "a/b", "a(b)", "a=b", "a?b"):
            body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"\r\n\r\n"
                    f"hello\r\n--{boundary}--\r\n").encode()
            with self.subTest(boundary=boundary):
                with self.assertRaises(MultipartError) as caught:
                    parse_multipart(f"multipart/form-data; boundary={boundary}", body, 1000)
                self.assertEqual(caught.exception.code, "bad_multipart")
                files = parse_multipart(f'multipart/form-data; boundary="{boundary}"', body, 1000)
                self.assertEqual(files, {"document": b"hello"})
        body = b'--abc.123_x\r\nContent-Disposition: form-data; name="document"\r\n\r\nhello\r\n--abc.123_x--\r\n'
        self.assertEqual(parse_multipart("multipart/form-data; boundary=abc.123_x", body, 1000), {"document": b"hello"})

    def test_an_apostrophe_is_part_of_a_token_not_a_quote(self):
        # "'" is a token character (RFC 9110 5.6.2), so boundary='abc' names the
        # boundary 'abc', apostrophes included.
        body = b"--'abc'\r\nContent-Disposition: form-data; name=\"document\"\r\n\r\nhello\r\n--'abc'--\r\n"
        self.assertEqual(parse_multipart("multipart/form-data; boundary='abc'", body, 1000), {"document": b"hello"})
        with self.assertRaises(MultipartError):
            parse_multipart("multipart/form-data; boundary='abc'", body.replace(b"'abc'", b"abc"), 1000)
        # The same for a field name: 'document' is not document.
        renamed = body.replace(b'name="document"', b"name='document'")
        with self.assertRaises(MultipartError) as caught:
            parse_multipart("multipart/form-data; boundary='abc'", renamed, 1000)
        self.assertEqual(caught.exception.code, "unexpected_field")

    def test_accepts_transport_padding_after_delimiters(self):
        content_type, body = encode_form([("original", "a.docx", b"aaa \t"), ("revised", "b.docx", b"bbb")])
        boundary = content_type.split("boundary=", 1)[1].encode()
        padded = body.replace(b"--" + boundary + b"\r\n", b"--" + boundary + b" \t \r\n")
        self.assertNotEqual(padded, body)
        # The file bytes keep their own trailing spaces and tab.
        self.assertEqual(parse_multipart(content_type, padded, 1000), {"original": b"aaa \t", "revised": b"bbb"})
        with self.assertRaises(MultipartError):
            parse_multipart(content_type, body.replace(b"--" + boundary + b"\r\n", b"--" + boundary + b" x\r\n", 1), 1000)

    def test_quoted_filename_cannot_change_the_field_name(self):
        content_type, body = encode_form([("document", "budget;name=Q4.docx", b"abc")])
        self.assertEqual(parse_multipart(content_type, body, 1000), {"document": b"abc"})
        escaped = body.replace(b'filename="budget;name=Q4.docx"', b'filename="a\\";name=\\"x.docx"')
        self.assertEqual(parse_multipart(content_type, escaped, 1000), {"document": b"abc"})
        # Two name parameters are ambiguous, so neither is used.
        doubled = body.replace(b'name="document";', b'name="document"; name="other";')
        with self.assertRaises(MultipartError) as caught:
            parse_multipart(content_type, doubled, 1000)
        self.assertEqual(caught.exception.code, "unexpected_field")

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
