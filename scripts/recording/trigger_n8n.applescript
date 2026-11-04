#!/usr/bin/osascript
-- Execute the active n8n workflow in the visible Chrome tab.
-- The operator must first open the intended workflow and focus its tab.
on run argv
    if (count of argv) < 1 then error "missing JavaScript file"
    set jsPath to POSIX path of (item 1 of argv)
    set jsCode to read POSIX file jsPath
    tell application "Google Chrome"
        if (count of windows) = 0 then error "Chrome has no window"
        execute front window's active tab javascript jsCode
    end tell
end run
