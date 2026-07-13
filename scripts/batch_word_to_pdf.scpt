#!/usr/bin/env osascript
on run argv
  set srcDir to POSIX file (item 1 of argv) as alias
  set outDir to item 2 of argv

  set srcPath to (item 1 of argv)
  set outPath to (item 2 of argv)

  tell application "Microsoft Word"
    set displayAlerts to false
  end tell

  set fileList to paragraphs of (do shell script "ls \"" & srcPath & "\" | grep '\\.docx$'")
  set totalCount to count of fileList
  set idx to 0

  repeat with f in fileList
    set idx to idx + 1
    set inFilePath to srcPath & "/" & f
    set outFilePath to outPath & "/" & (do shell script "echo " & quoted form of f & " | sed 's/\\.docx$/.pdf/'")

    try
      tell application "Microsoft Word"
        open inFilePath
        set theDoc to active document
        save as theDoc file name outFilePath file format format PDF
        close theDoc saving no
      end tell
      do shell script "echo '[" & idx & "/" & totalCount & "] OK: " & f & "'"
    on error errMsg
      do shell script "echo '[" & idx & "/" & totalCount & "] FAIL: " & f & " - " & errMsg & "'"
    end try
  end repeat

  tell application "Microsoft Word"
    set displayAlerts to true
  end tell
end run
