# Decisions — Write the getting-started guide for todo-cli

Framing: size=standard; autonomy=attended; harness=generic; launch=interactive; model=choose; effort=default; run=one-session; machine=personal; seat=implementer; review=none; folder=/srv/projects/todo-cli

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | generic, interactive | "my own agent harness" | Stated | 2026-10-01 | live |
| D2 | Autonomy | attended | "step by step with me" | Stated | 2026-10-01 | live |

## The person's words

> Write a getting-started guide for todo-cli with real outputs. Don't touch the code. I run my own agent harness, step by step with me.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | "a getting-started guide for todo-cli with real outputs" | wish | each command's real output pasted from a run of that command | Required product | T1 |
| W2 | "don't touch the code" | prohibition | Do not edit the code under `todo/`. | Scope | T2 |

## Open questions

None.

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

Your harness, attended: open a session in "/srv/projects/todo-cli" by its own
means, and give it prompts/getting-started-guide/master-prompt.md as its first message: paste it, or ask it to read that
file in full and follow it.

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 0, allowed 0.
