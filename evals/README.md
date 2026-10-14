# Evals

End-to-end runs of the skill: a session with the skill installed is given a task's opening, a scripted
person answers from a hidden brief, and the produced prompt is linted and checked against the
scenario's assertions. These runs call a real model and cost money; the tests in `tests/` never do.

| Path | What it is |
|---|---|
| `evals.json` | the ten scenarios: each names its task, what a good run does, and its assertions |
| `tasks/<id>/` | `task.json` (the opening, the fixtures, the person's turn limit) and `hidden-brief.md` |
| `fixtures/` | the files a task copies into its bench |
| `trigger-set.json` | queries that should and should not invoke the skill |
| `harness/run_skill.py` | one run of the skill on one task in Claude Code |
| `harness/person.md` | the scripted person's prompt |
| `harness/check_assertions.py` | one run's outputs against one scenario |

## One run

From the repository root, with a bench folder outside any git repository:

```
python3 evals/harness/run_skill.py --skill skills/<name> --task evals/tasks/quick-slugger/task.json \
    --bench <empty folder> --out <results folder> --arm new --max-budget-usd 5 --model <model id>
python3 evals/harness/check_assertions.py <results folder>/quick-slugger/new/metrics.json --scenario quick-slugger
```

`--model` has no default: it is the model the skill session runs on; the skill's helper seats choose
theirs by its guideline. `--effort` is optional; without it no effort is set. `--dry-run` prints the
commands and calls nothing. The run's docstring lists every flag, refusal and exit code.

The tasks never name a real model. Where the person states one, the opening and the hidden brief hold
`{MODEL}`, which the runner fills with `--model`, and `check_assertions.py` fills an assertion's `{MODEL}`
with the model `metrics.json` records. So the prompt is checked against the model the run really used.
The tasks that test an unstated model (`harness-not-stated`, `oversized-no-cap`, `hero-loop-against-site`)
keep `{MODEL}` out of the opening and the hidden brief: the person names no model, and the scenario expects
`model=choose`.

The default allowlist admits the skill's linter, the uuid one-liner and a few read-only commands; the
runner's docstring lists them.

The metrics count, from the skill session's own transcript: the turns asking the harness question
(matched on its English wording, "Where will the run execute"), the harness guides read
(`guide_reads`) and the guidance packs read (`pack_reads`), by the Read tool only.

## Known limits

- `framing_question_turns` matches the question's English wording only, so a run that asks it in
  another language counts 0: in `stated-spanish`, 0 shows only that no question was asked in English.
- The exact `guide_reads` lists assume that a path above quick starts at least one helper seat, so a run
  for another harness also reads the Claude Code guide for those seats (`codex-unattended`,
  `no-subagents`), and that the quick lane starts none, so `other-harness-named` expects the generic
  guide alone. A guide read in part, with an offset, counts as read.
- The runner clears no subagent-model setting of the operator's shell: run the evals from a shell that
  sets none.

## A runner for another harness

Only the Claude Code runner exists. A runner for another harness provides three operations, and the rest
of the harness (the person, the prompt search, the linter, the redaction, the metrics) stays as it is:

1. **Start** a session in the bench's working folder with the skill installed where that harness loads
   skills, on the given model, and send it the task's opening.
2. **Resume** that same session with the person's reply.
3. **Read the assistant's texts** of each turn, in order, without tool results.
