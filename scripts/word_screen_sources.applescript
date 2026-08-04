#!/usr/bin/env osascript
-- Pre-flight screen: can Microsoft Word actually READ each staged source?
--
-- argv: 1=staged source dir  2=log path
-- Log row: <filename> <TAB> <paragraph count | ERROR:msg>
-- Prints "POISON <name>" and STOPS as soon as one document fails.
--
-- Why this exists, and why it stops instead of continuing:
--
-- The SuperDoc pool contains documents Word opens without complaint but loads
-- as EMPTY (`count of paragraphs` = 0 — impossible for a real document, which
-- always has at least one). Using one as a compare target fails with a
-- thoroughly misleading error reported against the *base* document:
--   document "<base>" doesn't understand the "compare" message
--
-- The dangerous part is what happens next: a single poison document leaves
-- Word degraded for the REST OF THE SESSION. Every subsequent open returns an
-- empty document, silently — no error, no dialog. Screening 223 files in one
-- Word session reported 213 as unreadable when only a handful actually are;
-- the other 203 were collateral damage from file #11.
--
-- So the only safe contract is: stop at the first failure and let the driver
-- restart Word. The log makes this resumable, so each restart costs ~10s and
-- makes guaranteed progress.

on logLine(logPath, msg)
	do shell script "printf '%s\\n' " & quoted form of msg & " >> " & quoted form of logPath
end logLine

on run argv
	set srcDir to item 1 of argv
	set logPath to item 2 of argv

	set fileList to paragraphs of (do shell script "ls " & quoted form of srcDir & " | grep '\\.docx$' || true")

	tell application "Microsoft Word"
		set displayAlerts to false
	end tell

	repeat with f in fileList
		set fname to f as string
		if fname is not "" then
			set alreadyDone to false
			try
				do shell script "grep -q ^" & quoted form of (fname & tab) & " " & quoted form of logPath
				set alreadyDone to true
			end try

			if not alreadyDone then
				set paraCount to missing value
				set failMsg to ""
				try
					with timeout of 60 seconds
						tell application "Microsoft Word"
							open (srcDir & "/" & fname) confirm conversions false add to recent files false
							set paraCount to count of paragraphs of document 1
							close every document saving no
						end tell
					end timeout
				on error errMsg
					set failMsg to errMsg
				end try

				-- Healthy = a POSITIVE INTEGER. Word signals an unreadable
				-- document three different ways and all three are poison: a
				-- thrown error, a count of 0, and `missing value` (the count
				-- simply never comes back). An earlier version tested only for
				-- 0, so the `missing value` cases were logged as healthy and
				-- never triggered a restart — which means every file screened
				-- after one of them was measured on a possibly-degraded Word.
				set healthy to false
				try
					if (paraCount as integer) > 0 then set healthy to true
				end try

				if healthy then
					my logLine(logPath, fname & tab & (paraCount as string))
				else
					if failMsg is not "" then
						my logLine(logPath, fname & tab & "ERROR:" & failMsg)
					else
						my logLine(logPath, fname & tab & "BAD:" & (paraCount as string))
					end if
					return "POISON " & fname
				end if
			end if
		end if
	end repeat

	my logLine(logPath, "__SCREEN_DONE__" & tab & "0")
	return "SCREEN_DONE"
end run
