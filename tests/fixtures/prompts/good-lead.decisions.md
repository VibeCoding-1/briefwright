# Decisions — Move the legacy endpoints in src/api to the new router

Framing: size=standard; autonomy=unattended; harness=claude-code; launch=cloud; model=choose; effort=default; run=one-session; machine=disposable; seat=lead; review=fresh; folder=/workspace/shop-api

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | claude-code, cloud | this session's own, accepted | Default accepted | 2026-10-01 | live |
| D2 | Autonomy | unattended, in a cloud session | "I'll start it in the cloud and walk away, check it in the morning" | Stated | 2026-10-01 | live |
| D3 | Paths | Endpoints keep their exact paths, including the trailing slashes | the mobile client matches paths exactly | Stated | 2026-10-01 | live |

## The person's words

> Move the 42 legacy endpoints in src/api onto the new router; the tests have to stay green. Keep every path exactly as it is, trailing slashes too. Don't touch src/billing or migrations, another team owns them. Put it on a branch called router-migration. I'll start it in the cloud and walk away, check it in the morning.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | "move the 42 legacy endpoints in src/api onto the new router" | wish | Move the 42 legacy endpoints in `src/api/legacy/` onto the router in `src/api/router.py` | Mission | T1 |
| W2 | "the tests have to stay green" | quality | with the test suite green | Mission | T1 |
| W3 | "keep every path exactly as it is, trailing slashes too" | prohibition | Endpoints keep their exact paths, including the trailing slashes the mobile client sends. | Context | T2 |
| W4 | "don't touch src/billing or migrations" | prohibition | Forbidden: `src/billing/` and `migrations/`, because another team owns them. | Scope | T4 |
| W5 | "router-migration" | value | The branch `router-migration` | Required product | none: the branch is where the work lands, named in the final report |

## Open questions

None.

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

Claude Code on the web: open a new session on the repository that holds prompts/api-router-migration/. Then paste the contents of prompts/api-router-migration/master-prompt.md. Also take any
permissions file committed for the run, such as `.claude/settings.json`, off the default branch: its allow rules apply
to every later session on that repository.

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 0, allowed 0.
