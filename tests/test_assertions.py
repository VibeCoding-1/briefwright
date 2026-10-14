"""Tests for evals/harness/check_assertions.py against metric fixtures, and for the shape of evals/evals.json."""
import json
import os
import shutil
import tempfile
import unittest

from support import EVALS, HARNESS, PROMPTS, SKILL, read, run_py, write, write_json

import check_assertions
import lint_prompt
import run_skill

CHECK = os.path.join(HARNESS, "check_assertions.py")
EVALS_JSON = os.path.join(EVALS, "evals.json")
QUICK = read(os.path.join(PROMPTS, "good-quick.md"))
QUICK_DECISIONS = read(os.path.join(PROMPTS, "good-quick.decisions.md"))
ALL_KEYS = {
    "delivered": True, "framing_question_count": 1, "guide_reads": ["harness-claude-code.md"], "pack_reads": [],
    "lint_errors_max": 0, "prompt_contains": ["Work alone: dispatch no subagent.", "re:(?i)\\*\\*wait rule\\.\\*\\*"],
    "prompt_absent": ["re:example-model-[0-9]"], "first_turn_questions_min": 2,
    "first_turn_contains_any": ["nothing like this", "re:Where will the run execute"],
    "framing": {"harness": "claude-code", "launch": "interactive", "model": "example-model-1", "effort": "default",
                "size": "quick"},
    "fixture_unchanged": ["project/slugger/slugger.py"],
}
SCENARIOS = ("quick-slugger", "vague-premium-landing", "oversized-no-cap", "battle-royale-lead", "harness-not-stated",
             "stated-spanish", "other-harness-named", "hero-loop-against-site", "codex-unattended", "no-subagents")
GUIDES = ("harness-claude-code.md", "harness-codex.md", "harness-generic.md")
UNSTATED = ("harness-not-stated", "oversized-no-cap", "hero-loop-against-site")   # the person names no model


def scenarios():
    return {s["name"]: s for s in json.loads(read(EVALS_JSON))["evals"]}


