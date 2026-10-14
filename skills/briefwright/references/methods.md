# Phase 2: designing the working method

The method says how the executor works: alone or with seats, in one pass or in rounds, checked by what, stopped by what. No method is the default. Read §1–4 and §12 always; then the two or three entries of `references/method-catalog.md` the routing names; then the sections below that the design needs.

## 1. Capabilities, phase zero, fit

**List what the executor will actually have.** Each missing capability removes options; name the degradation in `decisions.md`.

| Capability | What it gates |
|---|---|
| Fresh-context subagents | independent critics, blind comparison, any checker that must not be the builder |
| Parallel dispatch | fan-out over components, judge panels, research sweeps |
| Browser or rendering | visual bars, screenshot evidence |
| Code execution | test gates, benchmarks, reproductions, cold starts |
| Persistent filesystem | ledgers, checkpoints, resume after compaction |
| Network | references, live comparisons, installs |
| Specialised hardware | GPUs, real devices |
| Connected tools (MCP servers) | a logged-in browser, a simulator: found on a personal machine, not a fresh cloud box |

Without fresh contexts there is no honest critic: the context that built the thing grades it. Where the run's harness starts no subagents, the method keeps the seats the seat rule and `review=` call for, and the prompt's fallback paragraph runs each in turn; the bar leans on deterministic checks and the person's review for whatever a fresh critic would have judged, and the reflect-back and § Method say that the reviews will not be independent.

**A capability the executor lacks is not missing; it is phase zero.** On a bare machine almost nothing exists until installed, so the run first establishes its environment and proves it:

- **Read the machine's own record first** (a setup script, a boot manifest): what is expected present, verified; what must be installed, each with its exact command. **Probe** the rest, writing the findings to a file the run rereads.
- **Install** under the person's policy: what may be installed unasked, from where, pinned how, and what to do when an install fails.
- **Establish the seeing tool** that produces the bar's evidence (a headless browser and screenshot command, a renderer with its device proven). Where the executor lacks a sense, name the proxy evidence it can read (a spectrogram, a measured value); where none can be built, the artefact gets a self-test mode.
- **Prove it with a smoke test, and read the proof**: exit zero with the device silently fallen back proves nothing.
- **Adapt rather than stall.** For each capability that may be missing, the prompt names the degraded path up front ("if you can …; if you cannot …").

**Check that the work fits the machine.** Multiply out the expensive operation (renders, builds, suites, model calls): how many times, what one costs on *this* machine, times the rounds the method implies, against the agreed run size. When it does not fit, say so with the arithmetic and offer, in order: a cheaper operation per round (the expensive check once at delivery), the run split across machines, the whole run moved, or — with the person's agreement — a smaller bar.

**Check the proportions.** Verification must be smaller than what it verifies. Lower the evidence rung instead (critics that read the artefact, one script, a few named cases, the expensive check once) and record in `decisions.md` the rung taken, the one declined, and the confidence that costs.

## 2. Verification ladder (decide this first)

Build the method around the strongest evidence this task allows:

1. **Deterministic oracle** — a test suite, type checker, diff gate, golden file, clean build, schema validator.
2. **Execution evidence** — the thing was run and its output captured: a reproduction, a benchmark number, a screenshot at a named viewport, a cold-start reopen.
3. **Reference comparison** — blind, side by side, against a real named reference, on named dimensions, by a seat that did not build it.
4. **Rubric judgment** — a fresh critic scoring named criteria with cited evidence; weakest, strengthened by blindness, fresh context, citations and default-to-fail.

"It looks right" is not a rung. Three moves raise one: **feel as an invariant** (a frame budget, a maximum input lag, a contrast ratio); **determinism** (a fixed seed, so two runs can be diffed); **ablation** (turn the effect off and watch the result get measurably worse).

**The evidence map, read backwards.** One row per criterion: who checks it, the exact artefacts that checker receives, the observation that decides it. Is each row decidable from *only* what that checker is handed? Performance is invisible in a screenshot. A failing row gets the artefact that makes it observable, a checker that can see it, or removal from the bar, said aloud. The map goes into the prompt's bar and `decisions.md`. Where the oracle is weak, layer bars: correctness, quality, a budget (latency, size, cost), and a floor never traded (accessibility, safety).

## 3. Goal, bar, wait

- **Goal** — the outcome in one sentence, a destination, not a route.
- **Bar** — when it is done: each criterion specific, measurable, achievable within the run and relevant, with its check. "Safe outputs" fails all four; "fewer than 0.1% of 10,000 trials flagged by the content filter" passes. A bar may be aspirational; the loop pulls toward it and stops on plateau. The bar names what a weak result looks like, so every critic knows the failure it hunts.
- **Wait** — never done before the bar is met with evidence the checker observed; the wait rule points at the bar's ids rather than repeating them.

