#!/usr/bin/env python3
"""fake_claude.py: a stand-in for the Claude Code CLI's headless mode that the harness and launch tests drive.

It makes no network call. It reads a script, answers as the skill or as the scripted person, writes a
transcript where the real CLI does, and prints a result object shaped like `--output-format json`.

Role: a call carrying --disallowed-tools and no --allowed-tools is the person; any other call is the skill.
Environment:
  FAKE_CLAUDE_SCRIPT  JSON file {"skill": [spec, ...], "person": [spec, ...]}; the n-th call of a role
                      uses spec n (the last spec repeats; no spec: a plain answer).
  FAKE_CLAUDE_LOG     JSONL file; one line per call: role, argv, cwd, the CLAUDE_* variables, the prompt,
                      and the text read from stdin (a call with no prompt argument reads its prompt there,
                      as `claude -p < file` does).
  FAKE_CLAUDE_PARENT_SESSION  the session id a call with neither --session-id nor --resume takes, as the
                      real CLI does when it is launched inside another session (its transcript then
                      carries the calling session's id); unset: a fresh uuid4.
  CLAUDE_CONFIG_DIR or HOME: where transcripts go (<config>/projects/<cwd, non-alphanumerics as ->/).
Cost, as the real CLI reports it: a --resume call reports in total_cost_usd the session's running total,
not its own cost, since the CLI restores the session's cost state; a --session-id call and a call with neither (the person) start a fresh session and
report their own. Each call that writes a transcript ends it with a "cost-state" record holding the
figure it reports as the session's running total (totalCostUSD), as the real CLI's transcripts do, so a
forced `reported_cost` restarts it; every record carries "isSidechain" (false unless a spec says
otherwise).
Spec keys (all optional):
  result        the reply text ("{CWD}" is replaced by the call's folder)
  subtype       "success" (default), "error_max_turns", "error_max_budget_usd", "error_during_execution"
  is_error      default: subtype is not "success"
  cost          this call's own cost (default 0.01); total_cost_usd reports it, or on a --resume call the
                session's running total
  reported_cost total_cost_usd printed as this figure instead (a running total that restarted)
  exit          process exit code (default 0 on success, 1 otherwise)
  stdout        raw text printed instead of the result object
  sleep         seconds to wait before answering
  model         model of the closing assistant record (default: the --model flag); "<synthetic>" allowed
  records       extra records before the closing one, in order: an assistant record
                {"model": m, "tool_use": {"name", "input"}} or {"model": m, "text": t}, or a user record
                {"user": content} (a string, such as a background seat's <task-notification>, or a list of
                blocks, such as a tool_result); "sidechain": true marks any of them isSidechain, and
                "api_error": true an assistant record isApiErrorMessage (an API error the CLI retried)
  user_records  extra user message texts (e.g. "<command-name>/<skill name></command-name>")
  user_email    the account's address: a session_context attachment naming it, shaped as the real CLI's
                (attachment.context.userEmail, repeated in "rendered"), opens this call's records and
                every subagent transcript this call writes
  subagents     {"agent-<id>": {"meta": {...} or null, "models": [m, ...], "reads": [path, ...]}}
  write         {path relative to the call's folder: text} files to write (also to change a fixture)
  delete        [path relative to the call's folder] files to delete
  model_usage   the modelUsage keys (default: [the --model flag])
  no_transcript true: write no transcript at all
"""
import json
import os
import re
import sys
import time
import uuid

VALUE_FLAGS = {"--model", "--effort", "--max-turns", "--output-format", "--permission-mode", "--allowed-tools",
               "--disallowed-tools", "--max-budget-usd", "--session-id", "--resume", "--append-system-prompt-file"}


def parse(argv):
    flags, prompt, i = {}, None, 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            prompt = " ".join(argv[i + 1:])
            break
        if arg in VALUE_FLAGS:
            flags[arg] = argv[i + 1] if i + 1 < len(argv) else ""
            i += 2
            continue
        if arg.startswith("-"):
            flags[arg] = True
        elif prompt is None:
            prompt = arg
        i += 1
    return flags, prompt


def substitute(value, cwd):
    if isinstance(value, str):
        return value.replace("{CWD}", cwd)
    if isinstance(value, list):
        return [substitute(v, cwd) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, cwd) for k, v in value.items()}
    return value


def assistant(model, content, session, cwd, sidechain=False):
    return {"type": "assistant", "sessionId": session, "cwd": cwd, "uuid": str(uuid.uuid4()), "isSidechain": sidechain,
            "message": {"role": "assistant", "model": model, "content": content}}


def user(content, session, cwd, sidechain=False):
    return {"type": "user", "sessionId": session, "cwd": cwd, "uuid": str(uuid.uuid4()), "isSidechain": sidechain,
            "message": {"role": "user", "content": content}}


def session_context(address, session, cwd, sidechain=False):
    """The attachment the real CLI writes into each transcript, main and subagent: the account's address."""
    text = "The user's email address is %s. Use it only to identify the user." % address
    return {"type": "attachment", "sessionId": session, "cwd": cwd, "uuid": str(uuid.uuid4()), "isSidechain": sidechain,
            "attachment": {"type": "session_context", "context": {"userEmail": text}},
            "rendered": [{"type": "text", "text": "# userEmail\n" + text}]}


def running_total(path):
    """The last cost-state totalCostUSD of a transcript (0 when it has none)."""
    total = 0.0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and record.get("type") == "cost-state":
                    total = record.get("totalCostUSD", total)
    return total


