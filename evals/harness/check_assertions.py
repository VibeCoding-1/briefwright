#!/usr/bin/env python3
"""check_assertions.py: check one run's metrics against a scenario's assertions.

Usage: python3 check_assertions.py <metrics.json> --scenario <id or name> [--evals <evals.json>]
The default --evals is the evals.json beside this folder. The run's other outputs are read from the
folder of metrics.json: turns.jsonl, fixtures.json, prompt/<task-id>/master-prompt.md and decisions.md.

Exit: 0 every assertion holds; 1 at least one fails (each is printed PASS or FAIL); 2 usage.

Assertion keys (frozen):
  delivered (bool)                 metrics.delivered
  framing_question_count (int)     metrics.framing_question_turns: the skill's messages asking the
                                   harness question
  guide_reads (list)               the basenames of metrics.guide_reads (harness guides read), as an exact set
  pack_reads (list)                the basenames of metrics.pack_reads (guidance packs read), as an exact set
  lint_errors_max (int)            metrics.lint_errors is a number at most this
  prompt_contains (list)           each entry is found in master-prompt.md
  prompt_absent (list)             no entry is found in master-prompt.md
  first_turn_questions_min (int)   the questions in the skill's first message (a `**Qn` line, or a
                                   paragraph or list item ending with `?`) are at least this
  first_turn_contains_any (list)   the skill's first message holds at least one entry
  framing (dict)                   each key (harness, launch, model, effort or any other) has this value on
                                   the produced decisions.md's Framing line
  fixture_unchanged (list)         each bench-relative path has before == after in fixtures.json
A string entry is a case-sensitive substring; an entry that starts with `re:` is a Python regular
expression searched with re.M (write `re:(?i)...` to ignore case). `{MODEL}` in any assertion is the run's
model, metrics.model (escaped inside a `re:` entry), as the runner filled it into the task.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_skill import questions_in  # noqa: E402  (the harness's own question count)

MODEL_SLOT = "{MODEL}"
KEYS = ("delivered", "framing_question_count", "guide_reads", "pack_reads", "lint_errors_max", "prompt_contains",
        "prompt_absent", "first_turn_questions_min", "first_turn_contains_any", "framing", "fixture_unchanged")
FRAMING_KEYS = ("size", "autonomy", "harness", "launch", "model", "effort", "run", "machine", "seat", "review",
                "folder")


def found(entry, text):
    if entry.startswith("re:"):
        return re.search(entry[3:], text, re.M) is not None
    return entry in text


def with_model(value, model):
    """An assertion value with every {MODEL} replaced by `model` (metrics.model), escaped inside a `re:` entry."""
    if isinstance(value, dict):
        return {key: with_model(item, model) for key, item in value.items()}
    if isinstance(value, list):
        return [with_model(item, model) for item in value]
    if isinstance(value, str) and MODEL_SLOT in value:
        return value.replace(MODEL_SLOT, re.escape(model) if value.startswith("re:") else model)
    return value


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def prompt_folder(run_dir):
    """The prompts/<task-id>/ folder the harness linted, or the only one there is."""
    folders = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(run_dir, "prompt", "*", "master-prompt.md")))
    if len(folders) <= 1:
        return folders[0] if folders else None
    try:
        linted = read_json(os.path.join(run_dir, "lint.json")).get("file", "")
        name = os.path.basename(os.path.dirname(linted))
        match = [f for f in folders if os.path.basename(f) == name]
        if match:
            return match[0]
    except (OSError, ValueError, AttributeError):
        pass
    return folders[-1]


def framing_of(text):
    """The keys of the first `Framing:` line outside a fence; `folder=` takes the rest of the line."""
    fence = ""
    for line in text.split("\n"):
        opened = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            if line.strip() and set(line.strip()) == {fence[0]} and len(line.strip()) >= len(fence):
                fence = ""
            continue
        if opened:
            fence = opened.group(1)
            continue
        if line.startswith("Framing:"):
            body, values = line[len("Framing:"):].strip(), {}
            folder = re.search(r"(?:^|;)\s*folder=(.*)$", body)
            if folder:
                values["folder"] = folder.group(1).strip()
                body = body[:folder.start()]
            for part in body.split(";"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    values[key.strip()] = value.strip()
            return values
    return None


def check(metrics_path, scenario, evals_path):
    run_dir = os.path.dirname(os.path.abspath(metrics_path))
    metrics = read_json(metrics_path)
    results = []   # (ok, name, detail)

    def outcome(ok, name, detail):
        results.append((bool(ok), name, detail))

    task_file = os.path.join(os.path.dirname(os.path.abspath(evals_path)), scenario.get("task", ""))
    try:
        expected_task = read_json(task_file).get("id")
        if expected_task and metrics.get("task") != expected_task:
            outcome(False, "task", "metrics are for %r; scenario %s runs %r" % (metrics.get("task"), scenario.get("id"), expected_task))
    except (OSError, ValueError, AttributeError):
        pass
    folder = prompt_folder(run_dir)
    prompt = decisions = None
    if folder:
        with open(os.path.join(folder, "master-prompt.md"), encoding="utf-8", errors="replace") as handle:
            prompt = handle.read()
        if os.path.isfile(os.path.join(folder, "decisions.md")):
            with open(os.path.join(folder, "decisions.md"), encoding="utf-8", errors="replace") as handle:
                decisions = handle.read()
    first_turn = None
    try:
        with open(os.path.join(run_dir, "turns.jsonl"), encoding="utf-8") as handle:
            for line in handle:
                entry = json.loads(line)
                if entry.get("role") == "skill":
                    first_turn = entry.get("text") or ""
                    break
    except (OSError, ValueError):
        pass

    assertions = scenario.get("assertions", {})
    model = metrics.get("model")
    if MODEL_SLOT in json.dumps(assertions):
        if isinstance(model, str) and model:
            assertions = with_model(assertions, model)
        else:
            outcome(False, "model", "metrics.json names no model to fill %s with" % MODEL_SLOT)
    for key, want in sorted(assertions.items()):
        if key == "delivered":
            outcome(metrics.get("delivered") is want, key, "expected %s, got %s" % (want, metrics.get("delivered")))
        elif key == "framing_question_count":
            got = metrics.get("framing_question_turns")
            outcome(got == want, key, "expected %s framing-question turn(s), got %s" % (want, got))
        elif key in ("guide_reads", "pack_reads"):
            got = metrics.get(key)
            if not isinstance(got, list):
                outcome(False, key, "metrics.json has no %s list" % key)
                continue
            got = sorted({os.path.basename(p) for p in got})
            outcome(got == sorted(set(want)), key, "expected exactly %s, got %s" % (sorted(set(want)), got))
        elif key == "lint_errors_max":
            got = metrics.get("lint_errors")
            outcome(isinstance(got, int) and got <= want, key, "expected at most %s, got %s" % (want, got))
        elif key in ("prompt_contains", "prompt_absent"):
            if prompt is None:
                outcome(False, key, "no master-prompt.md in %s" % os.path.join("prompt", "*"))
                continue
            for entry in want:
                present = found(entry, prompt)
                ok = present if key == "prompt_contains" else not present
                outcome(ok, key, "%r %s" % (entry, "found" if present else "not found"))
        elif key == "first_turn_questions_min":
            got = questions_in(first_turn) if first_turn is not None else None
            outcome(got is not None and got >= want, key, "expected at least %s, got %s" % (want, got))
        elif key == "first_turn_contains_any":
            hits = [entry for entry in want if first_turn is not None and found(entry, first_turn)]
            outcome(bool(hits), key, "found %s" % hits if hits else "none of %s in the first message" % want)
        elif key == "framing":
            got = framing_of(decisions) if decisions is not None else None
            if got is None:
                outcome(False, key, "no Framing line in the produced decisions.md")
                continue
            for name, value in sorted(want.items()):
                outcome(got.get(name) == value, "%s.%s" % (key, name), "expected %r, got %r" % (value, got.get(name)))
        elif key == "fixture_unchanged":
            try:
                fixtures = read_json(os.path.join(run_dir, "fixtures.json"))
            except (OSError, ValueError):
                outcome(False, key, "no fixtures.json beside metrics.json")
                continue
            for path in want:
                entry = fixtures.get(path)
                ok = isinstance(entry, dict) and entry.get("before") is not None and entry.get("before") == entry.get("after")
                outcome(ok, key, "%s %s" % (path, "unchanged" if ok else "changed, deleted or not a fixture: %s" % entry))
        else:
            outcome(False, key, "unknown assertion key (known: %s)" % ", ".join(KEYS))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a run's metrics against a scenario's assertions.")
    parser.add_argument("metrics")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--evals", default=os.path.join(os.path.dirname(HERE), "evals.json"))
    args = parser.parse_args(argv)
    try:
        evals = read_json(args.evals)
        read_json(args.metrics)
    except (OSError, ValueError) as error:
        sys.stderr.write("check_assertions: cannot read input: %s\n" % error)
        return 2
    scenario = next((s for s in evals.get("evals", []) if str(s.get("id")) == args.scenario or s.get("name") == args.scenario), None)
    if scenario is None:
        sys.stderr.write("check_assertions: no scenario %r in %s\n" % (args.scenario, os.path.basename(args.evals)))
        return 2
    results = check(args.metrics, scenario, args.evals)
    for ok, name, detail in results:
        print("%s %s: %s" % ("PASS" if ok else "FAIL", name, detail))
    failed = sum(1 for ok, _, _ in results if not ok)
    print("scenario %s (%s): %d assertion(s), %d failed" % (scenario.get("id"), scenario.get("name"), len(results), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