With no fitting bar (a spike, a recommendation), write the goal and the deliverable's shape, record why, and still give a stop condition (a time box, a question answered). "Measured against X" does not authorise an expensive instrument: price the cheapest evidence that settles it beside the expensive one and let the person choose.

## 4. Routing

Answer from the decisions log; the answers point at catalog entries whose fit rules confirm or veto them.

1. A binary, machine-checkable exit? On quick or standard work, one agent converging on it (M3, M4). On deep work the exit is the bar, not the seat: the lead still does not implement, and seats converge on it (M5, M7).
2. Subtasks predictable up front? Plan and execute (M5) or phases with gates (M8); otherwise orchestrator and workers (M7).
3. Subjective quality with a real external reference? Blind comparison loop (M6). Without one: find one (M2), or criteria the person signed (M9); a critic never invents the reference.
4. Unattended above quick? Recoverability, a ledger and the interrupt policy become mandatory in any shape (§12).
5. Finding things of unknown count? Discovery until dry (M10).
6. Large and decomposable into separately judgeable pieces? Disjoint owners and an integration pass (M6, M7); otherwise one sequential owner.
7. Is a decision the deliverable? Options fan-out (M13) or research ending in a decision (M2).
8. Will the prompt run many times? Meta loop with a holdout (M14).
9. Broken, cause unknown? Diagnosis (M18).

Vetoes that send a task to a simpler method or back to the interview: the person cannot describe success; nothing can inspect the result; mistakes are irreversible or expensive; one careful pass is cheaper than the loop.

## 5. Catalog index

In `references/method-catalog.md`: M1 single careful pass (the default until something earns its cost) · M2 research, derive the bar, build · M3 converge to a deterministic exit · M4 tests first, slice by slice · M5 plan, fresh implementer per task, review · M6 blind comparison loop against a real bar · M7 orchestrator and workers · M8 phased pipeline with gates · M9 evaluator-optimizer · M10 discovery until dry · M11 adversarial verification · M12 self-refine in one context · M13 design it twice · M14 meta loop · M15 backlog loop · M16 wayfinding · M17 handoff to a person · M18 diagnosis.

## 6. Techniques à la carte

Any shape can carry these; name what each rests on before taking it (§7). Mechanics in `references/orchestration.md` and `references/contracts.md`: a **blind critic, fresh each round** (one that saw the last round grades the improvement, not the work); **context hygiene** (builders never see weights, scores, verdict history or who judges); **ownership contracts**; a **ledger** with rulings; **checkpoints**; a **cold start** (reopen the deliverable from a clean invocation, rerun the decisive check); **held-out checks** and a **frozen oracle** the builder cannot edit without a logged ruling; **regression labels** each fix round; **structural escalation** on plateau; a **smoothing pass** after parallel builds, judged fresh; **headless seats**, one non-interactive session per seat in its own bench under the bench root (§10), by the harness guide's `headless-line`, where it has one.

## 7. Composition

A catalog entry is a shape for the whole run; a technique is a piece that drops into any shape. One shape, or two when you can name which phase each owns; pieces, as many as earn their place. A single careful pass with a frozen oracle, a cold start and an honest report is a good design. The prompt carries mechanics, never catalog names.

A piece lifted out of its method can stop working: a blind critic without a fresh context is the builder in another voice; a plateau rule needs a measurement comparable between rounds. Nested loops multiply their cost; put a cheap deterministic gate before any expensive fan-out. A method whose fit rules fail is removed, however impressive.

## 8. Parallelism

**First: what does each concurrent seat write, and can the writes combine?** Text and code merge; a 3D scene, a design file, a binary, a database or an image does not — the last save wins. For an unmergeable target the prompt names **one writer** applying the others' patches in sequence, **separate artefacts** composed by an integration step with its own review, or **sequential ownership** with the handoff stated.

Readers fan out; writers own disjoint files, in separate worktrees when they share a repository. Pieces that must agree (timings, dimensions, names, data) read **one source of truth**. The spine is built and judged before anything fans out. Concurrency is the person's cap (area 10), at most what the lead can reconcile.

## 9. Stop rules and budgets

Every loop in the prompt — the late and small ones included — has exactly these exits: **success** (the bar met with observed evidence); **plateau → strategy change** (two rounds in a row that improve nothing trigger a named structural change: a fresh seat with the ruled-out list, a split, a different approach, a ruling; repeating the round is never the answer); **plateau again → honest delivery** (the best checkpoint, never a regressed one, with the gaps); and the **interrupt policy**.

