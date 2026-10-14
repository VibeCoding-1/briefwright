# Harness guide: Claude Code

How a run on Claude Code gives its seats their models, how it is launched, and what it allows. Each line of §1–§4 ends with its source: `[KEY #anchor]` is a section of a page listed in §5, and `[skill]` is this skill's own rule, or an observation no page states.

## 1. The harness

- **Instruction files** (`{INSTRUCTION_FILES}`): `CLAUDE.md`, or `AGENTS.md` where no `CLAUDE.md` sits in the working folder or above it; reading `AGENTS.md` needs CLI 2.1.277 or later [CC-MEM #agents-md].
- **Subagents** start through the Agent tool; its old name, Task, still works as an alias [CC-SA #restrict-which-subagents-can-be-spawned].
- A fork inherits the whole conversation, so no review seat is a fork [CC-SA #how-forks-differ-from-other-subagents].
- Nesting depth is `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`: 3 when unset; 1 turns nesting off [CC-SA #let-subagents-spawn-their-own-subagents].
- `--disallowedTools Agent` takes subagents away from one session [CC-SA #disable-specific-subagents; CC-CLI].
- **Model:** `--model` sets the session's model, by a family alias or a full model name [CC-CLI].
- An Agent dispatch's `model` takes a family alias, and the alias of the session's own family runs the session's exact model; a dispatch without one runs on the session's model unless the environment sets a subagent model [CC-SA #choose-a-model].
- Built-in agents may run another model [CC-SA #built-in-subagents].
- **Effort:** `CLAUDE_CODE_EFFORT_LEVEL` wins over `--effort`, `/effort`, saved settings and an agent file's `effort:` [CC-ENV #precedence; CC-MC #set-the-effort-level].
- **Headless:** `claude -p` runs without interactive mode and exits, so, with no goal set, a turn that ends ends the run [CC-CLI; CC-GOAL #run-non-interactively].
- `--resume <id>` continues a session; `--max-budget-usd` caps one call [CC-CLI].
- Under `--permission-mode acceptEdits`, file edits and common filesystem commands such as `mkdir` run unasked, while other shell commands need an `--allowed-tools` rule; in a `-p` run, where nobody answers a prompt, a call nothing allows is denied [CC-HEADLESS #auto-approve-tools; CC-HEADLESS #turn-off-permission-prompts-in-unattended-runs].
- `--allowed-tools` takes permission rules, as one comma-separated argument in the documented example; a trailing `*` makes a rule a prefix match [CC-HEADLESS #create-a-commit; CC-CLI].
- The CLI splits that list at a comma or a space that follows a `)`, so no rule can hold a `)` followed by a comma or a space; observed in the CLI's parser, not documented [skill].
- **Web:** a cloud environment's variables, set in its settings, are read by each new session of that environment; an open session keeps the old values until its VM is restored or rebuilt [CC-CLOUDENV #configure-your-environment; CC-CLOUDENV #set-environment-variables].
- In a cloud session `/model <id>` sets the model, from CLI 2.1.205 in the session's environment [CC-WEB #manage-context].
- **Keep-going command:** `/goal <condition>`, at most 4,000 characters, attended or under `-p`, where one invocation runs the loop to completion [CC-GOAL #set-a-goal; CC-GOAL #run-non-interactively].
- Its evaluator, run after each turn, is the small fast model, not the run's; no block here sets a goal [CC-GOAL #how-evaluation-works; skill].

## 2. A named model, and your helper seats

- **`{MODEL_ID}`**, only where the person named a model, is its id or alias as `--model` takes it; with neither, `[you fill this in: the model id]` [CC-MC #model-aliases].
- **The ask tool** is `AskUserQuestion`: 1–4 questions a call, 2–4 options each, a `header` of at most 12 characters, and an `Other` row the tool adds for the person's own text [CC-ASK #limitations; CC-ASK #question-format; CC-TOOLS #askuserquestion-tool-behavior].
- No subagent has it, and a `-p` run, where nobody answers, denies it: no mode auto-approves it [CC-ASK #limitations; CC-PERMMODES #actions-no-mode-auto-approves; CC-HEADLESS #turn-off-permission-prompts-in-unattended-runs].
- **A helper seat** is a new Agent dispatch of the `general-purpose` type, never a fork, described as `helper seat: <seat>` [CC-SA #how-forks-differ-from-other-subagents].
- Its `model` is the family alias the guideline gives its work: the strongest the Agent tool's description lists for the red team, cold read and review, and a faster one for fact-finding [CC-SA #choose-a-model].
- **With `--disallowedTools Agent`, or a dispatch refused,** `SKILL.md`'s sequential fallback applies [skill].

## 3. Seats and models in the prompt

- Implementer and lead: `seats-models`, then, with headless seats, `headless-line`, then the template's fallback paragraph [skill].
- Alone: no section [skill].
- Fill every slot. Keep an `{EFFORT: …}` fragment's text only where `effort=` names a level, a `{MODEL: …}` fragment's only where `model=` names a model and a `{NO_MODEL: …}` fragment's only where it is `choose`, and drop the braces and the name [skill].
- In `headless-line`, keep the `{BENCH_CLI: …}` text on `launch=interactive` or `headless` and the `{BENCH_OTHER: …}` text on `cloud`; a `{RUN_DIR}` the person gave as an absolute path replaces `{FOLDER}/{RUN_DIR}` [skill].
- A command the run executes holds no shell variable outside single quotes: in a `-p` run CLI 2.1.291 refused `mkdir` and `cd` on a path holding one, even inside an `--add-dir` folder (observed, not documented). So every path in it is literal, `{RUN_DIR}` and `{BENCH_ROOT}` included, and with headless seats `folder=` is written out, since `headless-line` reads each brief from `{FOLDER}` [skill].

### seats-models

```text
{NO_MODEL:Give each seat the model its work needs: the strongest available for planning, hard building and review; a
faster one for searches, simple edits and mechanical checks. Choose it at each dispatch with the Agent tool's `model`
parameter, which takes a family alias its description lists; a dispatch without one runs on your model.}{MODEL:Every
seat runs on `{MODEL_ID}`, the model the person chose, which the launch set for you: on each Agent dispatch, pass as
`model` the alias of your own model's family, which runs your exact model.}
```

### headless-line

```text
**Headless seats.** Each runs in its own bench under `{BENCH_ROOT}`, made and entered in two separate calls: first `mkdir -p "{BENCH_ROOT}/<seat-id>"`, then `cd "{BENCH_ROOT}/<seat-id>" && env -u CLAUDE_CODE_SESSION_ID claude -p {MODEL: --model {MODEL_ID} }{NO_MODEL: --model <seat-model> }{EFFORT: --effort {EFFORT} }--session-id <uuid> --max-turns <n> --max-budget-usd {SEAT_BUDGET_USD} --permission-mode acceptEdits --allowed-tools '<the seat's allowlist>' --output-format json < "{FOLDER}/{RUN_DIR}/briefs/<seat-id>.md"`.{NO_MODEL: `<seat-model>` is the model the guideline above gives the seat's work, as `--model` takes it.}

Never join the two calls: Claude Code wants an explicit approval for a `cd` and a write in one command, and nobody can give it in `-p`. Write the brief to that file first: it goes in on stdin, never as an argument, where the shell would run its backtick spans and `$(…)`. In the command, each `'` of the seat's allowlist is written `'\''`. {BENCH_CLI: `{BENCH_ROOT}` is outside the repository, and the launch added it to this session with `--add-dir`; if the `cd` is refused, it did not: stop that work and tell the person.}{BENCH_OTHER: This run's launch adds no folder to the session, so `{BENCH_ROOT}` is inside the working folder: keep it out of git (`.git/info/exclude`) before the first seat. A seat there is not isolated from the project (it inherits at least the project's skills): say so beside its results.}

Make each `<uuid>` fresh first with `python3 -c 'import uuid; print(uuid.uuid4())'`.
```

### reviewer-facts

```text
In Claude Code {MODEL:the launch sets `{MODEL_ID}` with `--model {MODEL_ID}`, and each seat is an Agent dispatch passing the alias of that model's family}{NO_MODEL:the launch names no model, and each seat's model is chosen at dispatch with the Agent tool's `model` parameter, by the guideline in Seats and models}{EFFORT:; `--effort {EFFORT}` sets the effort}. No seat is a fork. An unattended headless launch uses `claude -p` with `--permission-mode acceptEdits` and an allowlist, and its loop resumes the session at most three times.
```

## 4. The launch

- `launch=interactive` takes `launch-attended`, `headless` takes `launch-headless` and `cloud` takes `launch-cloud`; `other` takes the generic guide's `launch-headless` [skill].
- Keep a `{LOOP: …}` fragment's text above quick and drop it on quick, whose run keeps no ledger for the loop to read [skill].
- `{PERMISSION_MODE}` is `acceptEdits`; `bypassPermissions` only when the person confirms a disposable sandbox with nothing of value and no credentials beyond the run's own, which the page requires to be a container, a VM or the sandbox runtime, run as a non-root user [CC-PERMMODES #common-setups].
- `{ALLOWED_TOOLS}` starts with the run's own commands, `Bash(date *),Bash(mkdir *),Bash(pwd)`; no rule prints the whole environment or reads variables by a prefix, which would admit a credential variable [skill].
- grep and sed take no rule: under `acceptEdits` read-only commands, grep and a sed that writes nothing among them, run unasked inside the session's folders, which no allow rule narrows, and `Bash(sed *)` would add `sed -i` [CC-HEADLESS #auto-approve-tools; CC-PERMISSIONS #read-only-commands; skill].
- When the run commits, `Bash(git status *),Bash(git diff *),Bash(git log *),Bash(git add *),Bash(git commit *)`; never `Bash(git *)`, which admits every push and a `git -c` that runs any program; a push only as `Bash(git push origin <the run's branch>)`, where a decisions-log row records the person allowing it [CC-HEADLESS #create-a-commit; CC-PERMISSIONS #wildcard-patterns; skill].
- With headless seats, `Bash(env -u CLAUDE_CODE_SESSION_ID claude -p *)` and `Bash(python3 -c 'import uuid; print(uuid.uuid4())')`, in `headless-line`'s order [skill].
- Then every command the method and the bar run beyond file edits, such as `Bash(python3 -m pytest *)` [skill].
- Show the list with the design as written here; only in the launch, where it sits inside single quotes, write each `'` in it as `'\''`, so the uuid rule there reads `Bash(python3 -c '\''import uuid; print(uuid.uuid4())'\'')` [skill].
- `{EXTRA_FLAGS}`, each flag followed by a space: `--max-budget-usd` with the person's cap, per call (the block makes at most four calls), and with headless seats `--add-dir "{BENCH_ROOT}"` [CC-CLI].
- `{BENCH_ROOT}`, with headless seats, is a literal absolute path, never `$HOME/…` (§3): on the CLI a new folder outside the repository, by default `<the parent folder of {FOLDER}>/benches/<task-id>`, or one the person names, made by `{BENCH_MKDIR}` (`mkdir -p "{BENCH_ROOT}" && `) and added by `{ADD_DIR}` (` --add-dir "{BENCH_ROOT}"`), since a `cd` outside the session's folders is refused (observed, not documented); on the web `{FOLDER}/.benches`, as `headless-line` says; without headless seats both are empty [skill].
- `{SESSION_ID}` is a fresh id from `python3 -c 'import uuid; print(uuid.uuid4())'`; `{SEAT_BUDGET_USD}` is the method's per-seat budget [skill].

### launch-attended

```text
Claude Code CLI, attended:
    {BENCH_MKDIR}cd "{FOLDER}"
    claude{ADD_DIR}{MODEL: --model {MODEL_ID}}{EFFORT: --effort {EFFORT}}
  then paste the contents of prompts/{TASK_ID}/master-prompt.md as the first message.
```

### launch-headless

```text
Claude Code CLI, unattended on this machine. Permission mode {PERMISSION_MODE}: acceptEdits with the
allowlist below is the default; bypassPermissions only in a disposable sandbox. In -p nobody can answer
a permission prompt, so a call that neither the mode nor the allowlist allows is refused. The allowlist
bounds mistakes, not hostile input: the run can execute code it writes, with this account's files,
credentials and network, so where the run reads untrusted content, run it in a container or a VM.{LOOP: When the
first call ends, the loop resumes the run while its ledger lists open tasks and none blocked, at most three
times, with a message that approves nothing the run stopped to ask about:}
    {BENCH_MKDIR}cd "{FOLDER}" && mkdir -p {RUN_DIR} && (
    claude -p --session-id {SESSION_ID} {MODEL: --model {MODEL_ID} }{EFFORT: --effort {EFFORT} }--permission-mode {PERMISSION_MODE} --allowed-tools '{ALLOWED_TOOLS}' {EXTRA_FLAGS}--output-format json < prompts/{TASK_ID}/master-prompt.md > {RUN_DIR}/launch-0.json{LOOP:
    for n in 1 2 3; do
      grep -q '^- \[!\]' {RUN_DIR}/ledger.md 2>/dev/null && break
      open=$(grep '^- \[ \]' {RUN_DIR}/ledger.md 2>/dev/null | tr '\n' ' ')
      [ -n "$open" ] || break
      claude -p "Automatic continuation from the launch loop, not the person: it approves nothing you stopped to ask about. Open tasks in your ledger: $open Continue with them. If you stopped to wait for the person, mark that task blocked in the ledger and end the turn." --resume {SESSION_ID} {MODEL: --model {MODEL_ID} }{EFFORT: --effort {EFFORT} }--permission-mode {PERMISSION_MODE} --allowed-tools '{ALLOWED_TOOLS}' {EXTRA_FLAGS}--output-format json < /dev/null > {RUN_DIR}/launch-$n.json
    done} )
```

### launch-cloud

```text
Claude Code on the web: open a new session on the repository that holds prompts/{TASK_ID}/{EFFORT:, in a cloud
environment dedicated to this run whose variables set CLAUDE_CODE_EFFORT_LEVEL={EFFORT} (the cloud icon above the
message box, then Cloud, then Add cloud environment; remove it after the run)}.{MODEL: Send `/model {MODEL_ID}` as its
first message, then}{NO_MODEL: Then} paste the contents of prompts/{TASK_ID}/master-prompt.md. Also take any
permissions file committed for the run, such as `.claude/settings.json`, off the default branch: its allow rules apply
to every later session on that repository.
```

## 5. Sources

| Key | URL | Retrieved |
|---|---|---|
| CC-SA | https://code.claude.com/docs/en/sub-agents | 2026-10-05 |
| CC-MC | https://code.claude.com/docs/en/model-config | 2026-10-05 |
| CC-ENV | https://code.claude.com/docs/en/env-vars | 2026-10-05 |
| CC-CLI | https://code.claude.com/docs/en/cli-reference | 2026-10-13 |
| CC-MEM | https://code.claude.com/docs/en/memory | 2026-10-05 |
| CC-HEADLESS | https://code.claude.com/docs/en/headless | 2026-10-12 |
| CC-PERMISSIONS | https://code.claude.com/docs/en/permissions | 2026-10-05 |
| CC-PERMMODES | https://code.claude.com/docs/en/permission-modes | 2026-10-12 |
| CC-GOAL | https://code.claude.com/docs/en/goal | 2026-10-05 |
| CC-CLOUDENV | https://code.claude.com/docs/en/cloud-environments | 2026-10-05 |
| CC-WEB | https://code.claude.com/docs/en/claude-code-on-the-web | 2026-10-05 |
| CC-ASK | https://code.claude.com/docs/en/agent-sdk/user-input | 2026-10-12 |
| CC-TOOLS | https://code.claude.com/docs/en/tools-reference | 2026-10-12 |
