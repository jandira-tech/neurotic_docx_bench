"""Exercise live-check fixture handling without launching Word or making requests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import live_check
from tests.factory import make_docx
from word_endpoint.guard import GuardError, validate_docx
from word_endpoint.multipart import parse_multipart


class LiveFixtureTests(unittest.TestCase):
    def run_check(self, fixture_present):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / 'work'
            work.mkdir()
            for name, pid in (('compare', 101), ('convert', 102)):
                (work / (name + '.word.pid')).write_text(str(pid))
            if fixture_present:
                fixture = root / 'artifacts' / 'markup-demo' / 'with-comments.docx'
                fixture.parent.mkdir(parents=True)
                fixture.write_bytes(make_docx(['EUR 1,000.']))
            pdf = b'%PDF-1.4\n' + b'x' * 600
            compared = make_docx(['100 250'], '<w:p><w:ins w:id="1"><w:r><w:t>change</w:t></w:r></w:ins></w:p>')

            def call(base, path, payload, content_type, token):
                if token is None:
                    return 401, {}, b'{"code":"unauthorized"}'
                try:
                    for data in parse_multipart(content_type, payload, 20 * 1024 * 1024).values():
                        validate_docx(data)
                except GuardError as error:
                    return 400, {}, json.dumps({'code': error.code}).encode()
                if path == '/v1/compare':
                    return 200, {}, compared
                return 200, {'Content-Type': 'application/pdf'}, pdf

            text = ('100 250 Confirm whether the fee includes VAT. '
                    'Consider reducing the payment term to 14 days.')
            output = io.StringIO()
            with patch.object(live_check, 'ROOT', root), patch.object(live_check, 'winword_pids', return_value={101, 102}), patch.object(live_check, 'call', side_effect=call), patch('word_endpoint.config.load_settings', return_value=SimpleNamespace(port=8787, token='t' * 40)), patch.object(live_check.urllib.request, 'urlopen', return_value=SimpleNamespace(status=200, read=lambda: b'{"status":"ok"}')), patch('runpy.run_path', return_value={'fixture_text': lambda path: text}), contextlib.redirect_stdout(output):
                status = live_check.main()
            return status, output.getvalue()

    def test_missing_comment_fixture_fails_verification(self):
        status, output = self.run_check(False)
        self.assertEqual(status, 1)
        self.assertIn('FAIL commented DOCX fixture exists', output)
        self.assertIn('1 failure(s)', output)

    def test_present_comment_fixture_runs_comment_text_checks(self):
        status, output = self.run_check(True)
        self.assertEqual(status, 0, output)
        self.assertIn('PASS direct pdf retains VAT comment text', output)
        self.assertIn('PASS direct pdf retains payment comment text', output)


class DocxLeakTests(unittest.TestCase):
    def test_a_path_in_a_compressed_part_is_found(self):
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<w:t>" + b"padding " * 200 + b"C:\\Users\\someone\\x.dotm</w:t>")
            archive.writestr("word/styles.xml", b"<w:styles/>")
        body = buffer.getvalue()
        self.assertEqual(live_check.leaks(body), [])  # the old check, on ZIP bytes
        self.assertEqual(live_check.docx_leaks(body), ["word/document.xml:profile"])
        self.assertEqual(live_check.docx_leaks(make_docx(["clean"])), [])
        self.assertEqual(live_check.docx_leaks(b"%PDF-1.7"), ["not-a-docx"])


class LiveRecoverCleanupTests(unittest.TestCase):
    def test_server_is_stopped_when_verification_raises(self):
        from unittest.mock import Mock
        from tests import live_recover

        proc = Mock()
        proc.pid = 4242
        proc.poll.return_value = None
        proc.stdout = io.BytesIO(b"compare Word is ready\nconvert Word is ready\n")
        with patch.object(live_recover.subprocess, "Popen", return_value=proc), \
                patch.object(live_recover, "winword_pids", return_value=set()), \
                patch.object(live_recover, "free_port", return_value=1), \
                patch.object(live_recover.urllib.request, "urlopen", side_effect=TimeoutError("health")), \
                patch.object(live_recover, "stop_server") as stopping, \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(TimeoutError):
                live_recover.one_run(1, "secret")
        stopping.assert_called_once_with(proc)
