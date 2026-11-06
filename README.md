# claude-chat-manager

Two independent tools for managing terminal AI chat history, kept in one repo.
They are **separate on purpose** - neither depends on the other.

- **`chat-manager-gui/`** - the original **Claude Chat Manager**: a terminal UI (TUI)
  for browsing, filtering, renaming and deleting Claude Code conversations. A
  compiled .NET app, also shipped as a macOS `.app`.
- **`command-line/`** - the **Claude Code session toolkit**: a Python `sessions.py`
  engine plus Claude Code slash commands (`/sessions`, `/clean-sessions`,
  `/delete-session`, ...) and a `claude-manager` shell picker. Runs both inside
  Claude Code and from the CLI.

## Quick start

| I want to... | Go to |
|---|---|
| Browse/delete chats in a TUI | [chat-manager-gui/README.md](chat-manager-gui/README.md) |
| Manage sessions from Claude Code or the shell | [command-line/README.md](command-line/README.md) |

## Layout

```
chat-manager-gui/   # TUI app (C#/.NET): source + macOS .app + published binary
command-line/       # Python sessions.py + Claude Code commands + shell integration
```
