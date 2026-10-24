#!/bin/sh
# Runs the Claude Chat Manager TUI in the Terminal window Terminal.app opens.

DIR="$(cd "$(dirname "$0")" && pwd)"

BIN=""
for candidate in "$DIR/ClaudeChatManager" "$HOME/bin/ClaudeChatManager"; do
	if [ -x "$candidate" ]; then
		BIN="$candidate"
		break
	fi
done

if [ -z "$BIN" ]; then
	printf '%s\n\n' "ClaudeChatManager binary not found."
	printf '%s\n' "Download it from:"
	printf '  %s\n\n' "https://github.com/jitbit/claude-chat-manager/releases"
	printf '%s\n' "Then place it in one of these locations:"
	printf '  %s\n' "$DIR/ClaudeChatManager"
	printf '  %s\n' "$HOME/bin/ClaudeChatManager"
	printf '\n%s\n\n' "and make it executable:  chmod +x <path>"
	printf '%s' "Press Return to close."
	read -r _
	exit 1
fi

if xattr -p com.apple.quarantine "$BIN" >/dev/null 2>&1; then
	printf '%s\n\n' "macOS quarantined this binary because it was downloaded with a browser."
	printf '%s\n\n' "Remove the quarantine flag once, then relaunch:"
	printf '  xattr -d com.apple.quarantine "%s"\n\n' "$BIN"
	printf '%s' "Press Return to close."
	read -r _
	exit 1
fi

"$BIN"
status=$?

# A clean exit (Quit) closes this Terminal tab, even when the profile is
# configured to keep the window open. Non-zero exits hold the window open
# so the failure message is readable.
close_terminal_tab() {
	target_tty="$1"
	osascript <<APPLESCRIPT
tell application "Terminal"
	repeat with w in windows
		repeat with t in tabs of w
			if (tty of t) is "$target_tty" then
				try
					close t
				on error
					close w saving no
				end try
				return
			end if
		end repeat
	end repeat
end tell
error "Claude Chat Manager tab not found" number 1
APPLESCRIPT
}

close_terminal_later() {
	# Detach from the tab, wait for this shell to exit, then close the tab.
	# No process is left in the tab, so Terminal doesn't ask to terminate it.
	nohup /usr/bin/python3 - "$1" >/dev/null 2>&1 <<'PYTHON' &
import os, signal, sys, time

signal.signal(signal.SIGHUP, signal.SIG_IGN)

try:
	os.setsid()
except OSError:
	pass

deadline = time.time() + 3.0
while os.getppid() != 1 and time.time() < deadline:
	time.sleep(0.05)

time.sleep(0.15)

script = """tell application "Terminal"
	repeat with w in windows
		repeat with t in tabs of w
			if (tty of t) is "%s" then
				try
					close t
				on error
					close w saving no
				end try
				return
			end if
		end repeat
	end repeat
end tell
error "Claude Chat Manager tab not found" number 1
""" % sys.argv[1]

os.execv("/usr/bin/osascript", ["osascript", "-e", script])
PYTHON
}

if [ "$status" -eq 0 ]; then
	if [ -t 1 ]; then
		tty_path="$(tty 2>/dev/null)"
		if [ -n "$tty_path" ]; then
			if [ -x /usr/bin/python3 ]; then
				close_terminal_later "$tty_path"
				sleep 0.2
			elif ! close_terminal_tab "$tty_path"; then
				printf '\n%s\n' "Could not close the Terminal tab automatically."
				printf '%s' "Press Return to close."
				read -r _
			fi
		fi
	fi
else
	printf '\n%s\n' "Claude Chat Manager exited ($status)."
	printf '%s' "Press Return to close."
	read -r _
fi

exit "$status"