def main():
    flags, prompt = parse(sys.argv[1:])
    stdin_text = None
    if prompt is None and not sys.stdin.isatty():
        stdin_text = sys.stdin.read()
        prompt = stdin_text
    role = "person" if "--disallowed-tools" in flags and "--allowed-tools" not in flags else "skill"
    cwd = os.getcwd()
    log_path = os.environ.get("FAKE_CLAUDE_LOG")
    previous = 0
    if log_path and os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as handle:
            previous = sum(1 for line in handle if line.strip() and json.loads(line).get("role") == role)
    if log_path:
        env = {k: os.environ.get(k) for k in sorted(os.environ) if k.startswith("CLAUDE")}
        for name in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "CLAUDE_EFFORT", "CLAUDE_CODE_EFFORT_LEVEL"):
            env.setdefault(name, None)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"role": role, "argv": sys.argv[1:], "cwd": cwd, "env": env, "prompt": prompt,
                                     "stdin_is_tty": sys.stdin.isatty(), "stdin": stdin_text}) + "\n")
    specs = []
    script = os.environ.get("FAKE_CLAUDE_SCRIPT")
    if script:
        with open(script, encoding="utf-8") as handle:
            specs = json.load(handle).get(role, [])
    spec = specs[min(previous, len(specs) - 1)] if specs else {}
    spec = substitute(spec, cwd)
    if spec.get("sleep"):
        time.sleep(float(spec["sleep"]))
    model = flags.get("--model") or "example-model-1"
    session = flags.get("--session-id") or flags.get("--resume") or os.environ.get("FAKE_CLAUDE_PARENT_SESSION") or \
        str(uuid.uuid4())
    subtype = spec.get("subtype", "success")
    is_error = spec.get("is_error", subtype != "success")
    text = spec.get("result", "Done." if role == "skill" else "I don't know; I accept your recommendation.")

    for rel, content in (spec.get("write") or {}).items():
        path = os.path.join(cwd, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    for rel in spec.get("delete") or []:
        path = os.path.join(cwd, rel)
        if os.path.exists(path):
            os.remove(path)

    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.environ.get("HOME", "."), ".claude")
    folder = os.path.join(config, "projects", re.sub(r"[^A-Za-z0-9]", "-", cwd))
    transcript = os.path.join(folder, session + ".jsonl")
    own = spec.get("cost", 0.01)
    total = (running_total(transcript) if "--resume" in flags else 0.0) + own
    reported = spec.get("reported_cost", total)
    address = spec.get("user_email")

    if not spec.get("no_transcript"):
        os.makedirs(folder, exist_ok=True)
        records = [session_context(address, session, cwd)] if address else []
        records.append(user(prompt or "", session, cwd))
        records.append("not json at all")
        records.append(["a", "list", "is", "not", "a", "record"])
        for extra in spec.get("user_records") or []:
            records.append(user(extra, session, cwd))
        for extra in spec.get("records") or []:
            side = bool(extra.get("sidechain"))
            if "user" in extra:
                records.append(user(extra["user"], session, cwd, side))
                continue
            content = [{"type": "tool_use", "id": "toolu_%s" % uuid.uuid4().hex[:12], "name": extra["tool_use"]["name"],
                        "input": extra["tool_use"].get("input", {})}] if extra.get("tool_use") else \
                      [{"type": "text", "text": extra.get("text", "working")}]
            records.append(assistant(extra.get("model", model), content, session, cwd, side))
            if extra.get("api_error"):
                records[-1]["isApiErrorMessage"] = True
        records.append(assistant(spec.get("model", model), [{"type": "text", "text": text}], session, cwd))
        records.append({"type": "cost-state", "sessionId": session, "totalCostUSD": reported})
        with open(transcript, "a", encoding="utf-8") as handle:
            for record in records:
                handle.write((record if isinstance(record, str) else json.dumps(record)) + "\n")
        for agent, data in (spec.get("subagents") or {}).items():
            sub = os.path.join(folder, session, "subagents")
            os.makedirs(sub, exist_ok=True)
            with open(os.path.join(sub, agent + ".jsonl"), "a", encoding="utf-8") as handle:
                if address:
                    handle.write(json.dumps(session_context(address, session, cwd, True)) + "\n")
                for path in data.get("reads") or []:
                    handle.write(json.dumps(assistant(model, [{"type": "tool_use", "id": "toolu_r", "name": "Read",
                                                               "input": {"file_path": path}}], session, cwd, True)) + "\n")
                for seat_model in data.get("models") or []:
                    handle.write(json.dumps(assistant(seat_model, [{"type": "text", "text": "seat work"}], session, cwd,
                                                      True)) + "\n")
            if data.get("meta") is not None:
                with open(os.path.join(sub, agent + ".meta.json"), "w", encoding="utf-8") as handle:
                    json.dump(data.get("meta"), handle)

    if "stdout" in spec:
        sys.stdout.write(spec["stdout"])
    else:
        usage = spec.get("model_usage", [model])
        result = {"type": "result", "subtype": subtype, "is_error": is_error, "duration_ms": 7, "duration_api_ms": 5,
                  "num_turns": 1, "session_id": session, "total_cost_usd": reported,
                  "modelUsage": {m: {"costUSD": reported} for m in usage}}
        if subtype == "success" or "result" in spec:
            result["result"] = text
        sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
    return spec.get("exit", 0 if subtype == "success" else 1)


if __name__ == "__main__":
    sys.exit(main())
