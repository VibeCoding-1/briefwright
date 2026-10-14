# Harness guide: any other harness

This guide names no harness and states no vendor fact, so each line of §1–§4 ends with `[skill]`, this skill's own rule; what the harness itself can do, the person or its documentation says.

## 1. The harness

- **For:** any harness without a guide of its own, with or without subagents [skill].
- **Instruction files** (`{INSTRUCTION_FILES}`): the files this harness loads as project instructions; many load `AGENTS.md`. Where unsure, ask the person [skill].
- **Keep-going command:** none [skill].

## 2. A named model, and your helper seats

- **`{MODEL_ID}`**, only where the person named a model, is its id as this harness names it; with no id from the person, `[you fill this in: the model id]` [skill].
- **A helper seat** starts however this harness starts subagents, naming the model the guideline gives its work where that is possible [skill].
- With no subagents, `SKILL.md`'s sequential fallback applies [skill].

## 3. Seats and models in the prompt

- Implementer and lead: `seats-models`, then the template's fallback paragraph [skill].
- Alone: no section [skill].
- Fill every slot. Keep an `{EFFORT: …}` fragment's text only where `effort=` names a level, a `{MODEL: …}` fragment's only where `model=` names a model and a `{NO_MODEL: …}` fragment's only where it is `choose`, and drop the braces and the name [skill].

### seats-models

```text
{NO_MODEL:Give each seat the model its work needs: the strongest available for planning, hard building and review; a
faster one for searches, simple edits and mechanical checks. Where starting a seat lets you name a model, name it so;
where it does not, a seat runs what your harness gives it.}{MODEL:Every seat runs on `{MODEL_ID}`, the model the person
chose, which the launch set for you: name it wherever starting a seat lets you name a model.}
```

### reviewer-facts

```text
On this harness {MODEL:the launch sets `{MODEL_ID}` by the harness's own means, and a seat start names it where it can}{NO_MODEL:the launch names no model, and a seat start names the model the guideline in Seats and models gives its work where it can}; seats fall back to sequential work where none can start.
```

## 4. The launch

- `launch=interactive` takes `launch-attended`, `cloud` takes `launch-cloud`, and `headless` and `other` take `launch-headless` [skill].
- Keep a `{LOOP: …}` fragment's text above quick and drop it on quick, whose run keeps no ledger for the loop to read [skill].

### launch-attended

```text
Your harness, attended: open a session in "{FOLDER}"{MODEL: on `{MODEL_ID}`}{EFFORT: at `{EFFORT}` effort} by its own
means, and give it prompts/{TASK_ID}/master-prompt.md as its first message: paste it, or ask it to read that
file in full and follow it.
```

### launch-headless

```text
Your harness, unattended: only where it has a non-interactive mode. Start it in "{FOLDER}"{MODEL: on `{MODEL_ID}`}{EFFORT: at `{EFFORT}` effort}
with prompts/{TASK_ID}/master-prompt.md as its input and the narrowest permissions that let every command of the method and the bar run.{LOOP: If a call ends at its first finished turn,
resume the same session while the ledger lists open tasks and none blocked, at most three times, with a
message that approves nothing the run stopped to ask about.}
```

### launch-cloud

```text
Your harness's cloud sessions: open one on the repository that holds prompts/{TASK_ID}/{MODEL:, on `{MODEL_ID}` where
it offers a model}, with the first message "Read prompts/{TASK_ID}/master-prompt.md in full and follow it."
```

## 5. Sources

None: this guide states no vendor fact.
