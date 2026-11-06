---
description: Write a handoff note so a fresh session can continue this work
---
<!-- Adapted from mattpocock/skills `handoff` (MIT). -->
Write a handoff note summarising this conversation so a new session (after `/clear`) can continue without the history.

Save it to `~/dev/.handoffs/<project>/<YYYY-MM-DD>_<branch-or-topic>.md` (create the folder if needed; replace `/` in branch names with `-`). Use the repo name for `<project>` (e.g. `basename "$(git rev-parse --show-toplevel)"`, or the current directory name if this isn't a git repo). Keep it outside any repository.

Contents, kept under ~40 lines:
- **Goal**: the task in one or two sentences, with the JIRA ID if there is one.
- **State**: what is done, what is in progress, what is blocked.
- **Decisions**: choices made and why, especially anything the next session might otherwise redo or reverse.
- **Next steps**: an ordered list the next session can start on immediately.
- **References**: files, commits, plans, MRs and session ids by path, hash or URL. Point to them; do not copy their content.
- **Suggested commands/skills** for the next session (e.g. `/branch-review`, `/mr-description`).

Remove secrets, tokens, passwords and personal data. Then tell me the file path and the one line to start the next session with: `Continue from ~/dev/.handoffs/<project>/<file>`.

What the next session will focus on (optional): $ARGUMENTS
