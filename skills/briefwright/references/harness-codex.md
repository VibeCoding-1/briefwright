# Harness guide: Codex

How a run on Codex gives its seats their models, how it is launched, and what it allows. Each line of §1–§4 ends with its source: `[KEY #anchor]` names a page or a section listed in §5, and for `CX-SRC` a file of Codex's source at the tagged release, read there and not run. `[skill]` is this skill's own rule. The install and one use ran on Codex 0.162.1 on 2026-10-13; the launch, resume and cloud facts were not run. Lines marked "not established" are open, and the blocks say where they lean on them.

## 1. The harness

- **Instruction files** (`{INSTRUCTION_FILES}`): `AGENTS.md`, read from `$CODEX_HOME` and then from each folder between the project root and the working folder; where a folder has an `AGENTS.override.md`, that is read instead, and reading stops at `project_doc_max_bytes`, 32 KiB by default [CX-AGENTS #how-codex-discovers-guidance].
- **Skills** are read from `.agents/skills` and from plugins [CX-SKILLS #where-codex-loads-local-skills].
- Skills stored in the repository are available in cloud tasks [CX-CLOUD #current-limitations].
- **Subagents** start when the prompt or a skill's text asks for them [CX-SUB #triggering-subagent-workflows].
- A subagent's model and effort resolve in this order: the values its start names; then `agents.default_subagent_*`; then the parent's. A custom agent file's `model` overrides all three [CX-SUB #custom-agents].
- `agents.max_depth` is 1 by default, so a seat cannot start seats of its own [CX-SRC #core/src/config/mod.rs].
- `-c agents.enabled=false` turns subagents off for a run [CX-SUB #global-settings].
- **Effort:** `-c model_reasoning_effort="<level>"`; the levels on offer depend on the model [CX-CONFIG].
- **Headless:** `codex exec` forces the approval policy `never`, so an action that needs approval fails, and the failure goes back to the model [CX-SRC #exec/src/lib.rs; CX-SUB #approvals-and-sandbox-controls].
- A `codex exec` call ends at its first completed turn [CX-SRC #exec/src/event_processor_with_jsonl_output.rs].
- `-` reads the whole prompt from stdin; `--json` writes JSONL events; `-o` writes the last message to a file [CX-EXEC; CX-SRC #exec/src/cli.rs].
- The `--json` output opens with a `thread.started` event that carries the thread's id as `thread_id` [CX-EXEC #make-output-machine-readable; CX-SRC #exec/src/exec_events.rs].
- `codex exec resume <id> "<message>"` continues that thread; `--last` takes the folder's latest thread instead, which may be a seat's, so the launch loop resumes the first call's thread by its id [CX-EXEC #resume-a-non-interactive-session; CX-CMD #codex-exec; CX-SRC #exec/src/lib.rs].
- A resumed call runs on the model and sandbox its own flags and the configuration give, not the first call's: without `-m` a configured `model` replaces the thread's, and without `-s` the sandbox is the configured one, read-only by default; `-s` goes before `resume`, which does not take it; from the source at rust-v0.160.0, not run [CX-SRC #exec/src/lib.rs; CX-SRC #exec/src/cli.rs; CX-EXEC #permissions-and-safety].
- `codex exec` has no flag that limits time, turns or spend, so `timeout` bounds wall time [CX-SRC #exec/src/cli.rs].
- Do not use `--full-auto`: the docs keep it as a deprecated flag that warns, the source at this release no longer has it, and `-s workspace-write` replaces it [CX-EXEC #permissions-and-safety; CX-SRC #exec/src/cli.rs].
- **Keep-going command:** `/goal <objective>`, attended only; it takes at most 4,000 characters, so point it at the prompt file [CX-CMD #set-or-view-a-task-goal-with-goal].
- Not established: which branch a cloud task works on, how it picks a model, and whether it loads `AGENTS.md` [CX-CLOUD].
- Not established: a documented minimum CLI version for what the blocks use [skill].

## 2. A named model, and your helper seats

- **`{MODEL_ID}`**, only where the person named a model, is that model as Codex names it; with no id from the person, `[you fill this in: the model id]` [skill].
- **A helper seat** is a new subagent asked for with its brief, naming at its start the model the guideline gives its work: a start's own model outranks `agents.default_subagent_*` [CX-SUB #global-settings].
- A helper seat cannot start seats of its own [CX-SRC #core/src/config/mod.rs].
- With subagents turned off, `SKILL.md`'s sequential fallback applies [CX-SUB].

## 3. Seats and models in the prompt

- Implementer and lead: `seats-models`, then the template's fallback paragraph [skill].
- Alone: no section [skill].
- Fill every slot; `{RUN_DIR}` is the run's folder. Keep an `{EFFORT: …}` fragment's text only where `effort=` names a level, a `{MODEL: …}` fragment's only where `model=` names a model and a `{NO_MODEL: …}` fragment's only where it is `choose`; drop the braces and the name [skill].

### seats-models

```text
{NO_MODEL:Give each seat the model its work needs: the strongest available for planning, hard building and review; a
faster one for searches, simple edits and mechanical checks. Name it when you start each subagent: a start that names
none takes the configuration's `agents.default_subagent_*`, then yours, and a custom agent file's own model outranks
all three.}{MODEL:Every seat runs on `{MODEL_ID}`, the model the person chose, which the launch set for you: name it at
every subagent start, since a start that names none takes the configuration's `agents.default_subagent_*` first, and
start no seat as a custom agent whose file names another model.}
```

### reviewer-facts

```text
In Codex {MODEL:the launch sets the lead's model with `-m {MODEL_ID}` and every seat start names it}{NO_MODEL:the launch names no model, and each seat start names the model the guideline in Seats and models gives its work}{EFFORT:; `-c model_reasoning_effort="{EFFORT}"` sets the lead's effort}; a subagent takes the model its start names, then the configuration's `agents.default_subagent_*`, then the parent's, and a custom agent file outranks all three. An unattended launch uses `codex exec` with `-s workspace-write` and `--json`, and its loop resumes the first call's thread by its id, never `--last`, at most three times, each resumed call passing the first call's flags again, `-s` before `resume`.
```

## 4. The launch

- `launch=interactive` takes `launch-attended`, `headless` takes `launch-headless` and `cloud` takes `launch-cloud`; `other` takes the generic guide's `launch-headless` [skill].
- Keep a `{LOOP: …}` fragment's text above quick and drop it on quick, whose run keeps no ledger for the loop to read [skill].
- `{SANDBOX}` is `workspace-write`; `danger-full-access` only when the person confirms a disposable sandbox with nothing of value and no credentials beyond the run's own [CX-EXEC #permissions-and-safety].
- Under `workspace-write` `.git` is read-only and the network off by default, so a run can neither commit nor push [CX-SEC #protected-paths-in-writable-roots; CX-SEC #sandbox-and-approvals].
- So where an unattended run's method commits (RS2, RS9, RS12, or the quick template's `{DISPOSABLE: …}` line), the design asks the person, recommending that the run leave git to them (the template's `{NO_GIT: …}` texts, a row of § Accepted defaults); the alternative, and on a disposable machine the only one, since there the run pushes, is `danger-full-access` in a disposable sandbox with nothing of value and no credentials beyond the run's own, its push credentials scoped to this one repository [skill].
- `{TIMEOUT}` is `timeout <seconds> ` with the person's wall-clock cap, or empty [skill].

### launch-attended

```text
Codex CLI, attended:
    cd "{FOLDER}"
    codex {MODEL: -m {MODEL_ID} }{EFFORT: -c model_reasoning_effort="{EFFORT}" }-s workspace-write -a on-request "Read prompts/{TASK_ID}/master-prompt.md in full and follow it."
```

### launch-headless

```text
Codex CLI, unattended on this machine. Sandbox {SANDBOX}: workspace-write is the default; danger-full-access
only in a disposable sandbox. `codex exec` asks for no approval: an action the sandbox refuses fails, and the
run is told so.{LOOP: A `codex exec` call ends at its first completed turn, so the loop resumes the run while its
ledger lists open tasks and none blocked, at most three times, with a message that approves nothing the run
stopped to ask about. It resumes the first call's thread by the id its `thread.started` event gives, never
`--last`, which takes the folder's latest thread and could take a seat's; with no id found it stops. Each
resumed call passes the first call's flags again, since a resume runs on what its own flags and the
configuration give.} Under workspace-write `.git` is read-only and the network off, so the run
can neither commit nor push.{LOOP: The loop is not tested.}
    cd "{FOLDER}" && mkdir -p {RUN_DIR} && (
    {TIMEOUT}codex exec {MODEL: -m {MODEL_ID} }{EFFORT: -c model_reasoning_effort="{EFFORT}" }-s {SANDBOX} --json -o {RUN_DIR}/last-0.md - < prompts/{TASK_ID}/master-prompt.md > {RUN_DIR}/launch-0.jsonl{LOOP:
    tid=$(grep -o '"thread_id": *"[^"]*"' {RUN_DIR}/launch-0.jsonl | head -n 1 | sed 's/.*"\([^"]*\)"$/\1/')
    for n in 1 2 3; do
      [ -n "$tid" ] || break
      grep -q '^- \[!\]' {RUN_DIR}/ledger.md 2>/dev/null && break
      open=$(grep '^- \[ \]' {RUN_DIR}/ledger.md 2>/dev/null | tr '\n' ' ')
      [ -n "$open" ] || break
      {TIMEOUT}codex exec {MODEL: -m {MODEL_ID} }{EFFORT: -c model_reasoning_effort="{EFFORT}" }-s {SANDBOX} resume "$tid" "Automatic continuation from the launch loop, not the person: it approves nothing you stopped to ask about. Open tasks in your ledger: $open Continue with them. If you stopped to wait for the person, mark that task blocked in the ledger and end the turn." --json < /dev/null > {RUN_DIR}/launch-$n.jsonl
    done} )
```

### launch-cloud

```text
Codex Cloud: commit and push prompts/{TASK_ID}/ to the repository, create and publish a cloud environment
for it (Work in > Cloud > Select environment > Create environment), and start a new task in that environment
whose message is "Read prompts/{TASK_ID}/master-prompt.md in full and follow it."{MODEL: Pick `{MODEL_ID}` where the
task offers a model.} Which branch a task works on, how it sets its model, and whether it loads AGENTS.md are
not documented.
```

## 5. Sources

| Key | URL | Retrieved |
|---|---|---|
| CX-SUB | https://learn.chatgpt.com/docs/agent-configuration/subagents.md | 2026-10-05 |
| CX-AGENTS | https://learn.chatgpt.com/docs/agent-configuration/agents-md.md | 2026-10-05 |
| CX-SKILLS | https://learn.chatgpt.com/docs/build-skills | 2026-10-05 |
| CX-CLOUD | https://learn.chatgpt.com/docs/environments/cloud-environments.md | 2026-10-05 |
| CX-EXEC | https://learn.chatgpt.com/docs/non-interactive-mode.md | 2026-10-05 |
| CX-CMD | https://learn.chatgpt.com/docs/developer-commands.md?surface=cli | 2026-10-05 |
| CX-CONFIG | https://learn.chatgpt.com/docs/config-file/config-reference.md | 2026-10-05 |
| CX-SEC | https://learn.chatgpt.com/docs/agent-approvals-security.md | 2026-10-05 |
| CX-SRC | https://github.com/openai/codex/tree/rust-v0.160.0/codex-rs | 2026-10-05 |