class CheckAssertions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_dir = os.path.join(self.tmp, "out", "unit-task", "new")
        write_json(os.path.join(self.run_dir, "metrics.json"), {
            "task": "unit-task", "delivered": True, "framing_question_turns": 1, "lint_errors": 0,
            "guide_reads": ["harness-claude-code.md"], "pack_reads": []})
        write(os.path.join(self.run_dir, "turns.jsonl"), "\n".join(json.dumps(t) for t in [
            {"turn": 0, "role": "person", "text": "opening?"},
            {"turn": 1, "role": "skill", "text": "**Q1. Where will the run execute?**\n\nWhich folder?"}]) + "\n")
        write_json(os.path.join(self.run_dir, "fixtures.json"),
                   {"project/slugger/slugger.py": {"before": "aa", "after": "aa"},
                    "project/slugger/test_slugger.py": {"before": "bb", "after": "cc"}})
        write(os.path.join(self.run_dir, "prompt", "slug-fix", "master-prompt.md"), QUICK)
        write(os.path.join(self.run_dir, "prompt", "slug-fix", "decisions.md"), QUICK_DECISIONS)
        write_json(os.path.join(self.tmp, "tasks", "unit", "task.json"), {"id": "unit-task"})
        self.evals = os.path.join(self.tmp, "evals.json")
        self.scenario(ALL_KEYS)

    def scenario(self, assertions):
        write_json(self.evals, {"evals": [
            {"id": 1, "name": "unit", "task": "tasks/unit/task.json", "expected_output": "x", "assertions": assertions}]})

    def check(self, scenario="1"):
        return run_py(CHECK, [os.path.join(self.run_dir, "metrics.json"), "--scenario", scenario, "--evals", self.evals])

    def test_every_key_holds(self):
        self.assertEqual(sorted(ALL_KEYS), sorted(check_assertions.KEYS))
        proc = self.check()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)
        self.assertEqual(self.check("unit").returncode, 0)

    def test_each_key_can_fail(self):
        failing = {
            "delivered": False, "framing_question_count": 0, "guide_reads": ["harness-codex.md"],
            "pack_reads": ["example-pack.md"], "lint_errors_max": -1, "prompt_contains": ["absent text"],
            "prompt_absent": ["Work alone"], "first_turn_questions_min": 3, "first_turn_contains_any": ["nowhere"],
            "framing": {"harness": "codex"}, "fixture_unchanged": ["project/slugger/test_slugger.py"], "no_such_key": 1}
        self.assertEqual(sorted(set(failing) - {"no_such_key"}), sorted(check_assertions.KEYS))
        for key, value in failing.items():
            self.scenario({key: value})
            proc = self.check()
            self.assertEqual(proc.returncode, 1, key)
            self.assertIn("FAIL", proc.stdout, key)

    def test_the_read_lists_are_exact_sets_of_basenames(self):
        metrics = json.loads(read(os.path.join(self.run_dir, "metrics.json")))
        metrics["guide_reads"] = ["harness-codex.md", "project/x/references/harness-claude-code.md", "harness-codex.md"]
        write_json(os.path.join(self.run_dir, "metrics.json"), metrics)
        for want, code in ((["harness-claude-code.md", "harness-codex.md"], 0), (["harness-codex.md"], 1),
                           (["harness-claude-code.md", "harness-codex.md", "harness-generic.md"], 1)):
            self.scenario({"guide_reads": want})
            self.assertEqual(self.check().returncode, code, want)
        del metrics["pack_reads"]  # a metrics file without the list fails, whatever is wanted
        write_json(os.path.join(self.run_dir, "metrics.json"), metrics)
        self.scenario({"pack_reads": []})
        self.assertEqual(self.check().returncode, 1)

    def test_lint_errors_null_fails(self):
        metrics = json.loads(read(os.path.join(self.run_dir, "metrics.json")))
        metrics["lint_errors"] = None
        write_json(os.path.join(self.run_dir, "metrics.json"), metrics)
        self.scenario({"lint_errors_max": 5})
        self.assertEqual(self.check().returncode, 1)

    def test_task_mismatch_and_usage(self):
        write_json(os.path.join(self.tmp, "tasks", "unit", "task.json"), {"id": "another-task"})
        self.assertEqual(self.check().returncode, 1)
        self.assertEqual(self.check("99").returncode, 2)
        self.assertEqual(run_py(CHECK, [os.path.join(self.tmp, "missing.json"), "--scenario", "1", "--evals", self.evals]).returncode, 2)

    def test_the_model_slot_is_the_run_s_model(self):
        """`{MODEL}` in an assertion is metrics.model, so the Framing line must name the model the run used; inside a
        `re:` entry it is matched literally; with no model in metrics.json the check fails."""
        slot = check_assertions.MODEL_SLOT
        self.assertEqual(slot, run_skill.MODEL_SLOT)
        metrics = json.loads(read(os.path.join(self.run_dir, "metrics.json")))
        for model, code in (("example-model-1", 0), ("example-model-2", 1)):
            metrics["model"] = model
            write_json(os.path.join(self.run_dir, "metrics.json"), metrics)
            self.scenario({"framing": {"model": slot}})
            self.assertEqual(self.check().returncode, code, model)
        self.assertEqual(check_assertions.with_model({"model": slot, "prompt_contains": ["re:for `%s`" % slot, slot]},
                                                     "example.model-1"),
                         {"model": "example.model-1", "prompt_contains": ["re:for `example\\.model\\-1`",
                                                                          "example.model-1"]})
        self.assertFalse(check_assertions.found(check_assertions.with_model("re:for `%s`" % slot, "example.model-1"),
                                                "for `exampleXmodel-1`"))
        del metrics["model"]
        write_json(os.path.join(self.run_dir, "metrics.json"), metrics)
        self.scenario({"framing": {"model": slot}})
        proc = self.check()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("names no model", proc.stdout)

    def test_regex_entries(self):
        self.assertTrue(check_assertions.found("re:(?i)WAIT rule", "**Wait rule.** x"))
        self.assertFalse(check_assertions.found("wait rule", "**Wait rule.** x"))
        self.assertTrue(check_assertions.found("re:^## Scope$", "x\n## Scope\ny"))

    def test_the_framing_line_is_read_as_the_linter_reads_it(self):
        """folder= takes the rest of the line; a Framing line inside a fence is not the record's."""
        line = "Framing: size=standard; harness=codex; launch=headless; model=example-model-1; effort=high; folder=/srv/a b; c"
        self.assertEqual(check_assertions.framing_of(line), {"size": "standard", "harness": "codex", "launch": "headless",
                                                             "model": "example-model-1", "effort": "high",
                                                             "folder": "/srv/a b; c"})
        self.assertEqual(check_assertions.framing_of("```\n" + line + "\n```\n"), None)
        self.assertEqual(check_assertions.framing_of(QUICK_DECISIONS)["folder"], "/srv/projects/slugger")
        for name in sorted(os.listdir(PROMPTS)):
            if name.endswith(".decisions.md"):
                text = read(os.path.join(PROMPTS, name))
                got = check_assertions.framing_of(text)
                self.assertEqual(sorted(got), sorted(check_assertions.FRAMING_KEYS), name)
                self.assertEqual(lint_prompt.parse_framing(text)[0], got, name)


