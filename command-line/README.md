# command-line

Claude Code session toolkit - a Python engine (`sessions.py`) plus Claude Code slash commands and a shell picker. Works two ways:

- **Inside Claude Code**: `/sessions`, `/clean-sessions`, `/delete-session`, `/handoff`, `/branch-review`, `/mr-description`
- **From the CLI**: `claude-manager` (an fzf picker) and `ccs` (the script directly)

Independent of `chat-manager-gui/`.

## Requirements
- `python3`
- `fzf` (for the `claude-manager` picker)
- `claude` (Claude Code CLI, for resuming)

## Install (one command)
```sh
./command-line/install.sh            # installs script + commands into ~/.claude
./command-line/install.sh --shell    # also adds the shell integration to ~/.zshrc
```
What it installs:
- `~/.claude/scripts/sessions.py`
- `~/.claude/commands/*.md` (the slash commands)
- with `--shell`: `~/.claude/shell/claude.zsh` and a `source` line appended to `~/.zshrc`

Reload your shell afterwards (`source ~/.zshrc` or open a new terminal).

## Usage
In Claude Code:
- `/sessions` - markdown table of sessions grouped by project
- `/clean-sessions` - dry-run then remove empty sessions
- `/delete-session <id>` - dry-run then move to trash
- `/handoff` - write a handoff note to `~/dev/.handoffs/<project>/`
- `/branch-review`, `/mr-description` - git helpers (generic)

From the CLI:
- `claude-manager` - two-stage fzf picker: pick a **project** (or **All projects**
  to search across everything), then a **session**. Times are relative ("2h ago").
  ENTER resumes from the session's project dir (in a subshell, so your shell's cwd
  is unchanged afterwards), CTRL-R renames, CTRL-X deletes (dry-run + confirm),
  CTRL-A toggles multiple selections, ESC goes back a level. Untitled sessions show
  their first message as the title.
- `ccs projects [--with-all] [--format text|tsv]` - list projects (name, dir, session count)
- `ccs list [--all] [--project NAME] [--project-dir DIR] [--format text|md|tsv] [--limit N|--full] [--full-ids]`
- `ccs preview <id>` - metadata + first messages (what the picker shows on the right)
- `ccs show <id>` - short details summary
- `ccs dir <id>` - print the session's working directory
- `ccs rename <id> <new title...>` - set/replace the session's custom title
- `ccs clean-empty [--yes]`
- `ccs delete <id...> [--yes] [--force]`
- `ccs restore`

## Storage & safety
- Reads `~/.claude/projects/<project>/<session-id>.jsonl` (+ companion dir: `subagents/`, `custom-title.json`)
- Deletes **move** files to `~/.claude/sessions_trash/` - undo with `ccs restore`
- `clean-empty` / `delete` are dry runs unless `--yes`
- A session updated in the last 30 min is refused (it may be the one you are in)

## On a new machine
1. Ensure `python3`, `fzf`, and `claude` are installed (`brew install fzf`; install Claude Code).
2. Clone this repo.
3. Run `./command-line/install.sh --shell`, then reload the shell.

## Layout
```
scripts/sessions.py     # the engine
commands/*.md           # Claude Code slash commands
shell/claude.zsh        # claude-manager() + ccs alias
install.sh              # installer
```
