# Claude Chat Manager (GUI / TUI)

A terminal UI for browsing and deleting [Claude Code](https://docs.anthropic.com/en/docs/claude-code) chat history. Claude Code stores each conversation as JSONL under `~/.claude/projects/`; this app presents them grouped by project so you can find, inspect, rename and delete sessions.

Standalone tool - it does **not** use `command-line/`; the two are independent.

## What you can do
- Browse conversations grouped by project
- Filter by title / first message / session id (type to filter; Esc clears)
- View details: title, id, date, message count, first message, file, continuation info
- Rename a conversation (writes Claude's own `custom-title` sidecar so the name sticks)
- Delete a conversation (with confirmation; removes the whole session incl. continuation files)
- Empty projects (no conversations left) are hidden from the list

## Requirements
- [.NET 10 SDK](https://dotnet.microsoft.com/) to build from source (not needed for the prebuilt binary / `.app`).

## Prebuilt (no build)
- macOS: double-click `Claude Chat Manager.app`, or run `./publish/ClaudeChatManager`
- Windows builds are produced by CI on release.

If Gatekeeper blocks the Mac app: System Settings -> Privacy & Security -> "Open anyway".

## Build from source (run from the repo root)
```sh
dotnet build chat-manager-gui/ClaudeChatManager/ClaudeChatManager.csproj -c Release
```

Run from source:
```sh
dotnet run --project chat-manager-gui/ClaudeChatManager
```

## Publish a native (AOT) binary and refresh the macOS app
```sh
# build a native arm64 binary into publish/
dotnet publish chat-manager-gui/ClaudeChatManager/ClaudeChatManager.csproj -c Release -r osx-arm64 -o chat-manager-gui/publish

# copy the fresh binary into the app bundle
cp chat-manager-gui/publish/ClaudeChatManager "chat-manager-gui/Claude Chat Manager.app/Contents/Resources/ClaudeChatManager"
```

## On a new MacBook
1. Install the [.NET 10 SDK](https://dotnet.microsoft.com/) (only if building from source).
2. Clone this repo.
3. Run the prebuilt binary/app, **or** rebuild with the `dotnet publish` command above.
4. If the app is blocked by Gatekeeper, allow it in System Settings -> Privacy & Security.

## Keys
| Key | Action |
|---|---|
| Up / Down | move selection |
| PgUp / PgDn | page |
| Home / End | first / last |
| Enter | view conversation details |
| type to filter | filter list (Esc clears) |
| Ctrl+R | rename selected |
| Delete / Backspace | delete selected (confirm) |
| Esc | back / quit |

## Troubleshooting
- `error MSB4242 ... WorkloadSdkResolver` (seen with some .NET 10 patch SDKs on macOS):
  build/publish with the workload resolver disabled by adding
  `-p:MSBuildEnableWorkloadResolver=false` to the `dotnet build` / `dotnet publish` command.
