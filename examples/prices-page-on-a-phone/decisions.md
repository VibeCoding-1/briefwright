# Decisions — Prices page fits on a phone

Framing: size=quick; autonomy=attended; harness=claude-code; launch=interactive; model=claude-opus-5-5; effort=default; run=one-session; machine=personal; seat=alone; review=none; folder=$HOME/shop-website

(edited: `folder=` above replaces the test machine's scratch path)

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness and model | Claude Code CLI, attended in a terminal on this computer; `claude-opus-5-5` for every seat; harness default effort | "a prompt for Opus 5.5"; Q1: "Claude Code, in the terminal on this same computer. Opus 5.5 for everything. I don't know about effort, so whatever you recommend." | Stated (model), Interview (harness), Default accepted (effort) | 2026-10-06 | live |
| D2 | Autonomy | attended | "I'll be sat at my desk while it works, so it can just ask me if it needs anything." | Stated | 2026-10-06 | live |
| D3 | Opening-hours box | Fixed too: it fits the screen below 768px | Exploration found `.hours { width: 440px }` scrolls sideways under ~500px; person: "Fix that too then, nothing on that page should go sideways." | Interview | 2026-10-06 | live |
| D4 | Phone layout | Below 768px each service row becomes a block: name + price first line, then What's included, then Usual time; labels allowed, text exactly a column heading | Q2 answer: "(b) is fine. Labels are fine as long as the prices and descriptions themselves stay word for word." | Interview | 2026-10-06 | live |
| D5 | Widths | No sideways scroll at any width from 320px up; both pages pixel-identical at 768px and wider | Q3 answer: "(a) is fine. … keep it exactly like that." 320px is the WCAG 2.1 SC 1.4.10 reflow width | Interview | 2026-10-06 | live |
| D6 | Run size | One session | Reflect-back said "one sitting"; person: "The rest sounds right." | Interview | 2026-10-06 | live |
| D7 | Rollback | Originals copied to `prompts/prices-table-mobile-fit/before/` before any edit | Folder is not a git repository (exploration); reflect-back stated it; person: "The rest sounds right." | Interview | 2026-10-06 | live |
| D8 | Ruled-out fixes | No sideways-scrolling table box, no overflow hiding/clipping, no page shrinking | Reflect-back stated the first two; person: "The rest sounds right." Shrinking follows from D4's reason (text keeps its size) | Interview | 2026-10-06 | live |

## The person's words

> Hi, can you write me a prompt for Opus 5.5 to fix the prices page on my shop's website? The files are all in this folder. On my phone the price table runs off the right-hand side and you have to scroll sideways to see the prices. It must never scroll sideways on a phone. On the laptop it looks fine and I want it to stay like that. And please don't change any of the prices or the wording. I'll be sat at my desk while it works, so it can just ask me if it needs anything.

> Oh, I hadn't noticed the opening hours box. Fix that too then, nothing on that page should go sideways. The rest sounds right.
>
> 1. Claude Code, in the terminal on this same computer. Opus 5.5 for everything. I don't know about effort, so whatever you recommend.
> 2. (b) is fine. Labels are fine as long as the prices and descriptions themselves stay word for word.
> 3. I don't know the sizes. Mine's a few years old and customers have all sorts, so (a) is fine. It looks fine on the laptop, keep it exactly like that.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | Opus 5.5 | value | `claude --model claude-opus-5-5` (Opus 5.5), set by the launch | Launch | none: the model is set at launch |
| W2 | fix the prices page | wish | Goal: `prices.html` fits every screen from 320px up, and nothing else on either page changes. | The bar | T1 |
| W3 | It must never scroll sideways on a phone. | quality | every viewport width from 320 to 1920 in 1px steps | The bar | T1 |
| W4 | On the laptop it looks fine and I want it to stay like that. | quality | Both pages pixel-identical to `before/` | The bar | T2 |
| W5 | please don't change any of the prices or the wording | prohibition | "please don't change any of the prices or the wording" | Scope | T3 |
| W6 | it can just ask me if it needs anything | wish | said "it can just ask me if it needs anything" | Stop rules and interrupt policy | none: a permission to ask, not a result; T5 uses it |
| W7 | nothing on that page should go sideways | quality | every `<body>` element's box within `-1` and `clientWidth + 1` | The bar | T1 |
| W8 | Fix that too then | wish | The opening-hours box fits within the screen and keeps its border, padding and white background. | Scope | T1 |
| W9 | Claude Code, in the terminal on this same computer | wish | Claude Code CLI, attended | Launch | none: how the person starts the run |
| W10 | Opus 5.5 for everything | wish | Work alone: dispatch no subagent. | Launch | none: the run has one seat, set at launch |
| W11 | whatever you recommend | wish | effort=default (no effort flag in the launch) | Launch | none: launch setting |
| W12 | (b) is fine | wish | each service row becomes its own block | Scope | T4 |
| W13 | Labels are fine as long as the prices and descriptions themselves stay word for word. | prohibition | "Labels are fine as long as the prices and descriptions themselves stay word for word." | Scope | T3 |
| W14 | (a) is fine | wish | every viewport width from 320 to 1920 in 1px steps | The bar | T1 |
| W15 | keep it exactly like that | quality | Both pages pixel-identical to `before/` | The bar | T2 |

## Open questions

| ID | Question | Affects | Needed before | Status |
|---|---|---|---|---|
| Q1 | Harness, launch and effort for the run | Launch, model check | writing | resolved (→ D1) |
| Q2 | The table's look on a phone | Scope, bar | writing | resolved (→ D4) |
| Q3 | Widths that count as phone and as must-stay-identical | Bar | writing | resolved (→ D5) |

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|
| A1 | Effort: the harness default | Q1 answer "whatever you recommend"; recommendation was the default | Launch |
| A2 | Phone layout boundary `@media (max-width: 767px)` | Q3 (a): pixel-identical from 768px up | Scope |
| A3 | Smallest width 320px | Q3 (a); WCAG 2.1 SC 1.4.10 reflow width | The bar, T1 |
| A4 | Prices and descriptions keep their 17px size on phones | Q2 (b), recommended because a four-column table would need smaller text | Scope, T4 |

## Coverage

1 Outcome: clear (D3–D5). 2 Scope: clear (Scope section, D8). 3 Inputs and settled facts: clear; `table.prices { min-width: 680px }` at `css/style.css` line 60 and `.hours { width: 440px }` at line 90, read 2026-10-06; `css/style.css` shared by `index.html`; not a git repository. 4 Environment: partial; Claude Code CLI 2.1.291 present; per the machine's `CLAUDE.md`, `py` holds Playwright and Chromium; running `py` and `env-check` needed approval in this session, so the prompt checks `py -c "import playwright.sync_api, PIL"` first and asks before installing. 5 Working folder: clear. 6 Data: clear; all wording and prices live in `prices.html`, the closed list. 7 Quality bar: clear; reference is `before/` rendered. 8 Acceptance: clear (T1–T5). 9 Risks: no deploy; edits local and restorable from `before/`. 10 Autonomy: clear (D2, D6). 11 Output: edited files in place; run files in `prompts/prices-table-mobile-fit/run/`. 12 Terminology: "prices page", "price table", "opening hours box", "phone", "laptop". 13 Recoverability: not applicable (quick, attended).

## Red team

not run (quick, attended)

## Method

One agent converging on a machine-checkable exit (T1–T4, `check.py` exit 0), proved able to fail before any edit, then the person's look approval (T5). No seats: the visual subjectivity is covered by the person, who is present. Plateau: two different approaches on the same failing check, then report.

## Guidance put in

| Block | Pack | Task fact that triggers it | Where |
|---|---|---|---|

## Launch

```text
Claude Code CLI, attended:
    cd "$HOME/shop-website"
    claude --model claude-opus-5-5
  then paste the contents of prompts/prices-table-mobile-fit/master-prompt.md as the first message.
```

(edited: the folder in the `cd` line above replaces the test machine's scratch path)

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|

## Review

Linter: errors 0, warnings 1. First pass had 5 × P35 (choice answers and the model name filed as values): W1 was carried by the prompt's opening line, since trimmed: the launch sets the model; W9, W10, W11 and W14 are choices, refiled as wishes.

Kept warning, at delivery: P25 (about 1,700 words, over the then limit of 900 for a quick prompt), kept for the bar's exact checks.

(trimmed to match the current skill: the prompt was cut from 1,614 to 698 words (`wc -w`): the person's words and the reasons stay in this file, and the optional WebKit pass and part of the report list were dropped; § The person's words W2, W3, W4, W7, W12 and W15 now point at the prompt's new text, and the launch block reads as the current guide's. The linter on the trimmed pair: errors 0, warnings 0, allowed 0.)

Self-check (quick lane, no seats): reread from disk as the executor. Added a branch for `index.html` failing T1 before any edit, since the home page must not change. Walked § The person's words W1–W15: each is carried in its section and checked as listed. Reread both messages: no unrecorded demand.

Environment facts not verified in this session: running `py`, `env-check` and Playwright needed approval here, so the prompt's first step checks `py -c "import playwright.sync_api, PIL"` and asks before installing.
