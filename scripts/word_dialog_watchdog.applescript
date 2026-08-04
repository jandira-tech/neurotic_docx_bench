#!/usr/bin/env osascript
-- Dismiss Microsoft Word's modal dialogs so an unattended batch never blocks.
--
-- argv: 1=log path  [2=poll seconds, default 2]
--
-- `set displayAlerts to false` suppresses Word's *scriptable* alerts, but NOT
-- hard failure dialogs raised by the file loader — e.g.
--
--   "Word experienced an error trying to open the file.
--    Try these suggestions. * Check the file permissions ..."
--
-- which the SuperDoc pool triggers on documents Word cannot parse. That dialog
-- blocks the Apple event indefinitely: the batch hangs and a human has to click
-- OK. This watchdog polls Word's UI and clicks the dismiss button itself, so a
-- poison fixture costs one logged failure instead of one human interruption.
--
-- Requires the Accessibility (System Events) grant, which is separate from the
-- Apple-events grant for Word. Both are one-time.
--
-- Run it in the background alongside the batch; the driver kills it on exit.

on logLine(logPath, msg)
	do shell script "printf '%s\\n' " & quoted form of msg & " >> " & quoted form of logPath
end logLine

-- Click the most conservative dismiss button available. Only ever presses
-- buttons that acknowledge or cancel — never one that could confirm a
-- destructive or format-changing action.
on dismiss(uiElement, logPath)
	set clicked to ""
	repeat with wanted in {"OK", "Ok", "Cancel", "Close", "Don't Save", "No"}
		if clicked is "" then
			try
				tell application "System Events"
					if exists button (wanted as string) of uiElement then
						click button (wanted as string) of uiElement
						set clicked to wanted as string
					end if
				end tell
			end try
		end if
	end repeat
	if clicked is not "" then
		my logLine(logPath, "[dialog] dismissed via " & clicked)
		return true
	end if
	return false
end dismiss

on run argv
	set logPath to item 1 of argv
	set pollSecs to 2
	if (count of argv) >= 2 then set pollSecs to (item 2 of argv) as number

	repeat
		try
			tell application "System Events"
				if exists process "Microsoft Word" then
					tell process "Microsoft Word"
						-- Alerts attached to a document window arrive as sheets.
						repeat with w in windows
							try
								if exists sheet 1 of w then
									my dismiss(sheet 1 of w, logPath)
								end if
							end try
						end repeat
						-- Alerts with no document open arrive as their own window.
						repeat with w in windows
							try
								if (subrole of w is "AXDialog") or (description of w is "alert") then
									my dismiss(w, logPath)
								end if
							end try
						end repeat
					end tell
				end if
			end tell
		end try
		delay pollSecs
	end repeat
end run
