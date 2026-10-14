# Decisions — <task title>

Framing: size=<quick|standard|deep>; autonomy=<attended|unattended>; harness=<claude-code|codex|generic>; launch=<interactive|headless|cloud|other>; model=<model id|choose>; effort=<level|default>; run=<one-session|one-day|multi-session>; machine=<personal|disposable>; seat=<alone|implementer|lead>; review=<fresh|none>; folder=<absolute path>

<!-- prompts/<task-id>/decisions.md, written after every round: the detail the prompt leaves out (the person's words, reasons, rejected options, sources). Line 3 stays one line (the linter reads it). Its folder= fills {FOLDER} inside double quotes, so it starts with /, $HOME or ${HOME}, never ~ (write $HOME for a ~ the person gave), and holds no double quote, backtick, backslash, ! or other $; where the run's own commands use it (the harness guide's §3 says when), it starts with /. IDs never change. The prompt names this file, read on demand, whenever it cites a D-id. seat= and review= follow references/methods.md §12. -->

<!-- harness= names the guide read (references/harness-<harness>.md); model= is a model the person named, as the harness names it, or [you fill this in: the model id], and choose where they named none; effort= is the level the person named, or default. -->

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness | <harness and launch; a model or effort the person named> | <the person's words or answer, or "this session's own, accepted"> | <Stated, Interview or Default accepted> | YYYY-MM-DD | live |
| D2 | Autonomy | <attended, or unattended and its harness> | <the person's words, quoted, or the answer to the autonomy question> | <Stated or Interview> | YYYY-MM-DD | live |

<!-- Source: Stated (named unasked), Exploration, Draft, Interview, Red team, Default accepted. Status: live, or superseded by D<n> — the row stays, its sentences leave the prompt. -->

## The person's words

<!-- Their messages verbatim as a blockquote (`> ` on every line), then the rows (references/interview.md §7). Words: as said; for a value, the value alone. Kind: wish, prohibition, value or quality. In the prompt as: the prompt's exact English text carrying it. Section: its ## heading, Launch, or "not in the prompt: <reason>". Checked by: a T id of the bar, or "none: <reason>", never for quality. -->

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|

## Open questions

| ID | Question | Affects | Needed before | Status |
|---|---|---|---|---|

<!-- open; parked (agreed, a placeholder marks it, the prompt says what to do there, delivery lists it); resolved (→ D-id). -->

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|

<!-- Only defaults the person authorised; an unattended headless launch adds its permission setting and allowlist; headless seats add the bench root. -->

## Coverage

<!-- Each area of references/interview.md §3: clear, partial, missing, or not applicable (why). -->

## Red team

<!-- Deep, or unattended above quick: dimensions, survivors, resolutions (→ D-ids). Else "not run". -->

## Method

<!-- The shape and the routing answers behind it; verification; goal, bar, wait; seats; stop rules; the fit arithmetic and the evidence rung declined; for deep work, the increments and which one this prompt covers; alternatives removed. -->

## Guidance put in

<!-- Only with a guidance pack: in Phase 3, a row per pack block the prompt carries: its ### name and tag; the pack's file; the fact, the key=value its When names as the framing holds it, else a live D- or W-id (not D1, D2) with the fact; its section or brief. -->

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

<!-- The harness guide's §4 blocks for the framing: launch-attended when attended (launch-cloud where launch=cloud); when unattended, launch-headless for launch=headless, launch-cloud for launch=cloud, and the generic guide's launch-headless for launch=other; slots from the guide, the framing and references/methods.md §10's decisions; each ' in an allowlist written '\''. -->

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

<!-- Linter summary; each kept warning with its reason; each allowance on its own line, `Pnn lint-allow: <reason> | at: <exact text of a prompt line>` (the anchor on exactly one line; without `| at:`, a finding with no line, such as P25); the cold read's questions and resolutions; the reviewer's verdict. -->
