on splitTabs(t)
  set od to AppleScript's text item delimiters
  set AppleScript's text item delimiters to tab
  set parts to text items of t
  set AppleScript's text item delimiters to od
  return parts
end splitTabs

on logLine(logPath, msg)
  do shell script "printf '%s\\n' " & quoted form of msg & " >> " & quoted form of logPath
end logLine

on restoreAlerts(priorAlerts)
  if priorAlerts is missing value then return
  try
    tell application "Microsoft Word" to set displayAlerts to priorAlerts
  end try
end restoreAlerts

-- `--do-not-close` only: close the documents that appeared after `seen` was
-- taken, newest first, and leave everything that was already open alone.
on closeNew(seen)
  if seen is missing value then return
  tell application "Microsoft Word"
    repeat with i from (count of documents) to 1 by -1
      if seen does not contain (name of document i) then close document i saving no
    end repeat
  end tell
end closeNew

on run argv
  set manifestPath to item 1 of argv
  set logPath to item 2 of argv
  set rows to paragraphs of (read POSIX file manifestPath)
  set priorAlerts to missing value
  tell application "Microsoft Word"
    try
      set priorAlerts to displayAlerts
    end try
    set displayAlerts to false
  end tell
  set okCount to 0
  set failCount to 0
  set emptyStreak to 0
  try
    repeat with r in rows
      set rowText to r as string
      if rowText is not "" then
        set f to my splitTabs(rowText)
        if (count of f) is 4 then
          set itemId to item 1 of f
          set baseP to item 2 of f
          set revP to item 3 of f
          set outP to item 4 of f
          set revisionCount to -1
          set seenBeforeOpen to missing value
          try
            with timeout of 900 seconds
              tell application "Microsoft Word"
                close every document saving no
                set seenBeforeOpen to {}
                repeat with i from 1 to (count of documents)
                  set end of seenBeforeOpen to name of document i
                end repeat
                open POSIX file baseP
                delay 2
                set baseDoc to missing value
                set baseCount to 0
                repeat with i from 1 to (count of documents)
                  set nm to name of document i
                  if nm is not missing value and seenBeforeOpen does not contain nm then
                    set baseDoc to document i
                    set baseCount to baseCount + 1
                  end if
                end repeat
                if baseCount is not 1 then
                  close every document saving no
                  error "open produced " & baseCount & " new documents; refusing to guess"
                end if
                if (count of paragraphs of baseDoc) is 0 then
                  close every document saving no
                  error "base loaded empty (Word could not read it)"
                end if
                set seenBeforeCompare to {}
                set seenCount to count of documents
                repeat with i from 1 to seenCount
                  set end of seenBeforeCompare to name of document i
                end repeat
                compare baseDoc path revP detect format changes true ignore all comparison warnings true add to recent files false
                set cmpDoc to missing value
                set cmpCount to 0
                set docCount to count of documents
                repeat with i from 1 to docCount
                  set dd to document i
                  set nm to name of dd
                  if nm is not missing value and seenBeforeCompare does not contain nm then
                    set cmpDoc to dd
                    set cmpCount to cmpCount + 1
                  end if
                end repeat
                if cmpCount is not 1 then
                  close every document saving no
                  error "compare produced " & cmpCount & " new documents; refusing to guess"
                end if
                try
                  set revisionCount to count of revisions of cmpDoc
                end try
                save as cmpDoc file name outP file format format document
                set pdfP to (text 1 thru -6 of outP) & ".pdf"
                save as cmpDoc file name pdfP file format format PDF
                close every document saving no
              end tell
            end timeout
            set emptyStreak to 0
            set okCount to okCount + 1
            my logLine(logPath, "[ok]" & tab & itemId & tab & revisionCount)
          on error errMsg
            try
              tell application "Microsoft Word" to close every document saving no
            end try
            -- Same poison as word_pdf. A timeout is a final [fail] and stops
            -- the batch. An empty-load streak is [retry], which the log parser
            -- ignores, so those pairs are retried after a recycle.
            if errMsg contains "timed out" then
              set failCount to failCount + 1
              my logLine(logPath, "[fail]" & tab & itemId & tab & errMsg)
              exit repeat
            else if errMsg contains "Connection is invalid" or errMsg contains "isn't running" or errMsg contains ("isn" & (character id 8217) & "t running") then
              my logLine(logPath, "[retry]" & tab & itemId & tab & errMsg)
              exit repeat
            else if errMsg contains "loaded empty" then
              set emptyStreak to emptyStreak + 1
              my logLine(logPath, "[retry]" & tab & itemId & tab & errMsg)
              if emptyStreak ≥ 3 then exit repeat
            else
              set emptyStreak to 0
              set failCount to failCount + 1
              my logLine(logPath, "[fail]" & tab & itemId & tab & errMsg)
            end if
          end try
        end if
      end if
    end repeat
  on error errText
    my restoreAlerts(priorAlerts)
    error errText
  end try
  my restoreAlerts(priorAlerts)
  my logLine(logPath, "[done]" & tab & okCount & tab & failCount)
  return "ok=" & okCount & " fail=" & failCount
end run