# Method catalog

The shapes a run can take. Read the two or three the routing in `references/methods.md` §4 points at, not all of them. The names are for your reasoning: the prompt describes mechanics, never labels. A shape reshaped for the task, or one nobody wrote down, is right whenever the routing points there. Every loop in a shape exits on success, plateau (answered by a structural change) or the interrupt policy (`references/methods.md` §9).

### M1. Single careful pass

One agent, the full specification up front, verification before any claim of done, no loop.

- Fits: quick and many standard tasks; anything one competent pass with the full brief can finish; the default until something else earns its cost.
- Does not fit: subjective quality with a real bar; discovery of unknown size.
- Mechanics: the full brief; each criterion verified with its named command or artefact before the report; the report carries evidence, not claims.

### M2. Research, derive the bar, then build

A first phase studies the reference (a product, a codebase, a literature) and consolidates a feature matrix and an acceptance-test plan; building starts once that artefact is accepted.

- Fits: rebuilding or beating an existing product; a bar the person cannot enumerate but a reference can reveal.
- Does not fit: a bar the person already holds precisely; tiny tasks.
- Mechanics: researchers fanned out by facet (features, API, UI, workflows, edge cases, complaints); one consolidation step writes the bar document every later phase cites; attended, the person reviews it before the build; unattended, it is accepted and labelled as derived in the report.

### M3. Converge to a deterministic exit

One agent iterates until a machine check passes: tests green, build clean, diff gate satisfied, benchmark over threshold.

- Fits: a truly binary exit one agent can reach; regressions; migrations; "make the suite pass".
- Does not fit: exits that only look binary (the runaway-loop trap); subjective quality.
- Mechanics: the check runs every round; the oracle is frozen (no editing tests, cases or thresholds; a wrong test is reported, not changed); general solutions, never hardcoded passes; the plateau rule on identical failures; a branch or worktree to work in.

### M4. Tests first, one slice at a time

Behaviour pinned by a failing test at an agreed seam, then the least code to green, then the next slice.

- Fits: behaviour a test can pin; well-understood interfaces; regression fixes.
- Does not fit: exploratory prototypes; work with no testable seam (feel, prose).
- Mechanics: seams agreed first; the failing test run and seen red; minimal code; green; refactor after review; a regression test shown to fail without the fix.

### M5. Plan, then a fresh implementer per task, with review

A written plan of small tasks; each goes to a fresh implementer with a brief file, then a fresh reviewer (spec, then quality); fix rounds until clean or plateau; a final whole-branch review.

- Fits: multi-task implementation with a plan; mostly independent tasks; a need for an audit trail; work that outlives one context.
- Does not fit: tightly coupled work that cannot be sliced; tiny changes.
- Mechanics: a plan header (goal, architecture, stack, global constraints verbatim); tasks with owned files, interfaces and checks; a brief file per task; the review and fix loop of `references/orchestration.md` §5; a ledger with rulings.

### M6. Blind comparison loop against a real bar

Per piece judged apart, rounds of a builder and a fresh critic who inspects the real artefact against a named reference; closure is computed from the critic's verdict, never declared.

- Fits: quality is the point; the artefact can be rendered, run or read; a real reference exists; large surfaces that split cleanly (UI, scenes, games, sections of writing).
- Does not fit: no real reference (the critic would invent one); nothing inspectable; irreversible or expensive mistakes; small tasks; and nothing to polish yet — the loop needs a base, so with none the first increment builds one.
- Mechanics:
  - **The bar** is a reference named, fetchable and comparable (`references/interview.md` §3, area 7), pinned when the run starts.
  - **Spine first**: the piece whose rules the others inherit (tokens, a data model, a storyline) runs alone before the rest. Pieces run in parallel only on disjoint write scopes; a monolithic artefact (one document, one scene, one deck) is always sequential.
  - **Each round, one fresh critic** (`references/contracts.md` §2) judges a pinned commit or snapshot, never the live tree: from round 2 it first compares the previous and current versions under neutral labels, then judges the current one with evidence it gathered itself.
  - **Closure, void verdicts, the Goodhart flag, plateau and the final re-verify** follow `references/contracts.md` §7; on plateau a structural pass, never polish.
  - **The end**: an integration critic on the seams only, then one fresh critic on the whole; hold back budget for that tail.

### M7. Orchestrator and workers

A lead assesses the task, decides the subtasks, briefs seats with one objective each, dispatches in parallel where writes are disjoint, reconciles, and writes the synthesis itself.

- Fits: subtasks that cannot be predicted; breadth-first research; multi-file changes with disjoint ownership; long builds where the lead must preserve its context.
- Does not fit: shared mutable state or one file; latency-critical work; a task one agent finishes in a handful of tool calls.
- Mechanics: `references/orchestration.md`, briefs from `references/contracts.md`.

### M8. Phased pipeline with gates

Stages in order (analyse, design, build, verify), each closed by a gate whose failure loops back to the producer; a cheap gate before any expensive fan-out of reviewers.

