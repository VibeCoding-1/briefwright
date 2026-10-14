# Decisions — Fix slugify so the four slugger tests pass

Framing: size=quick; autonomy=attended; harness=claude-code; launch=interactive; model=example-model-1; effort=default; run=one-session; machine=personal; seat=alone; review=none; folder=/srv/projects/slugger

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | claude-code, interactive; model example-model-1 | "run it here on example-model-1" | Stated | 2026-10-01 | live |
| D2 | Autonomy | attended | "I'll watch it" | Stated | 2026-10-01 | live |

## The person's words

> Fix slugify so the four tests in slugger pass; run it here on example-model-1. Don't touch the tests. I'll watch it.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | "fix slugify so the four tests in slugger pass" | wish | `python3 -m unittest discover -s slugger -q` exits 0 with 4 tests run | The bar | T1 |
| W2 | "don't touch the tests" | prohibition | Do not edit `slugger/test_slugger.py` | Scope | T2 |

## Open questions

None.

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

Claude Code CLI, attended:
    cd "/srv/projects/slugger"
    claude --model example-model-1
  then paste the contents of prompts/slug-fix/master-prompt.md as the first message.

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 0, allowed 0.
