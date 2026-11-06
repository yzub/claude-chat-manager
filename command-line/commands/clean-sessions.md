---
description: Remove empty (0-message) Claude Code sessions, with confirmation
---
1. Run `python3 ~/.claude/scripts/sessions.py clean-empty $ARGUMENTS` (dry run) and show me the list of empty sessions it found, grouped by project.
2. Ask me to confirm. Only if I confirm, run `python3 ~/.claude/scripts/sessions.py clean-empty $ARGUMENTS --yes`.
3. Report how many were moved and that they can be restored with `python3 ~/.claude/scripts/sessions.py restore`.

Never delete non-empty sessions or edit session files by hand.
