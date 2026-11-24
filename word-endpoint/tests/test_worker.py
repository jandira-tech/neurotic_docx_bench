import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch
import tempfile
import shutil
from types import SimpleNamespace

import pywintypes

from word_endpoint.worker import (
    _MAC_REVISION_OPTIONS,
    WorkerError,
    _lock_fields,
    compare_documents,
    export_pdf,
    parse_job_command,
    set_revision_options,
)


class WorkerTests(unittest.TestCase):
    def test_pdf_export_uses_word_for_macs_inline_view_with_and_without_comments(self):
        for comments in (0, 2):
            with self.subTest(comments=comments):
                document = Mock()
                document.Comments.Count = comments
                # Deliberately inherit a different view before conversion.
                view = document.ActiveWindow.View
                view.RevisionsMode = 2
                view.ShowFormatChanges = False
                view.ShowComments = False
                view.RevisionsFilter.Markup = 0
                def exporting(**kwargs):
                    self.assertEqual(view.RevisionsMode, 1)
                    self.assertEqual(view.RevisionsFilter.Markup, 2)
                    self.assertEqual(view.RevisionsFilter.View, 0)
                    self.assertTrue(view.ShowRevisionsAndComments)
                    self.assertTrue(view.ShowInsertionsAndDeletions)
                    self.assertTrue(view.ShowFormatChanges)
                    self.assertTrue(view.ShowComments)
                    self.assertEqual(kwargs['Item'], 7)
                document.ExportAsFixedFormat.side_effect = exporting
                export_pdf(document, Path('unused.pdf'))
                document.ExportAsFixedFormat.assert_called_once()

    def test_revision_options_are_set_to_word_for_macs(self):
        options = SimpleNamespace(**{name: 0 for name, _ in _MAC_REVISION_OPTIONS})
        options.RevisedLinesColor = 6  # already right: left alone
        with self.assertLogs(level='INFO') as logs:
            set_revision_options(options)
        self.assertEqual({name: getattr(options, name) for name, _ in _MAC_REVISION_OPTIONS}, dict(_MAC_REVISION_OPTIONS))
        self.assertNotIn('RevisedLinesColor', ''.join(logs.output))
        self.assertEqual(dict(_MAC_REVISION_OPTIONS)['RevisedLinesColor'], 6)

    def test_a_revision_option_word_refuses_is_logged_not_raised(self):
        class Refusing(SimpleNamespace):
            def __setattr__(self, name, value):
                if name == 'CommentsColor':
                    raise pywintypes.com_error(-1, 'refused', None, None)
                super().__setattr__(name, value)
        options = Refusing(**{name: 0 for name, _ in _MAC_REVISION_OPTIONS})
        with self.assertLogs(level='WARNING') as logs:
            set_revision_options(options)
        self.assertIn('CommentsColor', ''.join(logs.output))
        self.assertEqual(options.InsertedTextMark, 3)
        self.assertEqual(options.SplitCellColor, 5)

    def test_comparison_pdf_exports_live_result_with_markup_without_saving_docx(self):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        original, revised, result, word = Mock(), Mock(), Mock(), Mock()
        result.StoryRanges = []
        result.Comments.Count = 2
        word.CompareDocuments.return_value = result
        result.ExportAsFixedFormat.side_effect = lambda **kwargs: Path(kwargs['OutputFileName']).write_bytes(b'%PDF-1.4\n' + b'x' * 80)
        with patch('word_endpoint.worker.open_document', side_effect=[original, revised]) as opening, patch('word_endpoint.worker.scrub_properties'), patch('word_endpoint.worker.close_document') as closing:
            compare_documents(word, directory, as_pdf=True)
        self.assertEqual(opening.call_count, 2)
        self.assertEqual(result.ExportAsFixedFormat.call_args.kwargs['Item'], 7)
        self.assertEqual(result.ActiveWindow.View.RevisionsMode, 1)
        self.assertTrue(result.ActiveWindow.View.ShowComments)
        self.assertTrue(result.ActiveWindow.View.ShowRevisionsAndComments)
        result.SaveAs2.assert_not_called()
        self.assertEqual(closing.call_count, 3)
        self.assertTrue((directory / 'output.pdf').exists())
        self.assertFalse((directory / 'output.docx').exists())

    def test_comparison_pdf_export_failure_has_no_clean_fallback(self):
        result, word = Mock(), Mock()
        result.StoryRanges = []
        result.Comments.Count = 0
        word.CompareDocuments.return_value = result
        result.ExportAsFixedFormat.side_effect = pywintypes.com_error(-1, 'export failed', None, None)
        with patch('word_endpoint.worker.open_document'), patch('word_endpoint.worker.scrub_properties'):
            with self.assertLogs(level='ERROR'), self.assertRaises(WorkerError) as caught:
                compare_documents(word, Path('unused'), as_pdf=True)
        self.assertEqual(caught.exception.code, 'convert_failed')
        self.assertEqual(result.ExportAsFixedFormat.call_count, 1)
        result.SaveAs2.assert_not_called()

    def test_conversion_lane_cannot_accept_comparison_jobs(self):
        with self.assertRaises(WorkerError):
            parse_job_command('convert', b'compare_pdf\tC:\\unused\n')

    def test_failed_markup_export_cannot_fall_back_to_clean_export(self):
        document = Mock()
        document.Comments.Count = 0
        document.ExportAsFixedFormat.side_effect = pywintypes.com_error(-1, "export failed", None, None)
        with self.assertLogs(level='ERROR'), self.assertRaises(WorkerError) as caught:
            export_pdf(document, Path("output.pdf"))
        self.assertEqual(caught.exception.code, "convert_failed")
        self.assertEqual(document.ExportAsFixedFormat.call_count, 1)
        self.assertEqual(document.ExportAsFixedFormat.call_args.kwargs["Item"], 7)

    def test_locks_all_fields_with_one_com_assignment(self):
        document = Mock()
        document.Sections.Count = 0
        document.Fields.Count = 500
        story = Mock()
        story.Fields = document.Fields
        story.NextStoryRange = None
        document.StoryRanges = [story]
        _lock_fields(document)
        self.assertTrue(document.Fields.Locked)
        document.Fields.Item.assert_not_called()

    def test_locks_fields_in_additional_sections_and_textbox_stories(self):
        first, second, textbox = Mock(), Mock(), Mock()
        for story in (first, second, textbox):
            story.Fields.Count = 3000
            story.NextStoryRange = None
        first.NextStoryRange = second
        document = Mock()
        document.StoryRanges = [first, textbox]
        _lock_fields(document)
        for story in (first, second, textbox):
            self.assertTrue(story.Fields.Locked)

    def test_timed_call_retries_busy_com_and_succeeds(self):
        from word_endpoint.worker import _timed_call
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] <= 2:
                raise pywintypes.com_error(-2147418111, "Call was rejected by callee.", None, None)
            return "done"

        workdir = Mock()
        workdir.name = "job"
        with patch("word_endpoint.worker.time.sleep"):
            self.assertEqual(_timed_call("phase", workdir, flaky), "done")
        self.assertEqual(calls["n"], 3)

    def test_timed_call_does_not_retry_other_com_errors(self):
        from word_endpoint.worker import _timed_call

        def refusing():
            raise pywintypes.com_error(-2147352567, "Exception occurred.",
                                       (0, "Microsoft Word", "protected area",
                                        "wdmain11.chm", 37373, -2146823683), None)

        workdir = Mock()
        workdir.name = "job"
        with self.assertRaises(pywintypes.com_error):
            _timed_call("phase", workdir, refusing)

    def test_timed_call_stops_retrying_after_three_busy_attempts(self):
        from word_endpoint.worker import _timed_call
        calls = {"n": 0}

        def always_busy():
            calls["n"] += 1
            raise pywintypes.com_error(-2147418111, "Call was rejected by callee.", None, None)

        workdir = Mock()
        workdir.name = "job"
        with self.assertRaises(pywintypes.com_error), \
                patch("word_endpoint.worker.time.sleep"):
            _timed_call("phase", workdir, always_busy)
        self.assertEqual(calls["n"], 4)  # initial call + 3 retries

    def test_wait_word_ready_returns_once_com_answers(self):
        from word_endpoint.worker import _wait_word_ready
        word = Mock()
        word.Version = Mock(side_effect=[
            pywintypes.com_error(-2147418111, "busy", None, None), "16.0"])
        with patch("word_endpoint.worker.time.sleep"):
            self.assertTrue(_wait_word_ready(word, timeout_s=5))

    def test_quit_word_logs_dead_proxy_without_error(self):
        from word_endpoint.worker import quit_word
        word = Mock()
        # The dynamic proxy raises AttributeError once the process is gone.
        word.Quit = Mock(side_effect=AttributeError("Word.Application.Quit"))
        with self.assertLogs("root", level="INFO") as logs:
            quit_word(word)
        self.assertTrue(any("already gone" in line for line in logs.output))

    def test_lock_fields_skips_protected_stories_instead_of_rejecting(self):
        # A protected document refuses fields.Locked = True (COM 37373).
        # Locking is best-effort hardening: skip the protected story,
        # keep locking the other stories, never fail the job.
        ok_story = Mock()
        ok_story.Fields.Count = 4
        ok_story.NextStoryRange = None

        class protected_fields:
            Count = 4

            def __setattr__(self, name, value):
                raise pywintypes.com_error(
                    -2147352567,
                    "Exception occurred.",
                    (0, "Microsoft Word",
                     "This method or property is not available because the "
                     "object refers to a protected area of the document.",
                     "wdmain11.chm", 37373, -2146823683),
                    None,
                )

        protected_story = Mock()
        protected_story.Fields = protected_fields()
        protected_story.NextStoryRange = None

        document = Mock()
        document.StoryRanges = [protected_story, ok_story]

        _lock_fields(document)

        self.assertTrue(ok_story.Fields.Locked)
