---
description: Review the current feature branch against the repo's default branch
---
Review my current branch against the repo's base branch.

1. Determine the base: use the base named in the project AGENTS.md if present, otherwise `git symbolic-ref --short refs/remotes/origin/HEAD` (e.g. `origin/qa`, `origin/main`). State which base you're using.
2. `git fetch origin`, then summarise `git log --oneline <base>..HEAD` and `git diff --stat <base>...HEAD`.
3. Take the ticket ID from the branch name and state the apparent goal of the change.
4. If it's a dbt project, use `fdbt` to list downstream models and existing tests for each changed model.
5. Flag: logic bugs, missing tests, risky incremental/snapshot/infra changes, convention breaks from AGENTS.md, and changes unrelated to the ticket.
6. Finish with: verdict (ready / needs changes) and a prioritised issue list with file:line. Then offer to run `/mr-description` rather than drafting MR text here.

Do not modify files or commit. Extra focus from me (optional): $ARGUMENTS
