---
description: Remove one or more Claude Code sessions (all local copies) by id, with confirmation
---
Session ids (8+ char prefixes work): $ARGUMENTS

1. If no ids were given, run `python3 ~/.claude/scripts/sessions.py list` and ask me which session(s) to delete.
2. Run `python3 ~/.claude/scripts/sessions.py delete <ids>` (dry run) and show me what will be removed.
3. Ask me to confirm. Only if I confirm, re-run with `--yes`.
4. Report what was moved and that `python3 ~/.claude/scripts/sessions.py restore` undoes it. A session updated in the last 30 minutes is refused automatically (it may be the one you are in).

Never edit or delete session files by hand.
