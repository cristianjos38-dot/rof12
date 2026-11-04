#!/usr/bin/osascript
-- Focuses existing Terminal and Chrome windows without embedding private URLs.
-- Usage: osascript focus_windows.applescript "$ROF12_GITHUB_URL" "$ROF12_N8N_URL"
on run argv
    set githubURL to ""
    set n8nURL to ""
    if (count of argv) ≥ 1 then set githubURL to item 1 of argv
    if (count of argv) ≥ 2 then set n8nURL to item 2 of argv

    tell application "Terminal" to activate
    delay 0.3
    tell application "Google Chrome"
        activate
        if (count of windows) = 0 then return
        set targetWindow to front window
        repeat with candidateWindow in windows
            repeat with candidateTab in tabs of candidateWindow
                set tabURL to URL of candidateTab
                if githubURL is not "" and tabURL contains githubURL then
                    set active tab index of candidateWindow to (index of candidateTab)
                    set targetWindow to candidateWindow
                else if n8nURL is not "" and tabURL contains n8nURL then
                    set active tab index of candidateWindow to (index of candidateTab)
                    set targetWindow to candidateWindow
                end if
            end repeat
        end repeat
        set index of targetWindow to 1
    end tell
end run
