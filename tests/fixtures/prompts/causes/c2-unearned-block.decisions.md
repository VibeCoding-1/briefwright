# Decisions — Add a CSV export to the invoices list

Framing: size=standard; autonomy=attended; harness=claude-code; launch=interactive; model=example-model-1; effort=default; run=one-session; machine=personal; seat=implementer; review=fresh; folder=/srv/projects/billing-web

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | claude-code, interactive; model example-model-1 | "run it on example-model-1" | Stated | 2026-10-01 | live |
| D2 | Autonomy | attended | "I'll be here" | Stated | 2026-10-01 | live |
| D3 | Review | a fresh reviewer seat reads the diff | the export touches money amounts | Interview | 2026-10-01 | live |
| D4 | Work | The run changes code: the invoices list, its route and its tests | read in `web/invoices/` | Exploration | 2026-10-01 | live |

## The person's words

> Add a CSV export to the invoices list, only the filtered rows. Leave web/payments alone. Run it on example-model-1. I'll be here.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | "add a CSV export to the invoices list, only the filtered rows" | wish | The export holds exactly the filtered rows, in the list's order. | Mission | T2 |
| W2 | "leave web/payments alone" | prohibition | Out of scope: `web/payments/`, which another team owns. | Scope | T3 |

## Open questions

None.

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|
| Scope discipline [SP #scope] | sample-pack.md | standard and deep | Run rules, Working on |

## Launch

Claude Code CLI, attended:
    cd "/srv/projects/billing-web"
    claude --model example-model-1
  then paste the contents of prompts/invoice-csv-export/master-prompt.md as the first message.

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 0, allowed 0.
