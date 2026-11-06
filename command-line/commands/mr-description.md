---
description: Draft the merge request description for the current branch
---
Draft an MR description for the committed work on my current branch. Do not push, open or edit the MR unless I ask.

1. Base branch: the one named in the project AGENTS.md, otherwise `git symbolic-ref --short refs/remotes/origin/HEAD`. Read `git log --oneline <base>..HEAD` and `git diff --stat <base>...HEAD`, and only open individual files where the diff stat leaves the change unclear.
2. Ticket: the JIRA ID from the branch name (`<type>/<JIRA-ID>_<desc>`). Use the real key, e.g. `DEC-1386`.
3. Shape:
   - If the repo has `.gitlab/merge_request_templates/mr_template.md` (or another template the AGENTS.md names), fill **that** template, keeping its headings and checkboxes. Tick only boxes the branch actually evidences; leave the rest unticked and list what is still missing at the end.
   - Otherwise use: `## What` / `## Why` / `## How` / `## Testing` / `## Risk & rollback`, under ~250 words, dropping any section with nothing real in it.
4. Rules for every section:
   - What = the change, not the investigation. Why = the ticket and the one-line reason.
   - How = decisions not visible in the diff: what was deliberately not done, conventions followed.
   - Testing = commands actually run and their results. Never "should work". If nothing was run, say so.
   - Risk & rollback = who is affected and how to revert; for a pipeline/model change, the post-deploy check.
   - Evidence I must add myself (screenshots, query profiles, reconciliation links) becomes a clearly marked `TODO:` line, never invented content.
5. Output the description in one fenced markdown block, then a short "still needed from you" list.

Extra context from me (optional): $ARGUMENTS
