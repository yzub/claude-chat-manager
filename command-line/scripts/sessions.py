#!/usr/bin/env python3
"""List Claude Code sessions grouped by project, and clean up empty ones.

usage:
  sessions.py list [--all] [--project NAME] [--project-dir DIR] [--no-project] [--format text|md|tsv]
                   [--limit N | --full] [--full-ids]   # --all includes subagents
  sessions.py projects [--with-all] [--format text|tsv]   # one row per project (name, dir, count)
  sessions.py preview ID [--latest]   # rich preview: metadata + messages
  sessions.py dir ID             # print the session's working directory
  sessions.py show ID            # details + first message
  sessions.py clean-empty [--yes]
  sessions.py delete ID-OR-PREFIX [...] [--yes] [--force]
  sessions.py rename ID NEW TITLE...   # set/replace the session's custom title
  sessions.py restore

Sessions are read from ~/.claude/projects/<project>/<session-id>.jsonl, plus an
optional companion directory <session-id>/ (subagents, custom title).

clean-empty/delete are dry runs unless --yes. Removed files are moved to
~/.claude/sessions_trash/ and can be restored with the `restore` command.
"""
import argparse
import glob
import json
import os
import shutil
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

ROOT = os.path.expanduser("~/.claude/projects")
TRASH = os.path.expanduser("~/.claude/sessions_trash")
ACTIVE_GRACE = timedelta(minutes=30)  # never touch sessions updated this recently


def parse_ts(ts):
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def rel_time(ts):
    dt = parse_ts(ts)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return "-"
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    if secs < 0:
        return "now"
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    if secs < 86400 * 7:
        return f"{int(secs // 86400)}d ago"
    return dt.strftime("%b %d")


def short(text, width):
    return text if len(text) <= width else text[: width - 1] + "\u2026"


def fmt_slug(slug):
    return " ".join(w[:1].upper() + w[1:] for w in slug.split("-") if w)


def read_custom_title(companion):
    try:
        with open(os.path.join(companion, "custom-title.json")) as f:
            return json.load(f).get("customTitle") or ""
    except (OSError, json.JSONDecodeError):
        return ""


def write_custom_title(path, title):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"customTitle": title}, f)
    os.replace(tmp, path)


def append_custom_title_event(path, session_id, title):
    line = json.dumps({"type": "custom-title", "customTitle": title, "sessionId": session_id})
    needs_nl = False
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                needs_nl = f.read(1) != b"\n"
    except OSError:
        needs_nl = False
    with open(path, "a") as f:
        if needs_nl:
            f.write("\n")
        f.write(line + "\n")


def first_user_text(content):
    if isinstance(content, str):
        return "" if content.lstrip().startswith("<") else content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                s = block.get("text") or ""
                if s.strip() and not s.lstrip().startswith("<"):
                    return s
    return ""


def message_text(d):
    """Best-effort plain text of a user/assistant message, skipping system <tags>."""
    content = (d.get("message") or {}).get("content")
    if isinstance(content, str):
        return "" if content.lstrip().startswith("<") else content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                s = block.get("text") or ""
                if s.strip() and not s.lstrip().startswith("<"):
                    parts.append(s)
        return "\n".join(parts)
    return ""