Counts appear only as a person's cap, which carries its honest-delivery clause and keeps budget for the final review, or as a safety net far above the expected run. Every risky choice names its fallback and when to take it — a time or a number of failed attempts. "No cap" never licenses a design longer than the agreed run size. For the design note: seats ≈ pieces × rounds × 2, plus integration and final verification; quote a range.

## 10. Models and the launch

Each seat's model follows the guideline the harness guide's `seats-models` block puts in § Seats and models, chosen at each start by the harness's own means; a model or effort the person named is set at launch, as the guide's §3 and §4 write it, and used. The method names no model of its own. Where the harness cannot start a seat, the template's fallback paragraph says what the executor does instead.

Decide, and record in `decisions.md` § Launch and § Accepted defaults, as the guide's §4 says: the permission setting of an unattended headless launch (the guide's narrow default; its wide one only when the person confirms a disposable sandbox); the allowlist, where the harness has one, starting with the run's own commands and covering every command the method and the bar run; a budget cap per call with the person's cap, where the harness has one; a fresh session id where the launch takes one; with headless seats, the bench root and per-seat budgets; and, where seats cannot start seats of their own, a method in which the lead dispatches every seat itself.

**Verification wording.** V1, above quick: "Name each check as a command and its expected result, and put its output in the report." No generic self-check line goes beside it: a named check with its output is evidence, a reminder to verify is not. V2, beside the step that dispatches a review seat when `review=fresh`: "Independent review is a fresh seat the method schedules, not a self-check." Every critic, reviewer and judge brief asks for every issue: "Name every problem you see, each with how much it matters and how sure you are. Keep the minor and the doubtful ones: sorting them is a later step." A lead that must not implement carries, in Method: "You are asked to delegate: every task of the plan goes to a seat. Give one task to one seat; do not split a task one seat can finish across several."

## 11. Presenting the design

The design goes to the person inside the final reflect-back (`references/interview.md` §8), readable at a glance: the method and why it fits; the goal; the bar and its verification, or why there is none; the seats and what each owns; the stop rules and what happens past the budget; what is delivered where; the permission mode and allowlist when unattended; the bench root with headless seats; the alternatives the fit rules removed. Their yes is the gate into writing; record it under § Method.

## 12. Ceremony by seat structure

The prompt carries the least machinery that keeps the evidence rule true, and the whole
apparatus where nobody watches or seats exist. Take the row of the framing's `seat=` (quick is always `alone`, attended or not),
then add every modifier that holds. The linter's P13, P23, P36 and P37 and the template's comments follow this table.

| Structure | Seats and models | Ledger and Progress | Run rules | Verification | Plateau |
|---|---|---|---|---|---|
| quick | none | no | RS1, RS13 | the bar's commands | short |
| `alone`, attended | none | no | RS1, RS7, RS13 | V1 | short |
| `alone`, unattended | none | yes | RS1, RS7, RS13 | V1 | short |
| `implementer` | the guide's seats-models block and the fallback paragraph | yes | RS1, RS4, RS6, RS7, RS10, RS13 | V1 | full with rounds, else short |
| `lead` | the guide's seats-models block and the fallback paragraph | yes | RS1, RS2, RS3, RS4, RS6, RS7, RS10, RS13 | V1, §10's delegation sentence | full |

| Modifier (not on quick) | Adds |
|---|---|
| `review=fresh` | RS5, RS7; V2 |
| deep, unattended or run=multi-session | ledger and Progress; RS8, RS9, RS10, RS11 |
| run=one-day | ledger and Progress; RS10 |
| machine=disposable | RS12 |
| a long operation | RS8 |

Checkpoints per seat (RS3) only under a lead, the ledger being the checkpoint of a run without writing seats; reviewer
rounds only with `review=fresh`, each loop closed by its plateau line; the Budget line goes in only with a person's cap or
a headless launch. Quick unattended adds only the quick template's unattended line.

`alone`: the executor dispatches no subagent (every quick prompt); `implementer`: it builds and dispatches only the helper seats the method names (explore, review, critique, verify); `lead`: it delegates the building. A method with no helper seat is `alone`, unless `SKILL.md` Phase 2's lead rule applies, whose lead delegates the building. `alone` means `review=none`, a size other than deep and one session; anything else takes the implementer or lead row. On attended work the person reviews: `review=fresh` only when the person asks for a reviewer or the change is hard to reverse, security-sensitive or touches data. The implementer row keeps a ledger because its seats' reports, rulings and the fallback paragraph's marks need one.
