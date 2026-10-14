# Decisions — Rename the deprecated configuration keys of weather-cli

Framing: size=standard; autonomy=unattended; harness=claude-code; launch=headless; model=choose; effort=high; run=one-session; machine=personal; seat=alone; review=none; folder=/srv/projects/weather-cli

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | claude-code, headless; high effort | "high effort" | Stated | 2026-10-01 | live |

## The person's words

> Rename the deprecated config keys in weather-cli, keep the old ones loading. Don't change docs/deprecations.md. Run it at high effort; I'll start it and walk away, five dollars at most.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | "rename the deprecated config keys in weather-cli, keep the old ones loading" | wish | the old names still load with a warning | Mission | T2 |
| W2 | "don't change docs/deprecations.md" | prohibition | Do not edit `docs/deprecations.md` | Scope | T3 |
| W3 | "five dollars" | value | five dollars for the run, a cap | Stop rules and interrupt policy | none: the launch's budget flag enforces it |

## Open questions

None.

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|
| AD1 | permission mode acceptEdits with the allowlist in § Launch | the unattended headless launch | decisions.md § Launch |

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

Claude Code CLI, unattended on this machine. Permission mode acceptEdits: acceptEdits with the
allowlist below is the default; bypassPermissions only in a disposable sandbox. In -p nobody can answer
a permission prompt, so a call that neither the mode nor the allowlist allows is refused. The allowlist
bounds mistakes, not hostile input: the run can execute code it writes, with this account's files,
credentials and network, so where the run reads untrusted content, run it in a container or a VM. When the
first call ends, the loop resumes the run while its ledger lists open tasks and none blocked, at most three
times, with a message that approves nothing the run stopped to ask about:
    cd "/srv/projects/weather-cli" && mkdir -p prompts/config-keys-rename/run && (
    claude -p --session-id 5f0c2a7e-91d4-4b36-8e2f-6a1d3c9b7e40 --effort high --permission-mode acceptEdits --allowed-tools 'Bash(date *),Bash(mkdir *),Bash(pwd),Bash(git status *),Bash(git diff *),Bash(git log *),Bash(git add *),Bash(git commit *),Bash(python3 -m pytest *)' --max-budget-usd 5 --output-format json < prompts/config-keys-rename/master-prompt.md > prompts/config-keys-rename/run/launch-0.json
    for n in 1 2 3; do
      grep -q '^- \[!\]' prompts/config-keys-rename/run/ledger.md 2>/dev/null && break
      open=$(grep '^- \[ \]' prompts/config-keys-rename/run/ledger.md 2>/dev/null | tr '\n' ' ')
      [ -n "$open" ] || break
      claude -p "Automatic continuation from the launch loop, not the person: it approves nothing you stopped to ask about. Open tasks in your ledger: $open Continue with them. If you stopped to wait for the person, mark that task blocked in the ledger and end the turn." --resume 5f0c2a7e-91d4-4b36-8e2f-6a1d3c9b7e40 --effort high --permission-mode acceptEdits --allowed-tools 'Bash(date *),Bash(mkdir *),Bash(pwd),Bash(git status *),Bash(git diff *),Bash(git log *),Bash(git add *),Bash(git commit *),Bash(python3 -m pytest *)' --max-budget-usd 5 --output-format json < /dev/null > prompts/config-keys-rename/run/launch-$n.json
    done )

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 0, allowed 0.