- Fits: deliverables with natural stages and a check per stage; research-then-build; production runs with a build order.
- Does not fit: exploratory work with unknown stages.
- Mechanics: each phase closes with something that runs end to end, committed at its close, so the run is usable wherever it stops; a baseline captured before any change; a dead reviewer is a failed gate, not a pass; each stage's artefact named and durable.

### M9. Evaluator-optimizer against fixed criteria

A generator and a separate critic with frozen criteria; rounds until the critic approves or the plateau rule fires.

- Fits: clear criteria and feedback that measurably improves the work — writing, plans, code against a signed bar, prompts.
- Does not fit: no criteria; a critic that cannot inspect the real artefact; taste with no reference and no signed criteria.
- Mechanics: the goal frozen after round one; a fresh critic each round with the compact verdict (`references/contracts.md` §8); oscillation noticed and ruled on; a finding rebutted once and re-asserted without new evidence goes to the lead as a ruling, or to the person when it changes the project.

### M10. Discovery loop until dry

Rounds of finding (bugs, defects, flaky tests, audit findings) with a seen-set across rounds; dry when a full rotation of lenses finds nothing new.

- Fits: finding things of unknown count.
- Does not fit: "is it good enough yet" questions (M6, M9).
- Mechanics: every finding deduplicated against the seen-set; lenses rotated before declaring dry; each finding with location, failure scenario and confidence, triaged separately; what a cap dropped is reported.

### M11. Adversarial verification

Independent skeptics try to refute a claim or a design; agreement between independent seats is the signal.

- Fits: before irreversible decisions; findings that need confirmation; high-stakes reviews.
- Does not fit: trivial changes; anything a deterministic oracle already settles.
- Mechanics: the full idea including rejected alternatives; no hint of the wanted conclusion; lensed critics plus one unlensed; confidence on every finding; deduplication and severity calibration in synthesis.

### M12. Self-refine inside one context

Draft, critique against explicit criteria, revise, in one agent.

- Fits: a drafting step inside a larger method; single-context work with no second agent.
- Does not fit: the only verification of anything that matters — self-evaluation is lenient.
- Mechanics: explicit criteria; stop when a pass changes nothing material; notes on what changed and why.

### M13. Design it twice

Several seats each design under a different constraint from the same brief; compare on named dimensions; recommend or hybridise.

- Fits: architecture or interface decisions with several plausible shapes; visual direction; best-of-N generation.
- Does not fit: one obvious design.
- Mechanics: identical briefs but for the constraint; a fresh judge or the lead compares on named dimensions; the person picks when the decision is theirs.

### M14. Meta loop

Run a candidate prompt over a test set, score it against ground truth with a separate evaluator, rewrite from the failures, re-check on a held-out set.

- Fits: a skill, a subagent brief, a classifier prompt — anything that runs many times.
- Does not fit: one-off prompts; no test set or holdout.
- Mechanics: a fixed holdout; a small anchor set the person labelled; the evaluator separate from the optimizer; the person picks the winner; evaluator-versus-person disagreement watched.

### M15. Backlog loop with a completion promise

The same prompt re-fed against a backlog of verifiable stories, one story per iteration, a progress log, and a completion promise made only when literally true.

- Fits: a well-defined backlog with automatic checks; greenfield work the person can walk away from.
- Does not fit: stories that each need the person's judgment; unclear success.
- Mechanics: stories as structured data with a pass flag; learnings appended to the log; a breaker on no progress; a sandbox.

### M16. Wayfinding

A shared map of decision tickets; one ticket resolved per session; fog becomes tickets as the frontier advances; a spec once the way is clear.

- Fits: huge or foggy efforts across sessions or people.
- Does not fit: a well-scoped feature.
- Mechanics: the destination named first; decisions made, not yet specified, and out of scope kept apart; ticket kinds (research, prototype, questions, task) with blocking edges.

### M17. Handoff to a person

A questionnaire or a step-by-step script for what only a person can decide or do (credentials, dashboards, a sign-off).

- Fits: a decision belonging to someone outside the run; a manual step.
- Does not fit: facts an agent can look up.
- Mechanics: one idea per question with why it matters; a placeholder in the prompt marked with the open-question id; the executor told what to do at the gap.

### M18. Diagnosis

A defect exists and nobody knows why. The shape is "find it", not "fix it".

- Fits: a bug of unknown cause; intermittent or environment-specific failures; a regression within a range of changes; performance that degraded unexplained.
- Does not fit: a known defect with an obvious fix; defects of unknown count (M10); a failing suite whose cause is understood (M3).
- Mechanics: **a reliable reproduction first** — a run that cannot reproduce says so, because a fix for an unreproduced bug is unfalsifiable. Narrow by bisection over a range of changes, or by elimination (halve the input, disable half the configuration). State each hypothesis and the result that would refute it before testing it. Prove the fix by removing it and watching the check fail. Record what was ruled out; when the reproduction resists, a fresh seat with the ruled-out list takes over.
