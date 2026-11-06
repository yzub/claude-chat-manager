# Claude Code CLI session picker (backed by ~/.claude/scripts/sessions.py)
# Stage 1: pick a project (or "All projects"). Stage 2: pick a session.
# Preview is a bottom (horizontal) split. Stage 2 keys: ENTER=resume (in a subshell, from the project dir)
#   CTRL-R=rename  CTRL-X=delete  CTRL-A=toggle all  ESC=back
claude-manager() {
  local cs_py="$HOME/.claude/scripts/sessions.py"
  local extra=("$@")

  while true; do
    local proj_line
    proj_line=$(python3 "$cs_py" projects --with-all --format tsv | fzf \
      --delimiter $'\t' --with-nth=4 \
      --header "Select a project  (ENTER open | ESC quit)" \
      --preview "python3 '$cs_py' list --format text --project-dir \"{2}\" 2>/dev/null | head -50" \
      --preview-window=down:50%:wrap) || return 0
    [ -z "$proj_line" ] && return 0
    local pdir=$(cut -f2 <<< "$proj_line")
    local pname=$(cut -f1 <<< "$proj_line")

    local list_args=(--format tsv --project-dir "$pdir")
    [ "$pdir" != "*" ] && list_args+=(--no-project)
    local hdr="Project: $pname"
    [ "$pdir" = "*" ] && hdr="All projects"

    while true; do
      local result
      result=$(python3 "$cs_py" list "${list_args[@]}" "${extra[@]}" | fzf \
        --delimiter $'\t' --with-nth=2 --multi \
        --expect=ctrl-x,ctrl-r --bind 'ctrl-a:toggle-all' \
        --header "$hdr  |  ENTER=Resume  CTRL-R=Rename  CTRL-X=Delete  CTRL-A=Toggle  ESC=Back" \
        --preview "python3 '$cs_py' preview {1} --latest" \
        --preview-window=down:50%:wrap) || break   # ESC -> back to projects

      local key=$(head -n 1 <<< "$result")
      local lines=("${(@f)$(tail -n +2 <<< "$result")}") ids=() line
      for line in "${lines[@]}"; do [ -n "$line" ] && ids+=("${line%%$'\t'*}"); done
      [ -z "${ids[1]}" ] && break

      if [ "$key" = "ctrl-x" ]; then
        python3 "$cs_py" delete "${ids[@]}"; local rc=$?
        if [ "$rc" = "2" ]; then
          echo -n "Updated <30 min ago — delete anyway? (y/N): "
          read -r force_confirm
          if [[ "$force_confirm" =~ ^[Yy]$ ]]; then
            python3 "$cs_py" delete "${ids[@]}" --force --yes
            sleep 0.3
          fi
          continue  # re-list
        elif [ "$rc" != "0" ]; then
          echo "Delete aborted."
          sleep 1
          continue
        fi
        echo -n "Confirm delete? (y/n): "
        read confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
          python3 "$cs_py" delete "${ids[@]}" --yes
          sleep 0.3
        fi
        continue  # re-list
      elif [ "$key" = "ctrl-r" ]; then
        local cur
        cur=$(python3 "$cs_py" show "${ids[1]}" 2>/dev/null | head -n 1)
        echo -n "New title (current: ${cur:-?}): "
        read -r newtitle
        if [ -n "$newtitle" ]; then
          python3 "$cs_py" rename "${ids[1]}" "$newtitle" && sleep 0.3
        fi
        continue  # re-list to show the new title
      else
        local sdir
        sdir=$(python3 "$cs_py" dir "${ids[1]}" 2>/dev/null)
        if [ -n "$sdir" ] && [ -d "$sdir" ]; then
          ( cd "$sdir" && claude --resume "${ids[1]}" )  # subshell: keeps your cwd
        else
          claude --resume "${ids[1]}"
        fi
        return
      fi
    done
  done
}

# Claude Code session manager (run the script directly)
alias ccs="python3 ~/.claude/scripts/sessions.py"
