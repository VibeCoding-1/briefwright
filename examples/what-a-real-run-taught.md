# What a real run taught

Source: the first prompt this skill wrote that was then run for real and watched — a long, unattended run in a cloud sandbox, led by one session that delegated to subagents — and the rules its later runs had to add. Every lesson below now lives in a rule the skill's template carries; this page says why each rule exists, so nobody rewrites it into a weaker form.

## The prompt, in three lines

- A lead of one long working session in a cloud sandbox, told not to implement and to delegate through a menu of models, picking one per dispatch.
- About 4,400 words in 78 lines, paragraphs of about 700 characters each; an eight-step method (environment, research, spine, pieces, self-check, comparison verdict, improvement loops, delivery).
- Its dispatch paragraph, kept as history with the models' names left out:

```history
Dispatch subagents for parallel or isolated work, as many at a time as you can reconcile (typically two
to five), and name the model in every dispatch. The choice is yours among [three models, each with a line
on what it fits]. A model this prompt names for a role is a suggestion.
```

It carried the run through its first five steps, environment to self-check. What follows is what it could not see coming.

## The lessons

Each: what happened → what the prompt said → the rule that now carries it.

### 1. A reviewer reused across rounds

**What happened.** The person watching the cloud session saw a ledger line reading "review round 2 (same reviewer)": a reviewer resumed for its second round, grading the improvement it had asked for rather than the work.
**What the prompt said.** "A fresh reviewer per piece" — per piece, not per round, which left a resumed reviewer allowed. The fix came mid-run, as a recorded decision, and only for the comparison step.
**The rule now.** Run rules, *A fresh reviewer every round*: every review, critique and re-review is a new dispatch that has not seen earlier rounds; never resumed, never sent a follow-up, even after an interruption; never started as a seat that inherits the lead's conversation.

### 2. Usage limits cut a review round

**What happened.** The account's usage limit killed running subagents mid-task, review rounds included — ten workers at once on one hit. The lead re-dispatched them to continue the same unfinished round: the right instinct, with nothing written to hold it.
**What the prompt said.** No usage-limit protocol for the run (the one line on a limit hit, added mid-run, covered the comparison reviewer alone), and no per-seat checkpoint to restart from.
**The rule now.** *Usage limits* (dispatch nothing new; record which seats were running and where their checkpoints are; commit and push what exists; resume a few seats at a time, restarting each dead one fresh), *A dead seat restarts fresh* (from its checkpoint, never resumed by id; twice dead means a smaller task), and *A checkpoint per seat*, created before the seat's first read.

### 3. Report writes refused

**What happened.** On later runs the harness refused some seats' writes of their report files; the detail survived only because the seats returned it and the lead filed it by hand.
**What the prompt said.** Nothing on how a report reaches the lead; the skill's builder contract had each seat write its report file and reply with a short status only, so a refused write loses the report.
**The rule now.** *Reports come back as text*: every seat ends with its full report as its final message; where the write is refused, the lead files the returned text, marked as filed by the lead. The status block opens that message.

### 4. A model named in text selects nothing

**What happened.** The next runs' rules replaced the menu outright by fixing the models themselves. Later measurement showed why a menu in prose cannot work: text a subagent reads does not choose the model that serves it. Only the harness's own means do — a field of the dispatch, an agent definition's model setting, a launch setting that forces every seat onto one model — and an agent definition that named another model pulled a seat off the lead's model even with the launch setting in place, until the launch forced it. Exit codes stayed zero throughout; only the session records showed which model had served.
**What the prompt said.** "Name the model in every dispatch", a menu with fit lines, and "a model this prompt names for a role is a suggestion".
**The rule now.** A model is chosen by the harness's own means, never by a brief's text. The prompt's *Seats and models* section, written from the harness guide, gives a guideline — the strongest model available for planning, hard building and review, a faster one for searches, simple edits and mechanical checks — and says how this harness makes each choice real: the dispatch's own model field where it has one. A model the person names is set at launch. For a while the skill went further, putting every seat on one model and reading the session records at every close to check which model had served; that rule and its check were later removed to keep the skill simple, and this lesson is why the choice still goes through the harness's field rather than through prose.

### 5. "Two to five" against the person's cap

**What happened.** The person's working rule was at most six subagents in parallel; the prompt's range was superseded by it.
**What the prompt said.** "As many at a time as you can reconcile (typically two to five)" — a number the writer chose, not one the person gave.
**The rule now.** The interview asks the parallel cap (recommended: at most six seats at a time) and the prompt carries the answer; no range is invented.

### 6. Long waits inside the turn

**What happened.** A lead waited on its seats inside its own turn; when that wait was interrupted, twice in one day, the turn ended and every background seat died with it, and the blocked turn had done no other work meanwhile.
**What the prompt said.** Nothing about operations that outlast a turn.
**The rule now.** *Long operations run detached*: anything over ten minutes runs in the background with a log and a finish signal, checked at intervals while other work goes on; attended, the lead says once that an interruption stops every running seat; in a headless run it keeps the turn open while work runs, because an ended turn ends the run.

### 7. Figures and timestamps estimated

**What happened.** Two sets of ledger entries, days apart, carried times the lead estimated instead of reading the clock, running up to about two hours ahead; both needed correction entries.
**What the prompt said.** Nothing on where figures and times come from.
**The rule now.** *Times from the clock* (`date -u`, never estimated) and *Evidence from commands* (every figure from a command whose output was kept; a check not run is reported as not run).

## What to take from it

The prompt's interview, method and bar held; what broke was survival — freshness, limits, reports, models, waits, clocks. Those are now the template's Run rules and its Seats and models section, scaled by run size, so no prompt depends on the writer remembering them.
