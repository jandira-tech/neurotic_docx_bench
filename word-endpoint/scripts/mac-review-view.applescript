-- Read Word for Mac's revision options, and the review view Word opens each given document in.
--     osascript scripts/mac-review-view.applescript /path/to/redline.docx [...]
-- Opens each document, reads the view of its window, and closes it without saving. Values are
-- printed by name (each enum is compared against its named enumerators from Word's dictionary).
-- docs/review-view.md lists what Word 16.115 returned on 2026-11-24 and the Windows equivalents.
on n_WdCellColor(x)
  tell application "Microsoft Word"
    if x is cell color by author then return "cell color by author"
    if x is cell color no highlight then return "cell color no highlight"
    if x is cell color pink then return "cell color pink"
    if x is cell color light blue then return "cell color light blue"
    if x is cell color light yellow then return "cell color light yellow"
    if x is cell color light purple then return "cell color light purple"
    if x is cell color light orange then return "cell color light orange"
    if x is cell color light green then return "cell color light green"
    if x is cell color light gray then return "cell color light gray"
  end tell
  return "?"
end n_WdCellColor
on n_WdColorIndex(x)
  tell application "Microsoft Word"
    if x is auto then return "auto"
    if x is black then return "black"
    if x is blue then return "blue"
    if x is turquoise then return "turquoise"
    if x is bright green then return "bright green"
    if x is pink then return "pink"
    if x is red then return "red"
    if x is yellow then return "yellow"
    if x is white then return "white"
    if x is dark blue then return "dark blue"
    if x is teal then return "teal"
    if x is green then return "green"
    if x is violet then return "violet"
    if x is dark red then return "dark red"
    if x is dark yellow then return "dark yellow"
    if x is gray50 then return "gray50"
    if x is gray25 then return "gray25"
    if x is by author then return "by author"
    if x is no highlight then return "no highlight"
  end tell
  return "?"
end n_WdColorIndex
on n_WdDeletedTextMark(x)
  tell application "Microsoft Word"
    if x is deleted text mark hidden then return "deleted text mark hidden"
    if x is deleted text mark strike through then return "deleted text mark strike through"
    if x is deleted text mark caret then return "deleted text mark caret"
    if x is deleted text mark pound then return "deleted text mark pound"
    if x is deleted text mark none then return "deleted text mark none"
    if x is deleted text mark bold then return "deleted text mark bold"
    if x is deleted text mark italic then return "deleted text mark italic"
    if x is deleted text mark underline then return "deleted text mark underline"
    if x is deleted text mark double underline then return "deleted text mark double underline"
    if x is deleted text mark color only then return "deleted text mark color only"
    if x is deleted text mark double strike through then return "deleted text mark double strike through"
  end tell
  return "?"
end n_WdDeletedTextMark
on n_WdInsertedTextMark(x)
  tell application "Microsoft Word"
    if x is inserted text mark none then return "inserted text mark none"
    if x is inserted text mark bold then return "inserted text mark bold"
    if x is inserted text mark italic then return "inserted text mark italic"
    if x is inserted text mark underline then return "inserted text mark underline"
    if x is inserted text mark double underline then return "inserted text mark double underline"
    if x is inserted text mark color only then return "inserted text mark color only"
    if x is inserted text mark strike through then return "inserted text mark strike through"
    if x is inserted text mark double strike through then return "inserted text mark double strike through"
  end tell
  return "?"
end n_WdInsertedTextMark
on n_WdMoveFromTextMark(x)
  tell application "Microsoft Word"
    if x is move from text mark hidden then return "move from text mark hidden"
    if x is move from text mark double strike through then return "move from text mark double strike through"
    if x is move from text mark strike through then return "move from text mark strike through"
    if x is move from text mark caret then return "move from text mark caret"
    if x is move from text mark pound then return "move from text mark pound"
    if x is move from text mark none then return "move from text mark none"
    if x is move from text mark bold then return "move from text mark bold"
    if x is move from text mark italic then return "move from text mark italic"
    if x is move from text mark underline then return "move from text mark underline"
    if x is move from text mark double underline then return "move from text mark double underline"
    if x is move from text mark color only then return "move from text mark color only"
  end tell
  return "?"
end n_WdMoveFromTextMark
on n_WdMoveToTextMark(x)
  tell application "Microsoft Word"
    if x is move to text mark none then return "move to text mark none"
    if x is move to text mark bold then return "move to text mark bold"
    if x is move to text mark italic then return "move to text mark italic"
    if x is move to text mark underline then return "move to text mark underline"
    if x is move to text mark double underline then return "move to text mark double underline"
    if x is move to text mark color only then return "move to text mark color only"
    if x is move to text mark strike through then return "move to text mark strike through"
    if x is move to text mark double strike through then return "move to text mark double strike through"
  end tell
  return "?"
end n_WdMoveToTextMark
on n_WdRevisedLinesMark(x)
  tell application "Microsoft Word"
    if x is revised lines mark none then return "revised lines mark none"
    if x is revised lines mark left border then return "revised lines mark left border"
    if x is revised lines mark right border then return "revised lines mark right border"
    if x is revised lines mark outside border then return "revised lines mark outside border"
  end tell
  return "?"
end n_WdRevisedLinesMark
on n_WdRevisedPropertiesMark(x)
  tell application "Microsoft Word"
    if x is revised properties mark none then return "revised properties mark none"
    if x is revised properties mark bold then return "revised properties mark bold"
    if x is revised properties mark italic then return "revised properties mark italic"
    if x is revised properties mark underline then return "revised properties mark underline"
    if x is revised properties mark double underline then return "revised properties mark double underline"
    if x is revised properties mark color only then return "revised properties mark color only"
    if x is revised properties mark strike through then return "revised properties mark strike through"
    if x is revised properties mark double strike through then return "revised properties mark double strike through"
  end tell
  return "?"
end n_WdRevisedPropertiesMark
on n_WdRevisionsMode(x)
  tell application "Microsoft Word"
    if x is balloon revisions then return "balloon revisions"
    if x is in line revisions then return "in line revisions"
    if x is mixed revisions then return "mixed revisions"
  end tell
  return "?"
end n_WdRevisionsMode
on n_WdRevisionsView(x)
  tell application "Microsoft Word"
    if x is revisions view final then return "revisions view final"
    if x is revisions view original then return "revisions view original"
  end tell
  return "?"
end n_WdRevisionsView

on run argv
  set out to ""
  with timeout of 180 seconds
    tell application "Microsoft Word"
      set o to settings
      set out to out & "options: " & "inserted text mark=" & my n_WdInsertedTextMark(inserted text mark of o) & "; " & "inserted text color=" & my n_WdColorIndex(inserted text color of o) & "; " & "deleted text mark=" & my n_WdDeletedTextMark(deleted text mark of o) & "; " & "deleted text color=" & my n_WdColorIndex(deleted text color of o) & "; " & "revised properties mark=" & my n_WdRevisedPropertiesMark(revised properties mark of o) & "; " & "revised properties color=" & my n_WdColorIndex(revised properties color of o) & "; " & "revised lines mark=" & my n_WdRevisedLinesMark(revised lines mark of o) & "; " & "revised lines color=" & my n_WdColorIndex(revised lines color of o) & "; " & "comments color=" & my n_WdColorIndex(comments color of o) & "; " & "move from text mark=" & my n_WdMoveFromTextMark(move from text mark of o) & "; " & "move from text color=" & my n_WdColorIndex(move from text color of o) & "; " & "move to text mark=" & my n_WdMoveToTextMark(move to text mark of o) & "; " & "move to text color=" & my n_WdColorIndex(move to text color of o) & "; " & "inserted cell color=" & my n_WdCellColor(inserted cell color of o) & "; " & "deleted cell color=" & my n_WdCellColor(deleted cell color of o) & "; " & "merged cell color=" & my n_WdCellColor(merged cell color of o) & "; " & "split cell color=" & my n_WdCellColor(split cell color of o) & "; " & linefeed
      repeat with p in argv
        set seen to {}
        repeat with i from 1 to (count of documents)
          set end of seen to name of document i
        end repeat
        open POSIX file (p as text)
        set d to missing value
        repeat with i from 1 to (count of documents)
          if seen does not contain (name of document i) then set d to document i
        end repeat
        if d is missing value then
          set out to out & p & ": open produced no document" & linefeed
        else
          set v to view of (active window of d)
          set out to out & (name of d) & ": " & "revisions mode=" & my n_WdRevisionsMode(revisions mode of v) & "; " & "revisions view=" & my n_WdRevisionsView(revisions view of v) & "; " & "show revisions and comments=" & (show revisions and comments of v as text) & "; show insertions and deletions=" & (show insertions and deletions of v as text) & "; show format changes=" & (show format changes of v as text) & "; show comments=" & (show comments of v as text) & "; doc print revisions=" & (print revisions of d as text) & "; doc show revisions=" & (show revisions of d as text) & "; comments=" & ((count of Word comments of d) as text) & linefeed
          close d saving no
        end if
      end repeat
    end tell
  end timeout
  return out
end run
