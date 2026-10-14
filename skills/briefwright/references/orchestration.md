# Orchestration: how a lead leads

Read this when the seat is a lead or the method delegates. The prompt carries it adapted, in the executor's voice, without citing this file; what the template's run rules already say (fresh reviewers, dead seats, reports as text, the ledger's task list) is not said again. A task one careful agent finishes in a handful of tool calls gets one agent, and this file stays closed.

## 1. The seat

The lead owns strategy, planning, delegation, sequencing, the bar and final acceptance. On any run longer than a few tasks it does not implement, research, debug, test or review itself, and the prompt says why: everything it reads stays in its context, and that context is the run's memory. It keeps the verification housekeeping — running a check, reading a report, a search that confirms a claim. A weak result is redirected, re-briefed or split, never accepted. It never delegates the final report or the decision of what done means.

Where the harness cannot start a seat, the prompt's fallback paragraph applies: the lead builds each piece itself, in the plan's order, and the ledger stays its memory.

## 2. Assessment and seats

Before the first dispatch the lead writes in the ledger the main concepts, the facts and artefacts needed, the constraints, what the person cares about most, and the deliverable's form; then the query type — **depth-first** (one question, several perspectives in parallel, synthesised), **breadth-first** (independent parts, one seat each, crisp boundaries) or **straightforward** (one focused seat).

Fewer seats with whole tasks beat many narrow ones: each seat is overhead and a seam. Concurrency never exceeds the person's cap (recommended: at most six) nor what the lead can reconcile; small same-shape edits go to one seat in one dispatch.

## 3. The dispatch

Every brief carries, in this order: where the piece fits; the brief file as its requirements, with the exact values to use verbatim (one objective, acceptance checks, owned and forbidden files, interfaces consumed and produced, what is out of scope); decisions from earlier pieces it cannot know; the lead's resolution of any ambiguity; its checkpoint and report paths and the status reply; the tools and skills to use and avoid (seats do not inherit the lead's knowledge of them; a critic gets read-only tools by construction); "ask your questions now" and "it is always fine to stop and report BLOCKED with what you tried". Builders get no cap on tool calls; a researcher gets an approximate budget and "stop at diminishing returns". The seat's model is not in the brief: the dispatch follows the Seats and models section.

Never in a brief: the session's history, earlier seats' summaries, rubric weights or scores, the critic's identity. Artefacts travel as paths, not pasted text. Seats start no seats of their own unless the method says so and the spawn depth allows it.

## 4. Ownership and waiting

Ownership and parallel writes follow `references/methods.md` §8; shared files are the lead's, edited in sequence, and interfaces are fixed, with a stub, before parallel work. When the decomposition proves wrong mid-run, stop new work, redraw the boundaries, log the ruling.

The lead keeps working while seats run — the ledger, the next review package, reports that came in — and reconciles which seats are live, finished without a report, or stuck. Expensive evidence (test runs, screenshots, diffs) is computed outside the seat and handed over as a digest, so the seat's context goes to judging.

## 5. Reports and fix loops

A report is a set of claims; a reviewer or a command verifies them.

- **DONE** — package the artefact and dispatch a fresh reviewer with the brief, the report and the diff or artefact as files, plus the global constraints verbatim; never pre-judge ("do not flag X").
- **DONE_WITH_CONCERNS** — correctness or scope concerns are settled before review; observations go to the ledger.
- **NEEDS_CONTEXT** — a new seat with the context.
- **BLOCKED** — missing context gets context; a task too big gets split; a wrong plan gets a ruling carried into the new brief; a dead end gets a fresh seat with the ruled-out list. Never the same brief unchanged.

Findings go back to the builder while it progresses; a live builder may be continued, a reviewer never. The same findings open two rounds running change the strategy (a fresh builder with the ruled-out list, a split, a ruling). Each round closes with a fresh scoped review of the fix diff; out-of-scope observations go to the ledger and never extend the loop. At the end: one fresh whole-artefact review, one fix wave with the complete findings list, a fresh re-review, residual findings settled by logged rulings.

## 6. Rulings and finishing

An unattended lead does not wait on the person for ambiguities, plan defects or conflicts: outside the interrupt policy it decides, logs `Ruling: <what> — <why> — <cost if wrong>`, and continues. A wrong ruling costs visible, undoable rework; a stalled run costs the whole window. The ledger is appended after every dispatch, verdict and ruling: task, status, artefact paths, findings open and addressed, budget used, the next action.

The lead writes the final report itself: what was delivered and where, the evidence for each criterion, every ruling with its cost if wrong, what is below the bar and why, and genuine limitations. Scratch work is deleted only after the final review is clean and the record is committed.