class EvalsJson(unittest.TestCase):
    def test_shape_of_the_scenarios(self):
        data = json.loads(read(EVALS_JSON))
        self.assertEqual(sorted(data), ["evals"])  # no skill name: the runner reads it from the frontmatter
        found = data["evals"]
        self.assertEqual([s["id"] for s in found], list(range(1, 11)))
        self.assertEqual(tuple(s["name"] for s in found), SCENARIOS)
        for s in found:
            with self.subTest(scenario=s["name"]):
                self.assertEqual(sorted(s), ["assertions", "expected_output", "id", "name", "task"])
                self.assertTrue(set(s["assertions"]) <= set(check_assertions.KEYS))
                self.assertEqual(s["task"], "tasks/%s/task.json" % s["name"])
                task = run_skill.load_task(os.path.join(EVALS, s["task"]))
                self.assertEqual(task["id"], s["name"])
                a = s["assertions"]
                for key in ("delivered", "framing_question_count", "guide_reads", "pack_reads", "lint_errors_max", "framing"):
                    self.assertIn(key, a)
                self.assertTrue(set(a["guide_reads"]) <= set(GUIDES))
                self.assertEqual(a["guide_reads"], sorted(a["guide_reads"]))
                self.assertEqual(a["pack_reads"], [])   # the skill ships no pack
                self.assertTrue(set(a["framing"]) <= set(check_assertions.FRAMING_KEYS))
                # the model the run used, filled at check time; `choose` where the person names none
                self.assertEqual(a["framing"]["model"], "choose" if s["name"] in UNSTATED else run_skill.MODEL_SLOT)
                for entry in a.get("prompt_contains", []) + a.get("prompt_absent", []) + a.get("first_turn_contains_any", []):
                    if entry.startswith("re:"):
                        check_assertions.found(entry, "")   # compiles
                for path in a.get("fixture_unchanged", []):
                    self.assertIn(path, task["fixtures"])

    def test_every_guide_exists_and_every_framing_value_is_one_the_linter_accepts(self):
        for name in GUIDES:
            self.assertTrue(os.path.isfile(os.path.join(SKILL, "references", name)), name)
        for name, s in scenarios().items():
            framing = s["assertions"]["framing"]
            for key, value in framing.items():
                if key in lint_prompt.ENUM_VALUES:
                    self.assertIn(value, lint_prompt.ENUM_VALUES[key], (name, key))
            if "harness" in framing:
                self.assertIn("harness-%s.md" % framing["harness"], s["assertions"]["guide_reads"], name)

    def test_the_framing_question_scenarios(self):
        """Stated means not asked; otherwise the harness question is asked exactly once."""
        counts = {name: s["assertions"]["framing_question_count"] for name, s in scenarios().items()}
        self.assertEqual(counts, {"quick-slugger": 0, "vague-premium-landing": 0, "oversized-no-cap": 1,
                                  "battle-royale-lead": 0, "harness-not-stated": 1, "stated-spanish": 0,
                                  "other-harness-named": 0, "hero-loop-against-site": 1, "codex-unattended": 0,
                                  "no-subagents": 0})
        for name, count in counts.items():
            task = json.loads(read(os.path.join(EVALS, "tasks", name, "task.json")))
            stated = run_skill.MODEL_SLOT in task["opening"]
            self.assertEqual(count, 0 if stated else 1, name)
        harness = scenarios()["harness-not-stated"]["assertions"]
        self.assertIn("Where will the run execute", harness["first_turn_contains_any"])

    def test_the_guides_each_scenario_reads(self):
        """The run's guide, plus the Claude Code guide for the skill's own helper seats when the run's harness is another
        and the path has helper seats (the quick lane has none)."""
        reads = {name: s["assertions"]["guide_reads"] for name, s in scenarios().items()}
        for name in ("quick-slugger", "vague-premium-landing", "oversized-no-cap", "battle-royale-lead",
                     "harness-not-stated", "stated-spanish", "hero-loop-against-site"):
            self.assertEqual(reads[name], ["harness-claude-code.md"], name)
        self.assertEqual(reads["other-harness-named"], ["harness-generic.md"])
        self.assertEqual(scenarios()["other-harness-named"]["assertions"]["framing"]["size"], "quick")
        self.assertEqual(reads["codex-unattended"], ["harness-claude-code.md", "harness-codex.md"])
        self.assertEqual(reads["no-subagents"], ["harness-claude-code.md", "harness-generic.md"])

    def test_the_codex_and_no_subagent_scenarios(self):
        codex = scenarios()["codex-unattended"]["assertions"]
        self.assertEqual({k: codex["framing"][k] for k in ("harness", "launch", "effort", "autonomy")},
                         {"harness": "codex", "launch": "headless", "effort": "high", "autonomy": "unattended"})
        self.assertIn("model rerouted", codex["prompt_absent"])
        alone = scenarios()["no-subagents"]["assertions"]
        self.assertEqual({k: alone["framing"][k] for k in ("harness", "seat", "review")},
                         {"harness": "generic", "seat": "implementer", "review": "fresh"})
        self.assertIn(lint_prompt.FALLBACK_LABEL, alone["prompt_contains"])
        method = [e for e in alone["prompt_contains"] if "## Method" in e]
        self.assertEqual(len(method), 1)
        for text, holds in (("## Method\n\nThe review will not be independent.\n\n## The bar\n", True),
                            ("## Method\n\nThe reviews are not truly independent here.\n", True),
                            ("## Method\n\nIndependent review is a fresh seat.\n\n## Bar\n\nnot independent\n", False),
                            ("## Seats\n\nnot independent\n\n## Method\n\nOne pass.\n", False)):
            self.assertEqual(check_assertions.found(method[0], text), holds, text)

    def test_the_stated_model_is_a_slot_the_run_fills(self):
        """No task or scenario names a model id: the person's model is `{MODEL}`, which the runner fills with --model and
        check_assertions with metrics.model; the tasks that test an unstated model name none, in the opening or the
        hidden brief, and expect `model=choose`."""
        for name in SCENARIOS:
            task = run_skill.load_task(os.path.join(EVALS, "tasks", name, "task.json"))
            self.assertNotIn("example-model", task["opening"] + task["hidden_brief"], name)
            stated = name not in UNSTATED
            self.assertEqual(run_skill.MODEL_SLOT in task["opening"], stated, name)
            self.assertEqual(run_skill.MODEL_SLOT in task["hidden_brief"], stated, name)
            filled = run_skill.with_model(task, "example-model-2")
            self.assertNotIn(run_skill.MODEL_SLOT, filled["opening"] + filled["hidden_brief"], name)
            self.assertEqual("example-model-2" in filled["hidden_brief"], stated, name)
            if not stated:
                self.assertIn("You name no model", task["hidden_brief"], name)
        self.assertNotIn("example-model", read(EVALS_JSON))

    def test_no_task_names_a_real_model(self):
        import check_skill
        for name in SCENARIOS:
            folder = os.path.join(EVALS, "tasks", name)
            for file_name in sorted(os.listdir(folder)):
                text = read(os.path.join(folder, file_name))
                for pattern in check_skill.MODEL_PATTERNS:
                    self.assertIsNone(pattern.search(text), (name, file_name, pattern.pattern))
        text = read(EVALS_JSON)
        for pattern in check_skill.MODEL_PATTERNS:
            self.assertIsNone(pattern.search(text), pattern.pattern)


if __name__ == "__main__":
    unittest.main()
