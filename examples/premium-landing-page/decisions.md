# Decisions — Ardeta landing page

Framing: size=standard; autonomy=unattended; harness=claude-code; launch=cloud; model=claude-opus-5-5; effort=default; run=one-session; machine=disposable; seat=lead; review=fresh; folder=$HOME/ardeta-web

## Decisions log

| ID | Topic | Decision | Rationale | Source | Date | Status |
|---|---|---|---|---|---|---|
| D1 | Harness and model | Claude Code on the web (cloud session); every seat on `claude-opus-5-5`; harness default effort | "Sí. Claude Code en la nube, en la web. Opus 5.5, el mismo que esta sesión, para todo." | Interview | 2026-10-06 | live |
| D2 | Autonomy | Unattended, in a cloud session (launch=cloud) | "(c). Lo lanzo por la noche y me voy a dormir; nadie va a contestar." | Interview | 2026-10-06 | live |
| D3 | Run size | One session, tonight | "(a), una sesión esta noche." | Interview | 2026-10-06 | live |
| D4 | Purpose of the page | Waitlist page that collects emails; the shop opens in November; nothing is sold on this page; main button text `Únete a la lista` | "(b). Es una lista de espera para recoger emails, la tienda abre en noviembre y aquí no se vende nada. El botón dice "Únete a la lista"." | Interview | 2026-10-06 | live |
| D5 | References | Proposed by me (round 2); the person likes the websites of expensive cosmetics brands | "(b), propónmelas tú. No tengo una concreta; me gustan las webs de marcas de cosmética caras." | Interview | 2026-10-06 | live (set pending R2) |
| D6 | Photos | Type-led design; photo slots composed into the design (brand colour, exact aspect ratio, discreet label); a shot list for the photographer; swapping a photo is replacing one file | Q6 (a) | Interview | 2026-10-06 | live |
| D7 | Product claims | Only the facts in `brand/brand-notes.md`; no doses, prices, health claims, reviews, figures or seals; gaps marked as pending | "(a). No quiero problemas: que no prometa que cura nada." | Interview | 2026-10-06 | live |
| D8 | Language | Spanish only | "(a), solo español." | Interview | 2026-10-06 | live |
| D9 | Stack and delivery | Static HTML and CSS, no framework, no build step, in `site/`; self-hosted free-licence fonts; no third-party scripts; pushed to the session's own branch; nothing published | "(a). Algo sencillo que luego pueda subir a cualquier hosting." | Interview | 2026-10-06 | live |
| D10 | References | Aesop (aesop.com), LYMA (lyma.life), Seed (seed.com); alternates in order Augustinus Bader (augustinusbader.com), Byredo (byredo.com), Heights (yourheights.com); the run uses the first three it can capture; never copies their text, images or code; not verified from this session (no web access) | "10. Sí." | Interview | 2026-10-06 | live |
| D11 | Cloud environment and permissions | A cloud environment dedicated to this run: network "Full"; a setup script that installs Playwright's Chromium and always exits 0; the forced model pair and `PLAYWRIGHT_BROWSERS_PATH`; permission mode "Auto"; a committed `.claude/settings.json` with narrow allow rules for the run's own commands; `git push` allowed only to `claude/ardeta-landing-page`, pushes authorised in advance | "11. (a). No sé nada de esto, así que lo que recomiendes." | Interview | 2026-10-06 | live |
| D12 | Email service | None yet: the form posts to one action URL in one place, shipped as the reserved never-resolving `https://lista.invalid/` with a STUB note; tested against a local mock endpoint; the site stores nothing | "12. (a). No lo sé, todavía no tengo herramienta de email." | Interview | 2026-10-06 | live |
| D13 | Retention and deletion of emails (hard block resolved) | The list lives only in the email service the person will choose; double opt-in and an unsubscribe link in every email (service features, listed in the report as setup steps); unticked consent checkbox required to submit; the person deletes the list when the period ends; the privacy page shows the period as a visible `[pendiente: …]` gap | "13. No lo sé; lo que recomiendes, (a)." | Interview | 2026-10-06 | live |
| D14 | Legal texts | The run creates `privacidad.html`, `aviso-legal.html` and the basic-information block beside the form, structured on the official texts read during the run (GDPR art. 13 on eur-lex.europa.eu, LSSI art. 10 on boe.es, the AEPD's guidance on informing in layers on aepd.es); every company datum a visible `[pendiente: …]` gap; the person reviews with an adviser before publishing | "14. Los textos legales no los tengo todavía. (a)." | Interview | 2026-10-06 | live |
| D15 | Short sentences | No sentence longer than 20 words in the page text, legal texts excluded | "15. Sí." | Interview | 2026-10-06 | live |
| D16 | Ranking and method | The ranking and the method as recommended | "El resumen está bien. El orden de prioridades y el método no los decidí yo; si los recomiendas, vale." | Default accepted | 2026-10-06 | live |
| D17 | Working folder in the cloud | Expected clone path `$HOME/ardeta-web`; phase zero reads `git rev-parse --show-toplevel` and uses that path if it differs | Docs give no path (they use `$CLAUDE_PROJECT_DIR`); this session's own paths show `$HOME/<repo>` | Exploration | 2026-10-06 | live |
| D18 | Consent text and purpose | Checkbox label, exact: `Quiero recibir emails de Ardeta sobre la apertura de la tienda y sus novedades. Tengo 18 años o más.`; purpose: the shop's opening and its news | "19. No lo sé; lo que recomiendes, (a)." | Interview (red team RT12) | 2026-10-06 | live |
| D19 | Logo for the web | `brand/logo.svg` untouched; a web copy whose wordmark is outlined from Gelasio (free, metric-compatible with Georgia) | "20. (a), lo que recomiendes." | Interview (red team RT13) | 2026-10-06 | live |
| D20 | Register and softgel wording | Address the reader as «tú»; softgels are «perlas» (`60 perlas`) | "21. No lo sé; (a) vale." | Interview (red team RT16, RT17) | 2026-10-06 | live |
| D21 | Red-team design changes | RT1–RT11, RT14–RT18 resolutions adopted as listed in § Red team; time box: no new round after 6 h 30 min from phase zero, the night (8 h) as the run's cap | "Los cambios me parecen bien y apruebo el diseño." | Red team | 2026-10-06 | live |

## The person's words

> Prepárame el prompt: quiero una landing page para mi marca de suplementos que se vea premium, al nivel de las mejores del sector. Que la haga una sesión en la nube, ella sola, esta noche.

> 1. Sí. Claude Code en la nube, en la web. Opus 5.5, el mismo que esta sesión, para todo.
> 2. (c). Lo lanzo por la noche y me voy a dormir; nadie va a contestar.
> 3. (a), una sesión esta noche.
> 4. (b). Es una lista de espera para recoger emails, la tienda abre en noviembre y aquí no se vende nada. El botón dice "Únete a la lista".
> 5. (b), propónmelas tú. No tengo una concreta; me gustan las webs de marcas de cosmética caras.
> 6. (a).
> 7. (a). No quiero problemas: que no prometa que cura nada.
> 8. (a), solo español.
> 9. (a). Algo sencillo que luego pueda subir a cualquier hosting.

> 10. Sí.
> 11. (a). No sé nada de esto, así que lo que recomiendes.
> 12. (a). No lo sé, todavía no tengo herramienta de email.
> 13. No lo sé; lo que recomiendes, (a).
> 14. Los textos legales no los tengo todavía. (a).
> 15. Sí.
>
> El resumen está bien. El orden de prioridades y el método no los decidí yo; si los recomiendas, vale.

> 19. No lo sé; lo que recomiendes, (a).
> 20. (a), lo que recomiendes.
> 21. No lo sé; (a) vale.
>
> Los cambios me parecen bien y apruebo el diseño.

| ID | Words | Kind | In the prompt as | Section | Checked by |
|---|---|---|---|---|---|
| W1 | una landing page para mi marca de suplementos | wish | A static Spanish landing page that invites people to join Ardeta's waitlist | Mission | T1, T19 |
| W2 | que se vea premium, al nivel de las mejores del sector | quality | It must stand next to the reference sites without looking cheaper | Mission | T20 |
| W3 | Que la haga una sesión en la nube | wish | not in the prompt: the cloud environment and session are set at launch | Launch | none: a launch setting, reported by the phase-zero status line |
| W4 | ella sola | wish | Decide the rest, log the ruling in the ledger with its cost if wrong, and continue. | Stop rules and interrupt policy | none: a behaviour rule, enforced by the interrupt policy and the run rules |
| W5 | esta noche | value | "esta noche": 8 hours from phase zero | Stop rules and interrupt policy | none: a time cap measured with `date -u` in the ledger |
| W6 | Opus 5.5 | value | `/model claude-opus-5-5` (Opus 5.5), set by the launch | Launch | none: the model is set at launch |
| W7 | nadie va a contestar | prohibition | Nobody will answer tonight | Stop rules and interrupt policy | none: run rules "Long operations run detached" and "Resume from the files" |
| W8 | una lista de espera para recoger emails | wish | The form: `method="post"`, `action="https://lista.invalid/"` | Required product | T16 |
| W9 | tienda abre en noviembre | value | The shop opens in November (`La tienda abre en noviembre`) | Context | T5 |
| W10 | aquí no se vende nada | prohibition | No shop, prices, cart or buy buttons — "aquí no se vende nada" | Scope | T3 |
| W11 | Únete a la lista | value | Main button text, exact: `Únete a la lista` | Context | T4 |
| W12 | me gustan las webs de marcas de cosmética caras | quality | References in order: Aesop `https://www.aesop.com/`, LYMA `https://www.lyma.life/`, Seed `https://seed.com/` | Context | T20 |
| W13 | que no prometa que cura nada | prohibition | No health claims of any kind | Context | T3, T21 |
| W14 | solo español | value | "solo español" | Context | T20 |
| W15 | Algo sencillo que luego pueda subir a cualquier hosting | wish | Static HTML and CSS in `site/`. No framework, no build step, no server code | Context | T12, T17 |
| W16 | Quiero recibir emails de Ardeta sobre la apertura de la tienda y sus novedades. Tengo 18 años o más. | value | Consent checkbox label, exact: `Quiero recibir emails de Ardeta sobre la apertura de la tienda y sus novedades. Tengo 18 años o más.` | Context | T4, T16 |
| W17 | 20. (a): the logo web copy | wish | `brand/logo.svg` stays byte-identical; `site/assets/img/logo-web.svg` | Context | T8 |
| W18 | «tú» | value | Address the reader as «tú». | Context | T20 |
| W25 | «perlas» | value | Softgels are «perlas». | Context | T4 |
| W19 | 20 | value | no sentence over 20 words | The bar | T3 |
| W20 | 13. (a): retention in the service, period as a gap | wish | `privacidad.html` shows that period as a visible gap | Context | T11, T22 |
| W21 | 14. (a): legal drafts with gaps | wish | Legal drafts: `privacidad.html` and `aviso-legal.html` | Context | T22 |
| W22 | 12. (a): no email tool yet | wish | Email service unknown. The single form posts to `https://lista.invalid/` | Context | T16 |
| W23 | 11. (a): the recommended cloud environment | wish | not in the prompt: environment settings and `.claude/settings.json` | Launch | none: launch settings; phase zero reports the browser and the push |
| W24 | 10. Sí: the proposed references | wish | Use the first three that yield a valid capture | Context | T20 |

## Open questions

| ID | Question | Affects | Needed before | Status |
|---|---|---|---|---|
| Q10 | Reference set | the bar | Phase 2 | resolved (→ D10) |
| Q11 | Cloud environment: network level, setup script, permission mode | launch, phase zero | Phase 2 | resolved (→ D11) |
| Q12 | Email service for the waitlist | form action | Phase 2 | resolved (→ D12) |
| Q13 | Retention and deletion of the emails (security hard block) | privacy page, constraints | writing | resolved (→ D13) |
| Q14 | Legal pages (privacy, legal notice) | scope | Phase 2 | resolved (→ D14) |
| Q15 | "frases cortas" as a number | copy bar | Phase 2 | resolved (→ D15) |
| Q16 | Retention period of the emails | privacy page text | publishing (not the run) | parked: a visible `[pendiente: …]` gap in `privacidad.html`, listed in the final report (D13) |
| Q17 | Company data (razón social, NIF, address, contact email) | legal pages | publishing (not the run) | parked: visible `[pendiente: …]` gaps (D14) |
| Q18 | Email service and its form URL | form action | publishing (not the run) | parked: `https://lista.invalid/` with a STUB note (D12) |

## Accepted defaults

| ID | Default | Derived from | In the prompt at |
|---|---|---|---|
| A1 | Outcome ranking: correct complete pages > visual level > legal drafts > shot list | my recommendation, accepted (D16) | Mission |
| A2 | Lead that does not implement; fresh critic every round; at most 3 seats at a time | references/methods.md seat rule and parallel recommendation, accepted (D16) | Method |
| A3 | Bar thresholds: Lighthouse mobile performance ≥ 90 (median of 3); axe serious/critical = 0; six widths 360–1920 with no horizontal scroll; targets ≥ 44 px | presented in the final design, approved | The bar T13–T15 |
| A4 | The health and selling word lists of T3 | red-team RT7, examples presented, approved | The bar T3 |
| A5 | Time box: no new round after 6 h 30 min; cap 8 h | "esta noche" and the final design, approved | Stop rules and interrupt policy, Method |
| A6 | Branch `claude/ardeta-landing-page`; pushes only there | Q11 (a) | Context, Run rules |
| A7 | Placeholder form action `https://lista.invalid/` (reserved TLD, RFC 2606) with a not-open-yet guard | Q12 (a), red-team RT11 | Context, Required product, T16 |
| A8 | Field names `email`, `consentimiento`, honeypot `website` | my choice inside D12 (provider-agnostic; remapped when the service is chosen) | Required product |
| A9 | Gelasio for the logo outlines | Q20 (a) | Context |
| A10 | Valid capture rule (brand name present, no challenge page, overlays under 25% after one dismiss attempt, fonts ready) | red-team RT8, approved | Method phase 1 |
| A11 | Cloud environment: network Full, setup script, `PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright`, permission mode Auto (Accept edits where Auto is absent), `.claude/settings.json` from `prompts/ardeta-landing-page/settings.json` | Q11 (a), red-team RT2 | Launch |

## Coverage

1. Outcome and audience — partial: waitlist page (D4); ranking of outcomes to confirm in the reflect-back.
2. Scope and non-goals — partial: no sales, no prices, no health claims (D4, D7).
3. Inputs and settled facts — clear: `brand/brand-notes.md`, `brand/logo.svg`; the logo's wordmark is SVG `<text>` in Georgia, so it renders in a fallback serif where Georgia is absent; gold `#B08D57` on cream `#F4EFE6` computed by hand at about 2.7:1 (below WCAG AA for text; the run's contrast check decides).
4. Environment and constraints — partial. Fact-finding seat (code.claude.com docs, retrieved 2026-10-06): a cloud session is an Ubuntu 24.04 VM (about 4 vCPU, 16 GB RAM, 30 GB disk) with Node 22 on PATH, Python 3, Java 21, git, gh, chromedriver; Playwright and Chrome/Chromium not listed. Default network level "Trusted": registry.npmjs.org, pypi.org, github.com, fonts.googleapis.com, fonts.gstatic.com allowed; Playwright browser hosts and arbitrary sites (reference sites) blocked with 403 `host_not_allowed`; "Custom" allowlist or "Full" per environment. Setup script optional, runs as root before Claude Code; a non-zero exit stops the session from starting. Session keeps running after the tab closes, idles when the agent ends its turn; an idle VM pauses after a few minutes and can be reclaimed (running subagents and shell commands lost; uncommitted changes may be lost). Session pushes its branch at stopping points; `claude/` prefix unless the prompt names another branch; branch protection applies. Subagents work; `/model <id>` from CLI 2.1.205; environment variables reach the session. Opus 5.5 needs CLI 2.1.280 or later; alias `opus` resolves to Opus 5.5 from 2.1.280 (model-config, via WebFetch summary). Usage limits are shared with the account. Read tool shows PNGs. Permission modes in cloud: Accept edits (= `default`: other Bash commands prompt in claude.ai and the session waits), Plan, Auto (a classifier reviews actions; falls back to prompting after 3 consecutive or 20 total blocks; offered when the organisation allows it and the model supports it); cloud ignores `bypassPermissions` and `dontAsk`; the repository's `.claude/settings.json` permission rules carry over. Web access from this session (WebFetch, WebSearch, curl) refused: the legal and reference-site seats returned nothing verified.
5. Working folder and ownership — partial: repository `ardeta-web` (origin `https://github.com/<owner>/ardeta-web.git` (edited: the test's made-up remote)), one commit "fixture"; `.claude/skills/` untracked; clone path in the cloud being verified.
6. Data and integrations — partial: emails go to an email service (Q12); the static site stores nothing.
7. Quality bar and references — partial: references proposed in round 2.
8. Acceptance and verification — partial: deterministic checks plus fresh critics against references, to confirm.
9. Risks and irreversible actions — partial: personal data (emails) → hard block Q13; EU health-claim rules (D7 avoids claims entirely).
10. Budget, time and autonomy — clear: unattended, cloud, one session (D2, D3); no USD cap flag in a cloud session.
11. Output and delivery — partial: `site/`, pushed to a branch (D9).
12. Terminology — clear: product names as in brand-notes.md; `Únete a la lista`; "lista de espera".
13. Recoverability — partial: ledger and frequent pushes (disposable VM).

## Red team

One seat (`helper seat: red team`, dispatched with `model: "opus"`), dimensions: failure modes, scaling cliffs, security, contradictions, operations, data integrity, dependencies, wildcard. 18 survivors (4 critical, 9 major, 5 minor). Resolutions (design changes presented in the final reflect-back; questions asked there):

- RT1 (critical) the turn ending idles the VM → RS8's unattended text; seats dispatched in the foreground (several in one message for parallel); servers start and stop inside one command; rules reread from the committed prompt file and ledger at every close; resume by the person typing `Continúa`.
- RT2 (critical) permission prompts freeze the run → installs in the setup script; `.claude/settings.json` allowlist covering every command of the plan in Accept edits too, plus a deny list; never retry a blocked action the same way; blocked actions counted in the ledger.
- RT3 (critical) usage limit mid-run → a thin, complete, checked and pushed first version of every page and the report before any polish round; `INFORME.md` rewritten at every push.
- RT4 (critical) launch prerequisites → Launch written step by step (delivery in Spanish); the person uploads `.claude/settings.json` and the prompt file to the default branch; the person watches about 10 minutes until the run prints its phase-zero status line.
- RT5 (major) an interrupt with nobody answering → the task is marked blocked, every independent task continues, the run ends with the report.
- RT6 (major) branch exists or push refused → fixed branch `claude/ardeta-landing-page`; phase zero fetches it and resumes from its ledger if it exists; never force-push; a refused push is recorded and work continues locally.
- RT7 (major) prohibitions unchecked → denylists of claim stems and selling words, a closed-world number check, a facts-trace table checked by script, a claims audit by the final critic.
- RT8 (major) reference captures invalid → a definition of a valid capture; the alternates; fewer than three valid captures → judge against the valid ones and report the weaker bar; none → no reference comparison, reported.
- RT9 (major) critics penalise missing photos → critics judge composition of the photo slots, never imagery; screenshots as viewport-height tiles after `document.fonts.ready`.
- RT10 (major) browser toolchain traps → checks split into static and browser parts; one Playwright version (global from the setup script, pinned in `tools/package.json`); `CHROME_PATH` to Playwright's Chromium; the setup log read in phase zero; Lighthouse median of 3.
- RT11 (major) the placeholder form loses signups → while the action is `https://lista.invalid/`, submitting shows a calm "not yet open" message and sends nothing; privacy page gaps for the email service and international transfers; connection steps in the report.
- RT12 (major) consent wording, purpose and age → asked (Q19).
- RT13 (major) logo wordmark in Georgia → asked (Q20).
- RT14 (minor) photo weights → shot list gives size, format and maximum weight per slot; images with width and height, lazy below the fold.
- RT15 (minor) morning visibility → `INFORME.md` in Spanish at the repository root with screenshots and viewing steps; final message in Spanish.
- RT16 (minor) facts list and product tokens → the facts list is brand-notes.md plus the person's interview facts; product-name tokens allowed in the number check; softgel wording asked (Q21).
- RT17 (minor) tú or usted → asked (Q21).
- RT18 (minor) repository exposure and dependencies → reference captures never committed; lockfile; `node_modules` ignored; font licence files; glyph check for Spanish characters.

## Method

Approved in the final reflect-back ("Los cambios me parecen bien y apruebo el diseño."), with the red-team changes (D21): phase 2 builds a complete first version of every page and the report before the critic rounds; Lighthouse gates performance only (≥ 90), the other scores reported; the evidence rung declined is a judge panel per round.

- **Routing.** No binary exit (subjective quality); subtasks predictable (tooling, references, spine, rest of page, legal pages, shot list, final review); subjective quality with real external references (D10) → research the references and derive measurable notes, then a blind comparison loop against them (references/method-catalog M2 then M6), on a sequential monolithic page (index.html builders in sequence; the legal pages are a disjoint file set). Unattended → ledger, recoverability, interrupt policy. Seat: unattended with a plan of more than one task → a lead that does not implement; `review=fresh` (fresh critic every round).
- **Capabilities.** Subagents yes (Agent tool); browser: Playwright Chromium from the setup script, else installed in phase zero (network Full), else degraded (no visual bar, reported); code execution yes; persistent filesystem yes but the VM is disposable → push at each closed piece; network Full (D11); no MCP.
- **Verification.** Rung 1–2: `node tools/check.mjs` (HTML validity, no third-party requests on load, axe-core serious/critical = 0, Lighthouse mobile thresholds, no horizontal scroll at six widths, copy rules, closed-world numbers, exact button text, form journey against a local mock, colour literals only in tokens, photo slots vs shot list, logo byte-identical, reduced motion, tap targets). Rung 3: fresh critic per round, screenshots of the pinned commit vs the reference captures at 390×844 and 1440×900, eight named dimensions, verdict JSON, closure computed by the lead. Rung declined: a judge panel or several critics per round (verification would outweigh a one-page product).
- **Goal, bar, wait.** Goal: a Spanish waitlist landing page for Ardeta, static, at the level of the reference set, ready to connect to an email service. Bar: T1–T20 in the prompt. Wait: not done until the final fresh critic's verdict and `node tools/check.mjs` on the final commit are both in the ledger.
- **Seats.** Lead (plans, briefs, runs checks, commits and pushes, computes closure, writes the report); builders (tooling; spine; rest of page; legal and thank-you pages; shot list) each fresh per task and per fix round; researchers (reference capture and notes; legal sources); critics fresh every round, read-only enforced by a `git status --porcelain` check around each critic; a final whole-page critic and a fresh re-verify after the one fix wave. At most 3 seats at a time.
- **Stop rules.** Success; plateau (two verdicts tie or worse with the same criterion unmet) → a structural pass by a fresh builder with the ruled-out list; plateau again → honest delivery of the best judged commit; interrupt policy (irreversible, credentials or accounts, side effects outside the folder such as a push to another branch or publishing, ambiguity that changes the project, a seat on another model twice); nobody answers, so every other ambiguity is a logged ruling.
- **Fit arithmetic.** About 18–24 seats (tooling 1, references 1, legal sources 1, spine 2–3 builder + 2–3 critic rounds, rest of page 2–3 + 2–3, legal pages 1 + 1 review, shot list 1, final critic 1, fix wave 1, re-verify 1); each 10–30 minutes, up to 3 in parallel → about 4–7 hours of wall clock; the cloud VM: 4 vCPU, 16 GB RAM; Lighthouse and screenshots take under a minute each. Past 8 hours the lead stops opening new work and moves to final review.
- **Alternatives removed.** A single careful pass (no independent visual judgment; the person wants "premium" proved against references); an evaluator loop with self-written criteria (a critic would invent the bar when references exist); parallel section builders on index.html (one file, unmergeable edits).

## Launch

Before launching (the person, on github.com, logged in):
1. Open `https://github.com/<owner>/ardeta-web` (edited: the test's made-up remote) on the default branch and check that the folder `brand/` with `brand-notes.md` and `logo.svg` is there; if not, upload both into a folder `brand/` (Add file → Upload files).
2. Add file → Create new file, name `.claude/settings.json`, paste the content of `prompts/ardeta-landing-page/settings.json`, commit to the default branch.
3. Add file → Create new file, name `prompts/ardeta-landing-page/master-prompt.md`, paste the prompt, commit to the default branch. (Never `git add .` locally: `.claude/skills/` is untracked and would load into the run.)

4. Create a cloud environment dedicated to this run (the cloud icon above the message box, then Cloud, then Add cloud environment; remove it after the run), as below, and open the session in it.

The harness guide's `launch-cloud` block, filled (edited: the current guide's wording, which replaced the delivered one's):

```text
Claude Code on the web: open a new session on the repository that holds prompts/ardeta-landing-page/. Send `/model claude-opus-5-5` as its
first message, then paste the contents of prompts/ardeta-landing-page/master-prompt.md. Also take any
permissions file committed for the run, such as `.claude/settings.json`, off the default branch: its allow rules apply
to every later session on that repository.
```

The dedicated environment (decision D11):
- Network access: **Full**.
- One more environment variable: `PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright`.
- Setup script:

```bash
#!/bin/bash
# Ardeta landing page: browser for screenshots. Never stops the session from starting.
{
  export PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
  npm install -g playwright@latest
  playwright install --with-deps chromium
  chmod -R a+rX /opt/ms-playwright
  playwright --version
} > /tmp/ardeta-setup.log 2>&1
exit 0
```

- The session: repository `ardeta-web`, starting from the default branch; permission mode **Auto** in the mode dropdown (Accept edits where Auto is not offered: the committed allowlist covers the plan's commands).
- After pasting the prompt, watch about 10 minutes for the line `FASE CERO CORRECTA …` (or `FASE CERO CON PROBLEMAS …`), then leave.
- In the morning: `INFORME.md` on the branch `claude/ardeta-landing-page`; if the session stopped early, send `Continúa`.

The allowlist and deny list (`prompts/ardeta-landing-page/settings.json`, to be committed as `.claude/settings.json`): allow — the exact `printenv PLAYWRIGHT_BROWSERS_PATH` read; `date`; `pwd`; `mkdir`; `check-tools`; `which`; `cat /tmp/ardeta-setup.log`; `playwright --version`; `npx playwright *`; `npm install|ci|ls *`; `node tools/*`; git `rev-parse`, `branch`, `fetch origin`, `switch [-c] claude/ardeta-landing-page`, `status`, `diff`, `log`, `show`, `add`, `commit`, `restore`, `clean -fd -- site tools`, `push [-u] origin claude/ardeta-landing-page`; WebFetch on eur-lex.europa.eu, boe.es, aepd.es. Deny — force pushes, `push --delete`, pushes to `main`/`master`, `reset --hard`, `branch -D`, `sudo`. In auto mode the broad interpreter rules (`node tools/*`, `npx playwright *`) may be dropped and go to the classifier instead (docs, permission-modes); the narrow ones stay.

No USD cap flag exists for a cloud session; the run's cap is the night (8 h), in the prompt.

## Placeholders in the prompt

| Marker | What the person must supply | Blocks |
|---|---|---|
| none | The prompt holds no `[you fill this in: …]`; the person's later inputs (email service, company data, retention period, photos) are visible gaps in the deliverable (`https://lista.invalid/`, `[pendiente: …]`, placeholder photos), listed in `INFORME.md` | nothing in the run |

## Review

- Linter: errors 0, warnings 2, allowed 2. Kept: P25 (about 10,800 words; an unattended lead with seven roles needs every brief's values in the prompt, and the method read as a schedule fits one night); P10 on T3's health-word list (an exact list, kept whole).
- Final lint after the fix round: errors 0, warnings 2 (P25 at about 11,500 words; P10 on T3's word list), allowed 2 (P11 on `D3`).
- Cold read (`helper seat: cold read`): 17 questions, all fixed in the prompt. Fixes: who writes files and copies fonts; the push fallback; a model stop with nobody answering; what `check-tools` is; old CLI and effort cases; legal builder after the page builder, then a page fix round placing the basic-information block; font installs by the page builder; tooling closure on fixtures (T8 and T19 not run); commit-hash labels so T19 finds tiles; T10 limited to `site`; the basic-information block exempt from T3; the WCAG inline exception in T15; seat-id roles and the probe's brief; the ledger created at step 1; reads outside the repository; restores after a fresh clone.
- Review (`helper seat: review`): not approved, 19 findings. Fixed: 1 (Phase 4 now re-judges T20–T22 on the final commit), 2 (A2's reading list), 3 (a plateau exit for the Phase 2 fix loop), 4 (the wait rule names Phase 4's end), 5 (`Continúa` after the cap), 6 (exit 2 at phase zero continues), 7 (no legal builder while a critic runs), 9 (T7's declared size, RT14's lazy loading), 10 (T5 exemptions), 11 (`fontkit` for WOFF2), 12 (foreground seats are not long operations), 13 (the DoD grep, the final-message list), 16 (no "ask your questions" in briefs). Kept as advisory: 8 (WebFetch may summarise the legal texts: A5 records unreachable or partial sources and T22 is a reviewer judgment, not a quote match), 14, 15, 17, 18 and 19 (minor), and the feasibility note that the tooling seat is the schedule's outlier. Its time is bounded by Phase 2's three-hour target and the 6 h 30 min time box. No second review round ran (budget). The Method section above is the pre-red-team draft; where it differs, the prompt and D21 hold.
- (trimmed to match the current skill: the prompt was cut from 10,793 to 3,812 words (`wc -w`). Each fact is said once; the seven appendix briefs became one Subagent contracts section; the shortened run rules are the current template's; the opening model check went. § The person's words W1, W2, W4–W7, W12, W17 and W19 point at the new text, and § Launch holds the current guide's block. Lint on the trimmed pair: errors 0, warnings 2 (P25, 3,812 words over 2,000; P10 on T3's word list), allowed 2.)
- Kept: P25 at 3,812 words, because the trimmed prompt keeps all 22 checks and the 13 run rules.
- Writing `.claude/settings.json` in the working folder was refused here (approval required); the file is `prompts/ardeta-landing-page/settings.json`, which the person commits as `.claude/settings.json`.

P11 lint-allow: `D3` is part of the product name `Vitamina D3 + K2` from brand-notes.md, not a decision id | at: - `Vitamina D3 + K2` — `60 perlas`.
P11 lint-allow: `D3` is the product-name token allowed by the number rule, not a decision id | at:   - every digit sequence is part of `D3`, `K2` or `Omega-3`, or is `90`, `60`, `18` or the current year;
- Exploration: the four `printenv` reads of this session's subagent variables, `env-check` and a `python3` contrast computation were refused (approval required, nobody answered); this session's model id comes from the system prompt: `claude-opus-5-5`. The fact-finding seats ran with no `model` parameter, so on this session's model unless a subagent-model variable was set (unread).
