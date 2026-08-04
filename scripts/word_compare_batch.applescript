#!/usr/bin/env osascript
-- Unattended Microsoft Word "Compare Documents" batch.
--
-- argv: 1=manifest.tsv  2=log path  [3=start index, 1-based]  [4=count, 0=all]
-- Manifest row: pair_id <TAB> base <TAB> next <TAB> out   (absolute POSIX paths)
--
-- EVERY path in the manifest MUST live inside Word's group container
-- (~/Library/Group Containers/UBF8T346G9.Office/...). Word for Mac is
-- sandboxed: a path outside that container raises a "Grant Access" dialog for
-- each file it touches — three clicks for a single pair, ~1200 for the corpus.
-- Inside the container Word needs no grant at all. scripts/word_compare_driver.sh
-- does the staging; do not point this script at repo paths.
--
-- Safety: this closes every open Word document after each pair, so the driver
-- asserts Word has zero documents open before starting. Never run it while a
-- human has unsaved work in Word.

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

on run argv
	set manifestPath to item 1 of argv
	set logPath to item 2 of argv
	set startIdx to 1
	if (count of argv) >= 3 then set startIdx to (item 3 of argv) as integer
	set wantCount to 0
	if (count of argv) >= 4 then set wantCount to (item 4 of argv) as integer

	set rows to paragraphs of (read POSIX file manifestPath)

	tell application "Microsoft Word"
		set displayAlerts to false
	end tell

	set idx to 0
	set doneCount to 0
	set okCount to 0
	set failCount to 0

	repeat with r in rows
		set rowText to r as string
		if rowText is not "" then
			set idx to idx + 1
			if idx >= startIdx then
				if wantCount > 0 and doneCount >= wantCount then exit repeat
				set fieldsList to my splitTabs(rowText)
				if (count of fieldsList) = 4 then
					set pairId to item 1 of fieldsList
					set baseP to item 2 of fieldsList
					set nextP to item 3 of fieldsList
					set outP to item 4 of fieldsList
					set doneCount to doneCount + 1

					-- Idempotent resume safety net. The driver already filters the
					-- manifest down to outstanding pairs before each invocation,
					-- so this normally matches nothing; it exists in case the log
					-- is lost. Skips are NOT logged: they would otherwise dwarf
					-- the real entries and make "the log grew" a false signal of
					-- progress for the driver's stall detection.
					if (do shell script "test -s " & quoted form of outP & " && echo yes || echo no") is "yes" then
						set doneCount to doneCount - 1
					else
						set failMsg to ""
						set paraCount to missing value
						try
							with timeout of 300 seconds
								tell application "Microsoft Word"
									open baseP confirm conversions false add to recent files false
									set baseDoc to document 1
									set baseName to name of baseDoc
									-- Health check BEFORE comparing. An unreadable base
									-- yields a document with no paragraphs, and comparing
									-- against it fails with an error naming the wrong file.
									set paraCount to count of paragraphs of baseDoc

									-- Signature verified against this machine's sdef (Word 16.98).
									-- `target` omitted => the result opens as a NEW document.
									compare baseDoc path nextP ignore all comparison warnings true add to recent files false

									-- Identify the result by exclusion rather than trusting
									-- `active document`: if compare silently produced nothing,
									-- `active document` is still the BASE, and saving that as
									-- the redline would ship a change-free document that looks
									-- valid and scores as garbage.
									-- Index the documents explicitly: `repeat with d in documents`
									-- makes AppleScript send `count` to `every document`, which
									-- this Word build rejects outright.
									set cmpDoc to missing value
									set docCount to count of documents
									repeat with i from 1 to docCount
										set dd to document i
										if (name of dd) is not baseName then set cmpDoc to dd
									end repeat
									if cmpDoc is missing value then error "compare produced no result document"

									-- `format document` is WdSaveFormat 12 (wdFormatXMLDocument,
									-- i.e. .docx). The legacy binary .doc format is the
									-- separate `format document97` — do not confuse them.
									save as cmpDoc file name outP file format format document
									-- After EVERY pair, success or failure: Word degrades
									-- linearly with open documents and eventually wedges.
									close every document saving no
								end tell
							end timeout
						on error errMsg
							set failMsg to errMsg
							try
								tell application "Microsoft Word" to close every document saving no
							end try
						end try

						set baseHealthy to false
						try
							if (paraCount as integer) > 0 then set baseHealthy to true
						end try

						if failMsg is "" then
							set okCount to okCount + 1
							my logLine(logPath, "[ok] " & pairId)
						else
							set failCount to failCount + 1
							my logLine(logPath, "[fail] " & pairId & " :: " & failMsg)
							-- Stop and let the driver recycle Word. A failed pair means
							-- Word may now be in the degraded state where every later
							-- open returns an empty document with no error at all —
							-- carrying on would silently corrupt the rest of the batch.
							return "POISON " & pairId
						end if

						if not baseHealthy then
							my logLine(logPath, "[warn] " & pairId & " :: base reported no paragraphs")
							return "POISON " & pairId
						end if
					end if
				end if
			end if
		end if
	end repeat

	tell application "Microsoft Word"
		set displayAlerts to true
	end tell

	my logLine(logPath, "[done] processed=" & doneCount & " ok=" & okCount & " fail=" & failCount)
	return "processed=" & doneCount & " ok=" & okCount & " fail=" & failCount
end run
