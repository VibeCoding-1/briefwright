# Decisions — Port the date parser of datekit to the standard library

Framing: size=standard; autonomy=unattended; harness=codex; launch=headless; model=example-model-1; effort=high; run=one-session; machine=personal; seat=implementer; review=none; folder=/srv/projects/datekit

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | codex, headless; model example-model-1, high effort | "in the codex CLI on example-model-1, high effort" | Stated | 2026-10-01 | live |
| D2 | Autonomy | unattended, headless on this machine | "leave it running overnight" | Stated | 2026-10-01 | live |

## The person's words

> Port datekit's date parser to the standard library and drop the vendored one; keep the public names. Run it in the codex CLI on example-model-1, high effort, and leave it running overnight, four hours at most.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | "port datekit's date parser to the standard library and drop the vendored one" | wish | which is then deleted | Mission | T2 |
| W2 | "keep the public names" | prohibition | Do not change the public names listed in `datekit/__init__.py`. | Scope | T3 |
| W3 | "four hours" | value | four hours of wall-clock time | Stop rules and interrupt policy | none: the launch's timeout enforces it |

## Open questions

None.

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|
| AD1 | sandbox workspace-write | the unattended headless launch | decisions.md § Launch |
| AD2 | git left to the person: the run commits nothing and records each closed piece in the ledger with the files it changed | the workspace-write sandbox, where `.git` is read-only | Run rules |

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

Codex CLI, unattended on this machine. Sandbox workspace-write: workspace-write is the default; danger-full-access
only in a disposable sandbox. `codex exec` asks for no approval: an action the sandbox refuses fails, and the
run is told so. A `codex exec` call ends at its first completed turn, so the loop resumes the run while its
ledger lists open tasks and none blocked, at most three times, with a message that approves nothing the run
stopped to ask about. It resumes the first call's thread by the id its `thread.started` event gives, never
`--last`, which takes the folder's latest thread and could take a seat's; with no id found it stops. Each
resumed call passes the first call's flags again, since a resume runs on what its own flags and the
configuration give. Under workspace-write `.git` is read-only and the network off, so the run
can neither commit nor push. The loop is not tested.
    cd "/srv/projects/datekit" && mkdir -p prompts/date-parser-port/run && (
    timeout 14400 codex exec -m example-model-1 -c model_reasoning_effort="high" -s workspace-write --json -o prompts/date-parser-port/run/last-0.md - < prompts/date-parser-port/master-prompt.md > prompts/date-parser-port/run/launch-0.jsonl
    tid=$(grep -o '"thread_id": *"[^"]*"' prompts/date-parser-port/run/launch-0.jsonl | head -n 1 | sed 's/.*"\([^"]*\)"$/\1/')
    for n in 1 2 3; do
      [ -n "$tid" ] || break
      grep -q '^- \[!\]' prompts/date-parser-port/run/ledger.md 2>/dev/null && break
      open=$(grep '^- \[ \]' prompts/date-parser-port/run/ledger.md 2>/dev/null | tr '\n' ' ')
      [ -n "$open" ] || break
      timeout 14400 codex exec -m example-model-1 -c model_reasoning_effort="high" -s workspace-write resume "$tid" "Automatic continuation from the launch loop, not the person: it approves nothing you stopped to ask about. Open tasks in your ledger: $open Continue with them. If you stopped to wait for the person, mark that task blocked in the ledger and end the turn." --json < /dev/null > prompts/date-parser-port/run/launch-$n.jsonl
    done )

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 0, allowed 0.