def scan_session(path):
    session_id = os.path.splitext(os.path.basename(path))[0]
    companion = os.path.splitext(path)[0]
    cwd = branch = first_ts = last_ts = ""
    msgs = 0
    first_msg = ai_title = custom_title = slug = continued_in = ""
    try:
        with open(path, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = d.get("type")
                if t in ("user", "assistant"):
                    msgs += 1
                ts = d.get("timestamp")
                if ts:
                    first_ts = first_ts or ts
                    last_ts = ts
                cwd = d.get("cwd") or cwd
                branch = d.get("gitBranch") or branch
                session_id = d.get("sessionId") or session_id
                if d.get("aiTitle"):
                    ai_title = d["aiTitle"]
                if d.get("customTitle"):
                    custom_title = d["customTitle"]
                if d.get("slug") and not slug:
                    slug = d["slug"]
                if d.get("continuedInSessionId"):
                    continued_in = d["continuedInSessionId"]
                if not first_msg and t == "user":
                    text = first_user_text((d.get("message") or {}).get("content"))
                    if text.strip():
                        first_msg = " ".join(text.split())
    except OSError:
        return None

    folder = os.path.basename(os.path.dirname(path))
    if cwd:
        project_dir = cwd
    else:
        project_dir = "/" + folder.lstrip("-").replace("-", "/")
    project = os.path.basename(project_dir.rstrip("/")) or project_dir

    fallback = short(first_msg, 60) if first_msg else (session_id[:8] if len(session_id) > 8 else session_id)
    title = (read_custom_title(companion) or custom_title or ai_title
             or (fmt_slug(slug) if slug else "")
             or fallback)
    updated = last_ts or datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat()
    return {
        "path": path,
        "id": session_id,
        "title": title,
        "project": project,
        "project_dir": project_dir,
        "branch": branch,
        "msgs": msgs,
        "type": "main",
        "updated": updated,
        "created": first_ts,
        "first_msg": short(first_msg, 120),
        "continued_in": continued_in,
    }


def load_sessions(include_subagents=False):
    sessions = []
    for path in glob.glob(os.path.join(ROOT, "*", "*.jsonl")):
        s = scan_session(path)
        if s:
            sessions.append(s)
    if include_subagents:
        for path in glob.glob(os.path.join(ROOT, "*", "*", "subagents", "*.jsonl")):
            s = scan_session(path)
            if s:
                s["type"] = "subagent"
                # a subagent file reuses its parent's sessionId; key it by filename instead
                s["id"] = os.path.splitext(os.path.basename(path))[0]
                sessions.append(s)
    return sessions


def dedupe(sessions):
    """One row per session id: the most recently updated copy, with a copy count."""
    by_id = defaultdict(list)
    for s in sessions:
        by_id[s["id"]].append(s)
    result = []
    for copies in by_id.values():
        best = max(copies, key=lambda c: (parse_ts(c["updated"]), c["msgs"]))
        result.append(dict(best, copies=len(copies)))
    return result


def is_recent(s):
    return datetime.now(timezone.utc) - parse_ts(s["updated"]) < ACTIVE_GRACE


def companion_dir(s):
    return os.path.splitext(s["path"])[0]


def is_empty(s):
    if s["type"] != "main" or s["msgs"] != 0 or is_recent(s):
        return False
    d = companion_dir(s)
    return not (os.path.isdir(d) and os.listdir(d))


def display_title(s, width=36):
    return short((s["title"] or "(untitled)").replace("|", "/"), width)


def display_branch(s, width=32):
    return short(s["branch"] or "-", width)


def flags(s):
    out = []
    if is_empty(s):
        out.append("empty")
    if s["type"] != "main":
        out.append(s["type"])
    if s.get("copies", 1) > 1:
        out.append(f"{s['copies']}x")
    if s.get("continued_in"):
        out.append("continued")
    return ", ".join(out)


def cmd_list(args):
    groups = defaultdict(list)
    for s in dedupe(load_sessions(args.all)):
        if s["type"] != "main" and not args.all:
            continue
        if args.project and args.project.lower() not in s["project"].lower():
            continue
        if args.project_dir and args.project_dir != "*" and s["project_dir"] != args.project_dir:
            continue
        groups[(s["project"], s["project_dir"])].append(s)
    ordered = sorted(groups.items(), key=lambda kv: max(parse_ts(i["updated"]) for i in kv[1]), reverse=True)
    limit = None if args.full else args.limit
    md = args.format == "md"
    id_len = 36 if args.full_ids else 8

    if args.format == "tsv":
        rows = [s for _, items in ordered for s in items]
        title_w = 90 if args.no_project else 60
        for s in sorted(rows, key=lambda i: parse_ts(i["updated"]), reverse=True):
            flag = flags(s)
            tstr = f"{rel_time(s['updated']):<8}"
            bstr = f"{short(s['branch'] or '-', 18):<18}"
            mstr = f"{s['msgs']:>5}"
            title = display_title(s, title_w) + (f" [{flag}]" if flag else "")
            if args.no_project:
                line = f"{tstr} | {bstr} | {title}"
            else:
                line = f"{tstr} | {short(s['project'], 20):<20} | {mstr} | {title}"
            print(f"{s['id']}\t{line}")
        return
    totals = []
    for (project, project_dir), items in ordered:
        items.sort(key=lambda i: parse_ts(i["updated"]), reverse=True)
        shown = items[:limit]
        empty = sum(1 for i in items if is_empty(i))
        totals.append((project, len(items), empty))
        if md:
            print(f"\n**{project}** `{project_dir}`\n")
            print("| Updated | Msgs | Title | Branch | ID |\n|---|---|---|---|---|")
        else:
            print(f"\n## {project}  ({project_dir})  - {len(items)} sessions")
        for s in shown:
            updated = s["updated"][5:16].replace("T", " ") or "-"
            sid, flag = s["id"][:id_len], flags(s)
            title = display_title(s) + (f" [{flag}]" if flag else "")
            if md:
                print(f"| {updated} | {s['msgs']} | {title} | {display_branch(s)} | `{sid}` |")
            else:
                print(f"  {updated}  {s['msgs']:>4}  {title}  [{display_branch(s)}]  {sid}")
        if len(items) > len(shown):
            more = f"+{len(items) - len(shown)} older (use --full or --project {project})"
            print(f"\n_{more}_" if md else f"  {more}")

    n_sessions = sum(t[1] for t in totals)
    n_empty = sum(t[2] for t in totals)
    if md:
        print("\n| Project | Sessions | Empty |\n|---|---|---|")
        for project, count, empty in totals:
            print(f"| {project} | {count} | {empty} |")
        print(f"| **Total** | **{n_sessions}** | **{n_empty}** |")
        print("\nReopen with `claude --resume <id>` (id prefixes work with `delete`).")
    else:
        print(f"\nTotal: {n_sessions} sessions in {len(totals)} projects, {n_empty} empty.")


def related_paths(s):
    base = os.path.splitext(s["path"])[0]
    out = [s["path"]]
    if os.path.isdir(base):
        out.append(base)
    return out


def move_to_trash(sessions):
    for s in sessions:
        for p in related_paths(s):
            dest = os.path.join(TRASH, os.path.relpath(p, ROOT))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            elif os.path.exists(dest):
                os.remove(dest)
            shutil.move(p, dest)


def cmd_clean(args):
    # A session is only removed if every copy of it is empty.
    sessions = load_sessions(False)
    non_empty_ids = {s["id"] for s in sessions if not is_empty(s)}
    empty = [s for s in sessions if is_empty(s) and s["id"] not in non_empty_ids]
    if not empty:
        print("No empty sessions found.")
        return
    for s in empty:
        print(f"  {s['project']:<28} {s['updated'][:16]}  {s['id']}")
    if not args.yes:
        print(f"\n{len(empty)} empty sessions. Dry run - re-run with --yes to remove.")
        return
    move_to_trash(empty)
    print(f"\nMoved {len(empty)} empty sessions to trash (run 'restore' to undo).")


def cmd_delete(args):
    sessions = load_sessions(False)
    copies, missing = [], []
    for wanted in args.ids:
        if len(wanted) < 6:
            print(f"  id prefix too short (min 6 chars): {wanted}")
            return 1
        matched_ids = {s["id"] for s in sessions if s["id"].startswith(wanted)}
        if len(matched_ids) > 1:
            print(f"  ambiguous prefix {wanted}: {', '.join(sorted(i[:12] for i in matched_ids))}")
            return 1
        if not matched_ids:
            missing.append(wanted)
        copies += [s for s in sessions if s["id"] in matched_ids]
    for m in sorted(missing):
        print(f"  not found: {m}")
    if not copies or missing:
        return 1
    for s in copies:
        print(f"  {s['project']:<28} {s['msgs']:>4} msgs  {s['title'][:60]}  {os.path.relpath(s['path'], ROOT)}")
    if any(is_recent(s) for s in copies) and not args.force:
        print("\nRefusing: a session was updated in the last 30 minutes (possibly the current one). Re-run with --force to override.")
        return 2
    if not args.yes:
        print(f"\n{len(copies)} file sets. Dry run - re-run with --yes to remove.")
        return
    move_to_trash(copies)
    print(f"\nMoved {len(copies)} copies to trash (run 'restore' to undo).")


def cmd_show(args):
    copies = [s for s in load_sessions(True) if s["id"] == args.id or s["id"].startswith(args.id)]
    if not copies:
        print(f"not found: {args.id}")
        return
    s = dedupe(copies)[0]
    print(f"{short(s['title'], 200)}\n")
    print(f"project : {s['project_dir']}\nbranch  : {s['branch'] or '-'}\nupdated : {s['updated'][:16].replace('T', ' ')}")
    print(f"messages: {s['msgs']}    copies: {s.get('copies', 1)}\nid      : {s['id']}")
    if s.get("continued_in"):
        print(f"continued in: {s['continued_in']}")
    if s.get("first_msg"):
        print("\n--- first message ---\n" + s["first_msg"][:1500])


def cmd_restore(args):
    count = 0
    for p in glob.glob(os.path.join(TRASH, "**", "*"), recursive=True):
        if os.path.isfile(p):
            dest = os.path.join(ROOT, os.path.relpath(p, TRASH))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(p, dest)
            count += 1
    print(f"Restored {count} files." if count else "Nothing to restore.")


def cmd_projects(args):
    groups = defaultdict(list)
    for s in dedupe(load_sessions(False)):
        if s["type"] != "main":
            continue
        groups[(s["project"], s["project_dir"])].append(s)
    rows = []
    for (project, pdir), items in groups.items():
        last = max(parse_ts(i["updated"]) for i in items)
        rows.append((last, project, pdir, len(items)))
    rows.sort(key=lambda r: r[0], reverse=True)
    def emit(project, pdir, n):
        if args.format == "tsv":
            label = "session" if n == 1 else "sessions"
            disp = f"{short(project, 24):<24} | {n:>3} {label}"
            print(f"{project}\t{pdir}\t{n}\t{disp}")
        else:
            print(f"{n:>4}  {project}  ({pdir})")

    if args.with_all:
        emit("All projects", "*", sum(r[3] for r in rows))
    for _last, project, pdir, n in rows:
        emit(project, pdir, n)


def cmd_dir(args):
    matches = [s for s in load_sessions(True) if s["id"] == args.id or s["id"].startswith(args.id)]
    if not matches:
        return 1
    print(dedupe(matches)[0]["project_dir"])


def cmd_preview(args):
    direct = glob.glob(os.path.join(ROOT, "*", args.id + ".jsonl"))
    if direct:
        path = direct[0]
    else:
        matches = [s for s in load_sessions(True) if s["id"].startswith(args.id)]
        if not matches:
            print(f"not found: {args.id}")
            return
        path = dedupe(matches)[0]["path"]

    cwd = branch = first_ts = last_ts = ""
    cont = ai_title = custom_title = slug = ""
    msgs = 0
    head = []                 # first messages (chronological)
    tail = deque(maxlen=12)   # most recent messages
    budget = 4000
    used = 0
    try:
        with open(path, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = d.get("type")
                if t in ("user", "assistant"):
                    msgs += 1
                ts = d.get("timestamp")
                if ts:
                    first_ts = first_ts or ts
                    last_ts = ts
                cwd = d.get("cwd") or cwd
                branch = d.get("gitBranch") or branch
                if d.get("aiTitle"):
                    ai_title = d["aiTitle"]
                if d.get("customTitle"):
                    custom_title = d["customTitle"]
                if d.get("slug") and not slug:
                    slug = d["slug"]
                if d.get("continuedInSessionId"):
                    cont = d["continuedInSessionId"]
                if t in ("user", "assistant"):
                    text = " ".join(message_text(d).split())
                    if text:
                        role = "user" if t == "user" else "assistant"
                        out = f"{role}: {short(text, 400)}"
                        tail.append(out)
                        if used < budget and len(head) < 12:
                            head.append(out)
                            used += len(out)
    except OSError:
        print("unreadable session file")
        return

    companion = os.path.splitext(path)[0]
    project = os.path.basename(cwd.rstrip("/")) if cwd else os.path.basename(os.path.dirname(path))
    title = (read_custom_title(companion) or custom_title or ai_title
             or (fmt_slug(slug) if slug else "") or args.id)
    upd = last_ts[:16].replace("T", " ") or "-"
    cre = first_ts[:16].replace("T", " ") or "-"
    print(title)
    print()
    print(f"  project   {cwd or '-'}")
    print(f"  branch    {branch or '-'}")
    print(f"  updated   {upd}    created   {cre}")
    print(f"  messages  {msgs}" + (f"    continued to {cont}" if cont else ""))
    print(f"  id        {args.id}")
    print(f"  file      {os.path.relpath(path, ROOT)}")
    print()
    print("\u2500" * 46)
    print()
    if args.latest:
        rows_view = list(tail)[::-1]   # most recent first
    else:
        rows_view = head

    if rows_view:
        if args.latest:
            print("latest messages (newest first):\n")
        for p in rows_view:
            print(p)
            print()
        if not args.latest and msgs > len(head):
            print(f"\u2026 {msgs} messages total")
    else:
        print("(no plain-text messages)")


def cmd_rename(args):
    title = " ".join(args.title).strip()
    if not title:
        print("empty title; nothing to do")
        return 1
    matches = [s for s in load_sessions(True) if s["id"] == args.id or s["id"].startswith(args.id)]
    if not matches:
        print(f"not found: {args.id}")
        return 1
    ids = {s["id"] for s in matches}
    if len(ids) > 1:
        print(f"ambiguous prefix {args.id}: {', '.join(sorted(i[:12] for i in ids))}")
        return 1
    s = dedupe(matches)[0]
    path = s["path"]
    base = os.path.splitext(path)[0]
    os.makedirs(base, exist_ok=True)
    write_custom_title(os.path.join(base, "custom-title.json"), title)
    append_custom_title_event(path, s["id"], title)
    print(f"renamed {s['id'][:8]} -> {title}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list")
    p_list.add_argument("--all", action="store_true")
    p_list.add_argument("--project")
    p_list.add_argument("--project-dir", help="exact project directory to filter")
    p_list.add_argument("--no-project", action="store_true", help="tsv: omit the project column")
    p_list.add_argument("--format", choices=["text", "md", "tsv"], default="text")
    p_list.add_argument("--limit", type=int, default=5, help="sessions shown per project (default 5)")
    p_list.add_argument("--full", action="store_true", help="show every session")
    p_list.add_argument("--full-ids", action="store_true", help="show 36-char ids instead of 8")
    p_list.set_defaults(func=cmd_list)
    p_clean = sub.add_parser("clean-empty")
    p_clean.add_argument("--yes", action="store_true")
    p_clean.set_defaults(func=cmd_clean)
    p_delete = sub.add_parser("delete")
    p_delete.add_argument("ids", nargs="+")
    p_delete.add_argument("--yes", action="store_true")
    p_delete.add_argument("--force", action="store_true", help="override the 30-minute active-session guard")
    p_delete.set_defaults(func=cmd_delete)
    p_show = sub.add_parser("show")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_show)
    p_restore = sub.add_parser("restore")
    p_restore.set_defaults(func=cmd_restore)
    p_projects = sub.add_parser("projects")
    p_projects.add_argument("--format", choices=["text", "tsv"], default="text")
    p_projects.add_argument("--with-all", action="store_true", help="prepend an 'All projects' row")
    p_projects.set_defaults(func=cmd_projects)
    p_preview = sub.add_parser("preview")
    p_preview.add_argument("id")
    p_preview.add_argument("--latest", action="store_true", help="show the most recent messages (newest first)")
    p_preview.set_defaults(func=cmd_preview)
    p_dir = sub.add_parser("dir")
    p_dir.add_argument("id")
    p_dir.set_defaults(func=cmd_dir)
    p_rename = sub.add_parser("rename")
    p_rename.add_argument("id")
    p_rename.add_argument("title", nargs="+")
    p_rename.set_defaults(func=cmd_rename)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
