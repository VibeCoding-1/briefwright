"""Tests for evals/harness/run_skill.py, driven with the fake CLI; no real `claude` call."""
import glob
import json
import os
import re
import shutil
import tempfile
import unittest
import uuid

from support import EVALS, FAKE_CLAUDE, HARNESS, LINTER, PROMPTS, SKILL, clean_env, read, run_py, write, write_json

import run_skill

RUNNER = os.path.join(HARNESS, "run_skill.py")
MODEL = "example-model-1"
NAME = run_skill.skill_name(SKILL)
COPY = ".claude/skills/%s" % NAME          # the skill's copy, from the working folder
QUICK = read(os.path.join(PROMPTS, "good-quick.md"))
QUICK_DECISIONS = read(os.path.join(PROMPTS, "good-quick.decisions.md"))
ASK = {"result": "**Q1. Where will the run execute?**\nRecommended: this harness, the one this session runs in.\n\n"
                 "Which folder?"}
DELIVER = {"result": "Delivered: prompts/slug-fix/master-prompt.md and decisions.md. Launch it with the line in "
                     "decisions.md.",
           "write": {"prompts/slug-fix/master-prompt.md": QUICK, "prompts/slug-fix/decisions.md": QUICK_DECISIONS}}
INHERITED = {"CLAUDE_CODE_SESSION_ID": "parent-session", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "30", "CLAUDE_EFFORT": "low",
             "CLAUDE_CODE_EFFORT_LEVEL": "low"}
SEAT = {"agentType": "general-purpose", "description": "helper seat: cold read"}


def rule_patterns(rules):
    """The `Bash(...)` rules of a comma-separated allowlist as regular expressions, read as Claude Code was observed
    to read them: literal up to each `*`, which matches anything; a comma inside parentheses is not a split."""
    items, depth, current = [], 0, ""
    for char in rules + ",":
        if char == "," and depth == 0:
            items.append(current)
            current = ""
            continue
        depth += {"(": 1, ")": -1}.get(char, 0)
        current += char
    assert depth == 0, rules
    return [re.compile("^" + ".*".join(re.escape(part) for part in rule[5:-1].split("*")) + "$")
            for rule in items if rule.startswith("Bash(") and rule.endswith(")")]


def in_copy(*parts):
    """A path in the bench's copy of the skill, as the fake CLI writes it ({CWD} is the call's folder)."""
    return "/".join(("{CWD}", COPY) + parts)


class HarnessCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.task_dir = os.path.join(self.tmp, "task")
        self.bench = os.path.join(self.tmp, "bench")
        self.out = os.path.join(self.tmp, "out")
        self.log = os.path.join(self.tmp, "calls.jsonl")

    def task(self, **override):
        fixtures = os.path.join(EVALS, "fixtures", "slugger")
        task = {"id": "unit-task", "opening": "prepare the prompt so another session fixes slugger", "working_folder": "project",
                "fixtures": {"project/slugger/slugger.py": os.path.relpath(os.path.join(fixtures, "slugger.py"), self.task_dir),
                             "project/slugger/test_slugger.py": os.path.relpath(os.path.join(fixtures, "test_slugger.py"),
                                                                                self.task_dir)},
                "hidden_brief": "hidden-brief.md", "max_person_turns": 3, "invoke": "auto"}
        task.update(override)
        write(os.path.join(self.task_dir, "hidden-brief.md"), "HIDDEN-BRIEF-MARKER: you want example-model-1 and frozen tests.\n")
        write_json(os.path.join(self.task_dir, "task.json"), task)
        return os.path.join(self.task_dir, "task.json")

    def run_harness(self, skill, person=None, args=(), task=None, env=None, budget="5", bench=None, model=MODEL,
                    skill_dir=None):
        script = os.path.join(self.tmp, "script.json")
        write_json(script, {"skill": skill, "person": person or [{"result": "Claude Code, example-model-1, tests frozen."}]})
        environment = clean_env(HOME=self.home, FAKE_CLAUDE_SCRIPT=script, FAKE_CLAUDE_LOG=self.log, **INHERITED)
        environment.update(env or {})
        argv = ["--skill", skill_dir or SKILL, "--task", task or self.task(), "--bench", bench or self.bench, "--out", self.out,
                "--arm", "new", "--claude-bin", FAKE_CLAUDE]
        if budget is not None:
            argv += ["--max-budget-usd", budget]
        if model is not None:
            argv += ["--model", model]
        return run_py(RUNNER, argv + list(args), env=environment)

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def result_dir(self, task_id="unit-task"):
        return os.path.join(self.out, task_id, "new")

    def metrics(self, task_id="unit-task"):
        return json.loads(read(os.path.join(self.result_dir(task_id), "metrics.json")))

    def turns(self):
        return [json.loads(line) for line in read(os.path.join(self.result_dir(), "turns.jsonl")).splitlines()]

    def reset(self):
        """Empty the bench, the output and the fake CLI's call log, for a second run in the same test."""
        for path in (self.bench, self.out):
            shutil.rmtree(path, True)
        if os.path.exists(self.log):
            os.remove(self.log)


class TaskAndRefusals(HarnessCase):
    def test_task_parsing(self):
        task = run_skill.load_task(self.task(invoke="slash"))
        self.assertEqual((task["id"], task["working_folder"], task["invoke"], task["max_person_turns"]),
                         ("unit-task", "project", "slash", 3))
        self.assertEqual(sorted(task["fixtures"]), ["project/slugger/slugger.py", "project/slugger/test_slugger.py"])
        self.assertIn("HIDDEN-BRIEF-MARKER", task["hidden_brief"])
        for bad in ({"id": "Not Kebab"}, {"invoke": "sometimes"}, {"working_folder": "/abs"}, {"working_folder": "../up"},
                    {"hidden_brief": "missing.md"}, {"fixtures": {"elsewhere/x.py": "hidden-brief.md"}},
                    {"fixtures": {"project/x.py": "no-such-file"}}, {"max_person_turns": -1}, {"opening": ""}):
            with self.assertRaises(run_skill.Refusal, msg=str(bad)):
                run_skill.load_task(self.task(**bad))

    def test_the_skills_own_scenarios_load(self):
        evals = json.loads(read(os.path.join(EVALS, "evals.json")))
        for scenario in evals["evals"]:
            task = run_skill.load_task(os.path.join(EVALS, scenario["task"]))
            self.assertTrue(task["hidden_brief"].strip(), scenario["name"])

    def test_refusals(self):
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(repo, ".git"))
        self.assertEqual(self.run_harness([DELIVER], bench=os.path.join(repo, "bench")).returncode, 2)
        os.makedirs(self.bench)
        write(os.path.join(self.bench, "left-over.txt"), "x")
        proc = self.run_harness([DELIVER])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("empty", proc.stderr)
        shutil.rmtree(self.bench)
        self.assertEqual(self.run_harness([DELIVER], budget=None).returncode, 2)
        self.assertEqual(self.run_harness([DELIVER], budget="0").returncode, 2)
        self.assertEqual(self.run_harness([DELIVER], budget="-3").returncode, 2)
        self.assertEqual(self.run_harness([DELIVER], args=["--arm", "a/b"]).returncode, 2)
        self.assertEqual(self.calls(), [])
        self.assertFalse(os.path.exists(self.bench))

    def test_the_model_is_required_and_has_no_default(self):
        proc = self.run_harness([DELIVER], model=None)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("--model", proc.stderr)
        self.assertEqual(self.run_harness([DELIVER], model="two words").returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_a_skill_without_a_frontmatter_name_is_refused(self):
        skill = os.path.join(self.tmp, "nameless")
        write(os.path.join(skill, "SKILL.md"), "# A skill\n\nNo frontmatter.\n")
        proc = self.run_harness([DELIVER], skill_dir=skill)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("frontmatter", proc.stderr)
        self.assertEqual(self.calls(), [])

    def test_the_skill_name_is_read_from_the_frontmatter(self):
        self.assertTrue(NAME)
        skill = os.path.join(self.tmp, "skill")
        for text, name in (("---\nname: sample-skill\ndescription: x\n---\n", "sample-skill"),
                           ("---\ndescription: x\nname: 'quoted-name'\n---\n", "quoted-name"),
                           ("---\nname: Not_Valid\n---\n", None), ("name: outside\n", None),
                           ("---\ndescription: x\n---\nname: after-the-frontmatter\n", None)):
            write(os.path.join(skill, "SKILL.md"), text)
            self.assertEqual(run_skill.skill_name(skill), name, text)

    def test_out_folder_must_be_empty(self):
        write(os.path.join(self.result_dir(), "metrics.json"), "{}")
        self.assertEqual(self.run_harness([DELIVER]).returncode, 2)

    def test_dry_run_makes_no_call_and_creates_nothing(self):
        proc = self.run_harness([DELIVER], args=["--dry-run"], task=self.task(invoke="slash"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("environment: env -u CLAUDE_CODE_SESSION_ID", proc.stdout)
        self.assertIn("--model %s" % MODEL, proc.stdout)
        self.assertIn("--max-budget-usd", proc.stdout)
        self.assertIn("/%s prepare the prompt" % NAME, proc.stdout)
        self.assertNotIn("CLAUDE_CODE_EFFORT_LEVEL=", proc.stdout)
        self.assertEqual(self.calls(), [])
        self.assertFalse(os.path.exists(self.bench))
        self.assertFalse(os.path.exists(self.out))


class EnvironmentAndFlags(HarnessCase):
    def test_every_call_gets_the_effort_and_the_unsets_and_no_subagent_variable(self):
        proc = self.run_harness([ASK, DELIVER], args=["--effort", "high"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertEqual([c["role"] for c in calls], ["skill", "person", "skill"])
        for call in calls:
            env = call["env"]
            self.assertIsNone(env["CLAUDE_CODE_SESSION_ID"])
            self.assertIsNone(env["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"])
            self.assertIsNone(env["CLAUDE_EFFORT"])
            self.assertEqual(env["CLAUDE_CODE_EFFORT_LEVEL"], "high")
            self.assertEqual([name for name in env if "SUBAGENT" in name], [])
            argv = call["argv"]
            for flag, value in (("--model", MODEL), ("--effort", "high"), ("--output-format", "json"),
                                ("--permission-mode", "acceptEdits")):
                self.assertEqual(argv[argv.index(flag) + 1], value)
            self.assertIn("--strict-mcp-config", argv)
            self.assertIn("-p", argv)
            self.assertEqual(argv[-2], "--")
        self.assertEqual(self.metrics()["effort"], "high")

    def test_without_effort_no_effort_is_set_even_when_inherited(self):
        proc = self.run_harness([ASK, DELIVER])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for call in self.calls():
            self.assertIsNone(call["env"]["CLAUDE_CODE_EFFORT_LEVEL"])
            self.assertIsNone(call["env"]["CLAUDE_EFFORT"])
            self.assertNotIn("--effort", call["argv"])
        self.assertIsNone(self.metrics()["effort"])
        self.assertNotIn("CLAUDE_CODE_EFFORT_LEVEL=", read(os.path.join(self.result_dir(), "commands.txt")))

    def test_allowlist_for_the_skill_and_no_tools_for_the_person(self):
        self.run_harness([ASK, DELIVER])
        skill, person, _ = self.calls()
        rules = skill["argv"][skill["argv"].index("--allowed-tools") + 1]
        copy = os.path.join(self.bench, "project", *COPY.split("/"))
        self.assertEqual(rules.replace(os.path.realpath(self.bench), self.bench),
                         run_skill.default_allowed_tools(copy, NAME))
        self.assertIn("Bash(python3 %s/scripts/lint_prompt.py *)" % copy, rules.replace(os.path.realpath(self.bench), self.bench))
        self.assertIn("Bash(python3 %s/scripts/lint_prompt.py *)" % COPY, rules)
        commands = read(os.path.join(self.result_dir(), "commands.txt"))
        self.assertIn("Bash(python3 <bench>/project/%s/scripts/lint_prompt.py *)" % COPY, commands)
        for line in commands.split("\n"):
            if "--allowed-tools" in line:
                self.assertNotIn(self.bench, line)  # the logged call shows <bench>, as its `cd` does
        self.assertEqual(skill["argv"][skill["argv"].index("--max-turns") + 1], "80")
        self.assertEqual(skill["argv"][skill["argv"].index("--disallowed-tools") + 1], "AskUserQuestion")
        self.assertNotIn("--allowed-tools", person["argv"])
        self.assertEqual(person["argv"][person["argv"].index("--disallowed-tools") + 1],
                         "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Agent,Skill")
        self.assertEqual(person["argv"][person["argv"].index("--max-turns") + 1], "1")
        self.assertTrue(person["cwd"].endswith(os.sep + "person"))
        self.assertTrue(skill["cwd"].endswith(os.sep + "project"))
        self.assertEqual(os.listdir(person["cwd"]), [])

    def test_on_a_symlinked_bench_the_rules_anchor_the_canonical_folder_claude_code_runs_in(self):
        """Claude Code's working folder is the canonical path, so on a symlinked bench (as temporary folders are on
        some systems) rules built from the bench as given would match none of SKILL.md's absolute lint calls."""
        real = os.path.join(self.tmp, "real dir")
        os.makedirs(real)
        link = os.path.join(self.tmp, "link")
        os.symlink(real, link)
        spec = dict(DELIVER, records=[{"tool_use": {"name": "Read", "input": {
            "file_path": in_copy("references", "harness-claude-code.md")}}}])
        proc = self.run_harness([spec], bench=os.path.join(link, "bench"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        call = self.calls()[0]
        cwd = call["cwd"]  # the fake CLI records os.getcwd(), the canonical path, as the real CLI's process does
        self.assertEqual(cwd, os.path.join(os.path.realpath(real), "bench", "project"))
        skill_dir = cwd + "/" + COPY
        rules = call["argv"][call["argv"].index("--allowed-tools") + 1]
        self.assertEqual(rules, run_skill.default_allowed_tools(skill_dir, NAME))
        self.assertNotIn(link + os.sep, rules)
        lint = 'python3 "%s/scripts/lint_prompt.py" "%s/prompts/slug-fix/master-prompt.md" --decisions "%s/prompts/slug-fix/decisions.md"' % (
            skill_dir, cwd, cwd)
        self.assertTrue(any(p.match(lint) for p in rule_patterns(rules)), lint)
        self.assertEqual(self.metrics()["guide_reads"], ["harness-claude-code.md"])
        commands = read(os.path.join(self.result_dir(), "commands.txt"))
        self.assertIn("Bash(python3 <bench>/project/%s/scripts/lint_prompt.py *)" % COPY, commands)
        self.assertIn("$ cd <bench>/project && ", commands)
        # the refusal of a path that would break the rules reads the canonical path the rules are built from
        broken = os.path.join(self.tmp, "real (copy)")
        os.makedirs(broken)
        os.symlink(broken, os.path.join(self.tmp, "plain"))
        os.remove(self.log)
        shutil.rmtree(self.out)
        proc = self.run_harness([DELIVER], bench=os.path.join(self.tmp, "plain", "bench"))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("pass --allowed-tools", proc.stderr)
        self.assertEqual(self.calls(), [])

    def test_custom_allowlist_replaces_the_default(self):
        self.run_harness([DELIVER], args=["--allowed-tools", "Bash(git status)"])
        argv = self.calls()[0]["argv"]
        self.assertEqual(argv[argv.index("--allowed-tools") + 1], "Bash(git status)")

    def test_each_call_gets_what_the_budget_has_left(self):
        self.run_harness([dict(ASK, cost=1.25), dict(DELIVER, cost=0.5)], person=[{"result": "Yes.", "cost": 0.25}])
        budgets = [float(c["argv"][c["argv"].index("--max-budget-usd") + 1]) for c in self.calls()]
        self.assertEqual(budgets, [5.0, 3.75, 3.5])
        self.assertAlmostEqual(self.metrics()["total_cost_usd"], 2.0)

    def test_a_resumed_call_counts_only_what_it_added(self):
        """A `--resume` call reports in total_cost_usd the session's cumulative cost (the fake CLI reports so, as the
        real one was observed to); summing those figures would inflate the run's total, the cap each call is passed
        and the max-budget stop. Costs are exact in binary."""
        skill = [dict(ASK, cost=1.25), dict(ASK, cost=0.5), dict(DELIVER, cost=0.75)]
        person = [{"result": "Claude Code.", "cost": 0.25}, {"result": "This folder.", "cost": 0.125}]
        proc = self.run_harness(skill, person=person, budget="10")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertEqual([c["role"] for c in calls], ["skill", "person", "skill", "person", "skill"])
        budgets = [float(c["argv"][c["argv"].index("--max-budget-usd") + 1]) for c in calls]
        self.assertEqual(budgets, [10.0, 8.75, 8.5, 8.0, 7.875])  # the cap minus the real spend so far
        self.assertEqual(self.metrics()["total_cost_usd"], 2.875)  # 1.25 + 0.25 + 0.5 + 0.125 + 0.75
        turns = self.turns()[1:]
        self.assertEqual([(t["role"], t["cost_usd"], t["reported_total_cost_usd"]) for t in turns],
                         [("skill", 1.25, 1.25), ("person", 0.25, 0.25), ("skill", 0.5, 1.75), ("person", 0.125, 0.125),
                          ("skill", 0.75, 2.5)])
        # the last figure the session reported is its transcript's own running total
        transcript = glob.glob(os.path.join(self.result_dir(), "transcripts", "*.jsonl"))[0]
        states = [json.loads(line)["totalCostUSD"] for line in read(transcript).splitlines() if '"cost-state"' in line]
        self.assertEqual(states, [1.25, 1.75, 2.5])
        self.assertIn("cost 0.5, reported 1.75", read(os.path.join(self.result_dir(), "commands.txt")))

    def test_a_running_total_that_falls_counts_as_reported(self):
        """A resumed figure below the session's previous one means the CLI's counter restarted, so the call counts its
        figure as reported, never 0: the budget is never undercounted; the next resumed call subtracts from the new
        figure. The fake's running total restarts with the figure it reports, so the third call reports 0.5 + its own
        0.25 by itself."""
        proc = self.run_harness([dict(ASK, cost=1.5), dict(ASK, reported_cost=0.5), dict(DELIVER, cost=0.25)],
                                person=[{"result": "Claude Code.", "cost": 0.25}, {"result": "Yes.", "cost": 0.125}],
                                budget="10")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.metrics()["total_cost_usd"], 2.625)  # 1.5 + 0.25 + 0.5 + 0.125 + 0.25
        self.assertEqual([(t["cost_usd"], t["reported_total_cost_usd"]) for t in self.turns() if t["role"] == "skill"],
                         [(1.5, 1.5), (0.5, 0.5), (0.25, 0.75)])
        transcript = glob.glob(os.path.join(self.result_dir(), "transcripts", "*.jsonl"))[0]
        states = [json.loads(line)["totalCostUSD"] for line in read(transcript).splitlines() if '"cost-state"' in line]
        self.assertEqual(states, [1.5, 0.5, 0.75])  # the transcript's running total is what the CLI reported


class TurnLoop(HarnessCase):
    def test_session_id_then_resume_and_the_person_sees_brief_and_conversation(self):
        self.run_harness([ASK, DELIVER], task=self.task(invoke="slash"))
        skill1, person, skill2 = self.calls()
        session = skill1["argv"][skill1["argv"].index("--session-id") + 1]
        self.assertNotIn("--resume", skill1["argv"])
        self.assertEqual(skill2["argv"][skill2["argv"].index("--resume") + 1], session)
        self.assertEqual(skill1["prompt"], "/%s prepare the prompt so another session fixes slugger" % NAME)
        self.assertIn("HIDDEN-BRIEF-MARKER", person["prompt"])
        self.assertIn("<person>\nprepare the prompt so another session fixes slugger\n</person>", person["prompt"])
        self.assertIn("Where will the run execute", person["prompt"])
        self.assertNotIn("{CONVERSATION}", person["prompt"])
        self.assertEqual(skill2["prompt"], "Claude Code, example-model-1, tests frozen.")
        self.assertNotEqual(person["argv"][person["argv"].index("--session-id") + 1], session)
        self.assertNotIn("--resume", person["argv"])

    def test_the_stated_model_is_the_run_s_model(self):
        """`{MODEL}` in a task's opening and hidden brief is --model, filled before the first call."""
        task = self.task(opening="prepare the prompt for a session on %s" % run_skill.MODEL_SLOT)
        write(os.path.join(self.task_dir, "hidden-brief.md"), "HIDDEN-BRIEF-MARKER: the model is %s.\n" % run_skill.MODEL_SLOT)
        self.run_harness([ASK, DELIVER], task=task, model="example-model-2")
        skill1, person = self.calls()[:2]
        self.assertEqual(skill1["prompt"], "prepare the prompt for a session on example-model-2")
        self.assertIn("HIDDEN-BRIEF-MARKER: the model is example-model-2.", person["prompt"])
        self.assertIn("<person>\nprepare the prompt for a session on example-model-2\n</person>", person["prompt"])
        self.assertNotIn(run_skill.MODEL_SLOT, skill1["prompt"] + person["prompt"])

    def test_an_auto_task_opens_with_its_words_alone(self):
        self.run_harness([DELIVER])
        self.assertEqual(self.calls()[0]["prompt"], "prepare the prompt so another session fixes slugger")

    def test_each_person_call_has_a_session_of_its_own(self):
        """A call with no --session-id launched inside a Claude session takes the calling session's id (the fake does
        the same under FAKE_CLAUDE_PARENT_SESSION), so a read of the person's transcripts would scan the caller's own.
        Each person call gets a fresh --session-id, distinct from the skill session's and from every other person
        call's, and only its own transcript is read."""
        parent = str(uuid.uuid4())
        # the caller's transcript names another address, so a read of it would show as that address redacted
        caller = "caller.session" + "@" + "mail.example"
        context = {"type": "attachment", "attachment": {"type": "session_context", "context": {
            "userEmail": "The user's email address is %s." % caller}}}
        caller_log = os.path.join(self.home, ".claude", "projects", "-caller-folder", parent + ".jsonl")
        write(caller_log, json.dumps(context) + "\n")
        before = read(caller_log)
        proc = self.run_harness([ASK, ASK, dict(DELIVER, result="Delivered; a copy goes to %s." % caller)],
                                person=[{"result": "Claude Code."}, {"result": "This folder."}],
                                env={"FAKE_CLAUDE_PARENT_SESSION": parent})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        skill = calls[0]["argv"][calls[0]["argv"].index("--session-id") + 1]
        persons = [c["argv"][c["argv"].index("--session-id") + 1] for c in calls if c["role"] == "person"]
        self.assertEqual(len(persons), 2)
        self.assertEqual(len({skill, parent} | set(persons)), 4)
        for session in persons:
            self.assertEqual(str(uuid.UUID(session)), session)
            self.assertEqual(len(glob.glob(os.path.join(self.home, ".claude", "projects", "*", session + ".jsonl"))), 1)
        self.assertEqual([t["session_id"] for t in self.turns() if t["role"] == "person"][1:], persons)
        self.assertEqual(read(caller_log), before)  # nothing was appended to the caller's session
        self.assertIn("a copy goes to %s." % caller, read(os.path.join(self.result_dir(), "turns.jsonl")))

    def test_a_reply_starting_with_a_dash_stays_a_prompt(self):
        self.run_harness([ASK, DELIVER], person=[{"result": "- (a) recommended"}])
        self.assertEqual(self.calls()[2]["prompt"], "- (a) recommended")

    def test_the_person_sees_every_main_chain_text_of_the_turn(self):
        """The result is only the turn's last text; a skill that writes its questions and then waits on a background
        seat before a closing line would have its questions lost. The person sees every main-chain text the call
        wrote, in order, from the transcript: no sidechain text, no tool result, no background seat's notification
        (a user record in the middle of the turn)."""
        questions = ("**Q1. Where will the run execute?**\nRecommended: this harness.\n\n"
                     "**Q2. May the tests change?**\nRecommended: no.")
        waiting = "I am waiting on a background check of the repository before the next step."
        spec = {"result": waiting, "records": [
            {"text": questions},
            {"tool_use": {"name": "Agent", "input": {"description": "helper seat: fact-finding", "run_in_background": True}}},
            {"user": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "TOOL-RESULT-MARKER"}]},
            {"text": "SIDECHAIN-MARKER: the seat's own notes", "sidechain": True},
            {"user": "<task-notification>NOTIFICATION-MARKER: the background check finished</task-notification>"}]}
        proc = self.run_harness([spec, dict(ASK, no_transcript=True), DELIVER],
                                person=[{"result": "Claude Code; no."}, {"result": "This folder."}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertEqual([c["role"] for c in calls], ["skill", "person", "skill", "person", "skill"])
        shown = calls[1]["prompt"]
        self.assertIn(questions, shown)
        self.assertIn(waiting, shown)
        self.assertLess(shown.index(questions), shown.index(waiting))
        for marker in ("SIDECHAIN-MARKER", "TOOL-RESULT-MARKER", "NOTIFICATION-MARKER"):
            self.assertNotIn(marker, shown)
        # the second call wrote no transcript: its result is shown, and turns.jsonl says which source was used
        self.assertIn(ASK["result"], calls[3]["prompt"])
        skill = [t for t in self.turns() if t["role"] == "skill"]
        self.assertEqual([t["text_source"] for t in skill], ["transcript", "result", "transcript"])
        self.assertEqual(skill[0]["text"], questions + "\n\n" + waiting)
        self.assertEqual(skill[1]["text"], ASK["result"])
        self.assertEqual(skill[2]["text"], DELIVER["result"])
        # the questions the person saw are the questions counted (and check_assertions reads the same text)
        self.assertEqual((self.metrics()["questions_asked"], self.metrics()["framing_question_turns"]), (4, 2))

    def test_api_error_and_synthetic_records_are_not_shown(self):
        """An API error the CLI retried (`isApiErrorMessage`) and any record of the `<synthetic>` model are written as
        main-chain assistant records, never the skill's words. Each flag is tested alone."""
        questions = "**Q1. May the tests change?**\nRecommended: no."
        closing = "Waiting for your answers."
        spec = {"result": closing, "records": [
            {"text": "API Error: 529 overloaded (BOTH-MARKER)", "model": "<synthetic>", "api_error": True},
            {"text": questions},
            {"text": "No response requested. (SYNTHETIC-MARKER)", "model": "<synthetic>"},
            {"text": "API Error: 500 (FLAG-MARKER)", "api_error": True}]}
        proc = self.run_harness([spec, DELIVER])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        shown = self.calls()[1]["prompt"]
        self.assertIn(questions + "\n\n" + closing, shown)
        for marker in ("BOTH-MARKER", "SYNTHETIC-MARKER", "FLAG-MARKER"):
            self.assertNotIn(marker, shown)
        first = [t for t in self.turns() if t["role"] == "skill"][0]
        self.assertEqual((first["text"], first["text_source"]), (questions + "\n\n" + closing, "transcript"))

    def test_the_delivered_test_reads_the_closing_message(self):
        """`delivered` reads the call's result, the closing message; a question earlier in the turn is shown to the
        person but does not hold back a delivery."""
        spec = dict(DELIVER, records=[{"text": "The draft is on disk. Should the tests stay frozen?"}])
        proc = self.run_harness([spec])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.metrics()["stop_reason"], "delivered")
        self.assertEqual(self.metrics()["person_turns"], 0)

    def test_custom_person_prompt(self):
        custom = os.path.join(self.tmp, "person.md")
        write(custom, "CUSTOM RULES\n{HIDDEN_BRIEF}\n---\n{CONVERSATION}\n")
        self.run_harness([ASK, DELIVER], args=["--person-prompt", custom])
        self.assertTrue(self.calls()[1]["prompt"].startswith("CUSTOM RULES\nHIDDEN-BRIEF-MARKER"))
        write(custom, "no slots\n")
        shutil.rmtree(self.bench)
        self.assertEqual(self.run_harness([DELIVER], args=["--person-prompt", custom]).returncode, 2)


class StopReasons(HarnessCase):
    def check(self, proc, code, stop):
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        self.assertEqual(self.metrics()["stop_reason"], stop)

    def test_delivered_only_when_the_prompt_exists_and_nothing_is_asked(self):
        draft_and_question = dict(DELIVER, result="The draft is on disk. The cold read asks: may tests be edited?")
        closing = {"result": "Delivered. Launch it with the line in decisions.md."}
        proc = self.run_harness([draft_and_question, closing], person=[{"result": "No."}])
        self.check(proc, 0, "delivered")
        self.assertEqual(self.metrics()["person_turns"], 1)
        self.assertTrue(self.metrics()["delivered"])

    def test_no_prompt_on_disk_is_not_delivered(self):
        proc = self.run_harness([{"result": "All done, nothing asked."}], task=self.task(max_person_turns=0))
        self.check(proc, 3, "max-person-turns")

    def test_question_forms(self):
        self.assertTrue(run_skill.asks("Text.\n\n**Q2. Tests frozen?** (a) yes"))
        self.assertTrue(run_skill.asks("Shall I go on?**"))
        self.assertTrue(run_skill.asks("Plan:\n- one\n- is this right?\n- three"))
        self.assertFalse(run_skill.asks("Delivered.\n\n```\nwhat? inside a fence?\n```"))
        self.assertFalse(run_skill.asks("Why? Because the tests say so."))
        self.assertEqual(run_skill.questions_in("**Q1. A?**\nWhy it matters.\n\n**Q2. B?**\n\nAnd you?"), 3)

    def test_max_turns_is_read_before_is_error(self):
        proc = self.run_harness([{"subtype": "error_max_turns"}])
        self.check(proc, 3, "max-turns")

    def test_max_budget_from_the_result_and_from_the_spend(self):
        self.check(self.run_harness([{"subtype": "error_max_budget_usd"}]), 3, "max-budget")
        self.reset()
        proc = self.run_harness([dict(ASK, cost=0.6), DELIVER], person=[{"result": "x", "cost": 0.5}], budget="1")
        self.check(proc, 3, "max-budget")
        self.assertEqual([c["role"] for c in self.calls()], ["skill", "person"])

    def test_a_delivery_on_the_call_that_crosses_the_cap_is_delivered(self):
        """The delivered test comes before the spend test, so a run that delivers on the call that crossed the cap is
        delivered."""
        self.check(self.run_harness([dict(DELIVER, cost=1.5)], budget="1"), 0, "delivered")
        self.assertEqual(self.metrics()["total_cost_usd"], 1.5)
        # a call the CLI cut stops max-budget even with a prompt file on disk and nothing asked: the file may be
        # unfinished
        self.reset()
        cut = dict(DELIVER, subtype="error_max_budget_usd", result="Delivered.")
        self.check(self.run_harness([cut], budget="1"), 3, "max-budget")
        self.assertTrue(os.path.isfile(os.path.join(self.result_dir(), "prompt", "slug-fix", "master-prompt.md")))
        # a call that crosses the cap and asks: the spend test comes before the next person call
        self.reset()
        self.check(self.run_harness([dict(ASK, cost=1.5)], budget="1"), 3, "max-budget")
        self.assertEqual([c["role"] for c in self.calls()], ["skill"])

    def test_max_person_turns(self):
        proc = self.run_harness([ASK], task=self.task(max_person_turns=2))
        self.check(proc, 3, "max-person-turns")
        self.assertEqual((self.metrics()["skill_turns"], self.metrics()["person_turns"]), (3, 2))
        self.reset()
        proc = self.run_harness([ASK], task=self.task(max_person_turns=2), args=["--max-person-turns", "0"])
        self.check(proc, 3, "max-person-turns")
        self.assertEqual(self.metrics()["person_turns"], 0)

    def test_errors(self):
        self.check(self.run_harness([{"subtype": "error_during_execution"}]), 4, "error")
        for spec, extra in (({"stdout": "this is not json", "exit": 1}, []), ({"sleep": 5}, ["--timeout-s", "1"])):
            self.reset()
            self.check(self.run_harness([spec], args=extra), 4, "error")
        self.reset()
        self.check(self.run_harness([ASK], person=[{"result": "", "subtype": "success"}]), 4, "error")


class PromptLocation(HarnessCase):
    """Where the harness looks for the produced prompt."""

    @staticmethod
    def deliver_at(folder, result=DELIVER["result"]):
        return {"result": result, "write": {folder + "/master-prompt.md": QUICK, folder + "/decisions.md": QUICK_DECISIONS}}

    def test_a_prompt_under_a_project_folder_is_delivered_collected_and_linted(self):
        """A skill may write its prompt under a project folder the person's brief names,
        `<working folder>/<project>/prompts/<slug>/`: it is found, collected and linted."""
        proc = self.run_harness([self.deliver_at("skyline_restaurant_bar/prompts/slug-fix")])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        m = self.metrics()
        self.assertEqual((m["stop_reason"], m["person_turns"]), ("delivered", 0))
        self.assertEqual((m["prompt_dir"], m["prompt_candidates"]),
                         ("skyline_restaurant_bar/prompts/slug-fix", ["skyline_restaurant_bar/prompts/slug-fix"]))
        folder = os.path.join(self.result_dir(), "prompt", "slug-fix")
        self.assertEqual((read(os.path.join(folder, "master-prompt.md")), read(os.path.join(folder, "decisions.md"))),
                         (QUICK, QUICK_DECISIONS))
        lint = json.loads(read(os.path.join(self.result_dir(), "lint.json")))
        self.assertTrue(lint["file"].endswith("/project/skyline_restaurant_bar/prompts/slug-fix/master-prompt.md"), lint)
        self.assertEqual((m["lint_errors"], m["prompt_words"]), (0, len(QUICK.split())))

    def test_the_top_prompts_folder_first_then_the_newest_deeper_one(self):
        # a prompt in <working folder>/prompts/ wins over a newer one deeper down, which is then not a candidate
        ask = dict(self.deliver_at("prompts/first"), result=ASK["result"])
        proc = self.run_harness([ask, self.deliver_at("deep/prompts/second")])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual((self.metrics()["prompt_dir"], self.metrics()["prompt_candidates"]), ("prompts/first", ["prompts/first"]))
        # with none there, the newest by mtime at any depth up to 3 wins, and every candidate is recorded
        self.reset()
        ask = dict(self.deliver_at("a/prompts/older"), result=ASK["result"])
        proc = self.run_harness([ask, self.deliver_at("b/c/d/prompts/newer")])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        m = self.metrics()
        self.assertEqual((m["stop_reason"], m["person_turns"]), ("delivered", 1))
        self.assertEqual((m["prompt_dir"], m["prompt_candidates"]), ("b/c/d/prompts/newer", ["a/prompts/older", "b/c/d/prompts/newer"]))
        self.assertTrue(os.path.isfile(os.path.join(self.result_dir(), "prompt", "newer", "master-prompt.md")))
        self.assertFalse(os.path.exists(os.path.join(self.result_dir(), "prompt", "older")))  # another prompts/ folder

    def test_skipped_too_deep_and_unchanged_fixture_prompts_are_not_prompts(self):
        """`.claude/`, `.git/` and `node_modules/` are skipped, a `prompts/` folder more than three levels down is not
        read, a folder named master-prompt.md is not a prompt, and a master-prompt.md the task's fixtures put in the
        bench counts only once its content changes: the deeper search must not read a project's old prompt as this
        run's delivery."""
        source = os.path.relpath(os.path.join(PROMPTS, "good-quick.md"), self.task_dir)
        task = self.task(max_person_turns=0, fixtures={"project/docs/prompts/old/master-prompt.md": source})
        writes = {}
        for folder in (".claude/prompts/a", ".git/prompts/b", "node_modules/pkg/prompts/c", "vendor/node_modules/prompts/d",
                       "a/b/c/d/prompts/e"):
            writes.update(self.deliver_at(folder)["write"])
        writes["docs/prompts/old/master-prompt.md"] = QUICK  # the fixture rewritten with the same bytes
        writes["z/prompts/f/master-prompt.md/notes.txt"] = "a folder by that name is not a prompt"
        proc = self.run_harness([{"result": "All done, nothing asked.", "write": writes}], task=task)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        m = self.metrics()
        self.assertEqual((m["stop_reason"], m["prompt_dir"], m["prompt_candidates"]), ("max-person-turns", None, []))
        self.assertEqual(os.listdir(os.path.join(self.result_dir(), "prompt")), [])
        # the same fixture, once the skill changes it, is the delivered prompt (rewritten unchanged, it is not)
        self.reset()
        revised = self.deliver_at("docs/prompts/old")
        revised["write"]["docs/prompts/old/master-prompt.md"] = QUICK + "\n"
        proc = self.run_harness([revised], task=task)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.metrics()["prompt_dir"], "docs/prompts/old")


class Metrics(HarnessCase):
    def test_metrics(self):
        helper = "example-helper-model"   # a model the CLI bills for its own helpers: recorded, never a seat
        first = dict(ASK, cost=0.5, model_usage=[MODEL, helper], user_records=["<command-name>/%s</command-name>" % NAME],
                     records=[{"tool_use": {"name": "Read", "input": {"file_path": in_copy("SKILL.md")}}}])
        second = dict(DELIVER, cost=0.5, records=[
            {"tool_use": {"name": "Read", "input": {"file_path": in_copy("references", "harness-codex.md")}}},
            {"tool_use": {"name": "Read", "input": {"file_path": in_copy("references", "harness-codex.md"), "offset": 40}}},
            {"tool_use": {"name": "Read", "input": {"file_path": in_copy("references", "harness-claude-code.md")}}},
            {"tool_use": {"name": "Read", "input": {"file_path": in_copy("references", "methods.md")}}},
            {"tool_use": {"name": "Read", "input": {"file_path": in_copy("packs", "README.md")}}},
            {"tool_use": {"name": "Read", "input": {"file_path": in_copy("packs", "example-pack.md")}}},
            {"tool_use": {"name": "Read", "input": {"file_path": "{CWD}/notes/references/harness-elsewhere.md"}}},
            {"tool_use": {"name": "Grep", "input": {"path": in_copy("packs", "other-pack.md"), "pattern": "MATCHES"}}},
            {"tool_use": {"name": "Skill", "input": {"skill": NAME}}}],
            subagents={"agent-a1": {"meta": SEAT, "models": [MODEL],
                                    "reads": [in_copy("references", "harness-generic.md")]}})
        proc = self.run_harness([first, second], person=[{"result": "Claude Code.", "cost": 0.25}],
                                args=["--linter", LINTER])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        m = self.metrics()
        self.assertEqual(sorted(m), sorted([
            "task", "arm", "model", "delivered", "stop_reason", "skill_turns", "person_turns", "total_cost_usd", "wall_s",
            "questions_asked", "framing_question_turns", "guide_reads", "pack_reads", "skill_loaded", "effort",
            "budget_usd", "prompt_words", "lint_errors", "lint_warnings", "lint_allowed", "prompt_dir",
            "prompt_candidates", "model_usage_keys"]))
        self.assertEqual((m["task"], m["arm"], m["model"], m["effort"], m["budget_usd"]), ("unit-task", "new", MODEL, None, 5.0))
        self.assertEqual((m["skill_turns"], m["person_turns"]), (2, 1))
        self.assertAlmostEqual(m["total_cost_usd"], 1.25)
        self.assertEqual((m["questions_asked"], m["framing_question_turns"]), (2, 1))
        # the main chain's Reads of the copy's guides and packs; a subagent's read, a Grep, a file of the same name
        # outside the copy, a reference that is not a guide and the packs README are not counted
        self.assertEqual(m["guide_reads"], ["harness-claude-code.md", "harness-codex.md"])
        self.assertEqual(m["pack_reads"], ["example-pack.md"])
        self.assertTrue(m["skill_loaded"])
        self.assertEqual((m["lint_errors"], m["lint_warnings"], m["lint_allowed"]), (0, 0, 0))
        self.assertEqual(m["prompt_words"], len(QUICK.split()))
        self.assertEqual(m["model_usage_keys"], sorted([MODEL, helper]))   # every call's modelUsage keys, once each

    def test_skill_loaded_from_each_kind_of_evidence_and_only_for_this_skill(self):
        evidence = (([], [{"tool_use": {"name": "Skill", "input": {"skill": NAME}}}], True),
                    (["<command-name>/%s</command-name>" % NAME], [], True),
                    ([], [{"tool_use": {"name": "Read", "input": {"file_path": in_copy("SKILL.md")}}}], True),
                    ([], [{"tool_use": {"name": "Skill", "input": {"skill": NAME + "-other"}}}], False),
                    (["<command-name>/%s-other</command-name>" % NAME], [], False),
                    ([], [{"tool_use": {"name": "Read", "input": {"file_path": "{CWD}/.claude/skills/other/SKILL.md"}}}], False),
                    ([], [], False))
        for user_records, records, loaded in evidence:
            with self.subTest(user_records=user_records, records=records):
                self.reset()
                self.run_harness([dict(DELIVER, user_records=user_records, records=records)])
                self.assertEqual(self.metrics()["skill_loaded"], loaded)

    def test_the_framing_question_is_matched_on_its_words(self):
        self.assertTrue(run_skill.is_framing_question("**Q1. Where will the run execute?**\nWhy."))
        self.assertTrue(run_skill.is_framing_question("Before I go on: where will the run execute?"))
        self.assertFalse(run_skill.is_framing_question("Which model runs this, and at what effort?"))
        self.assertFalse(run_skill.is_framing_question("Where will the run execute: Claude Code, as you said."))
        self.assertFalse(run_skill.is_framing_question("```\nWhere will the run execute?\n```"))


class OutputsAndFixtures(HarnessCase):
    def test_output_layout_turns_and_commands(self):
        self.run_harness([ASK, DELIVER])
        folder = self.result_dir()
        self.assertEqual(sorted(os.listdir(folder)), ["commands.txt", "fixtures.json", "lint.json", "metrics.json", "prompt",
                                                      "transcripts", "turns.jsonl"])
        self.assertTrue(os.path.isfile(os.path.join(folder, "prompt", "slug-fix", "master-prompt.md")))
        self.assertEqual(len(glob.glob(os.path.join(folder, "transcripts", "*.jsonl"))), 1)
        turns = [json.loads(line) for line in read(os.path.join(folder, "turns.jsonl")).splitlines()]
        self.assertEqual([t["role"] for t in turns], ["person", "skill", "person", "skill"])
        self.assertEqual([t["turn"] for t in turns], [0, 1, 2, 3])
        for turn in turns:
            self.assertEqual(sorted(turn), ["cost_usd", "duration_ms", "is_error", "num_turns", "reported_total_cost_usd",
                                            "role", "session_id", "text", "text_source", "turn"])
        self.assertEqual([t["text_source"] for t in turns], ["task", "transcript", "result", "transcript"])
        commands = read(os.path.join(folder, "commands.txt"))
        self.assertEqual(commands.count("$ cd <bench>/"), 3)
        self.assertIn("env -u CLAUDE_CODE_SESSION_ID", commands)
        self.assertIn("skill copied to <bench>/project/%s" % COPY, commands)
        self.assertIn("lint: exit 0", commands)
        lint = json.loads(read(os.path.join(folder, "lint.json")))
        self.assertEqual(lint["errors"], 0)

    def test_the_skill_is_copied_whole_under_its_frontmatter_name_without_caches(self):
        source = os.path.join(self.tmp, "a-folder-with-another-name")
        shutil.copytree(SKILL, source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        write(os.path.join(source, "scripts", "__pycache__", "lint_prompt.cpython-39.pyc"), "cache")
        write(os.path.join(source, "scripts", "stray.pyc"), "cache")
        write(os.path.join(source, ".git", "HEAD"), "ref: refs/heads/main\n")
        proc = self.run_harness([DELIVER], skill_dir=source)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        copied = os.path.join(self.bench, "project", *COPY.split("/"))
        self.assertEqual(sorted(os.listdir(os.path.join(self.bench, "project", ".claude", "skills"))), [NAME])
        for rel in ("SKILL.md", "scripts/lint_prompt.py", "references/harness-generic.md"):
            self.assertTrue(os.path.isfile(os.path.join(copied, *rel.split("/"))), rel)
        for rel in ("scripts/__pycache__", "scripts/stray.pyc", ".git"):
            self.assertFalse(os.path.exists(os.path.join(copied, *rel.split("/"))), rel)
        expected = sorted(os.path.relpath(os.path.join(folder, name), SKILL)
                          for folder, dirs, files in os.walk(SKILL) for name in files
                          if "__pycache__" not in folder and not name.endswith(".pyc"))
        got = sorted(os.path.relpath(os.path.join(folder, name), copied) for folder, _, files in os.walk(copied) for name in files)
        self.assertEqual(got, expected)
        self.assertEqual(sorted(os.listdir(self.bench)), ["person", "project"])

    def test_fixtures_json_before_and_after(self):
        spec = dict(DELIVER, write=dict(DELIVER["write"], **{"slugger/slugger.py": "changed\n"}),
                    delete=["slugger/test_slugger.py"])
        self.run_harness([spec])
        fixtures = json.loads(read(os.path.join(self.result_dir(), "fixtures.json")))
        changed, deleted = fixtures["project/slugger/slugger.py"], fixtures["project/slugger/test_slugger.py"]
        self.assertNotEqual(changed["before"], changed["after"])
        self.assertIsNone(deleted["after"])
        self.reset()
        self.run_harness([DELIVER])
        fixtures = json.loads(read(os.path.join(self.result_dir(), "fixtures.json")))
        self.assertTrue(all(v["before"] == v["after"] for v in fixtures.values()))

    def test_secret_values_never_reach_the_copied_files(self):
        # built at run time, and fake by name, so no file holds anything shaped like a real credential
        key, token, oauth = ("-".join(("fake", "api", "key", "0123456789")), "-".join(("fake", "auth", "token", "abcdef")),
                             "-".join(("fake", "oauth", "access", "token", "0123456789ab")))
        write_json(os.path.join(self.home, ".claude", ".credentials.json"), {"claudeAiOauth": {"accessToken": oauth}})
        dump = "SKILL_TEST_API_KEY=%s\nSERVICE_AUTH_TOKEN=%s\nGIT_AUTHOR_NAME=Alexandra\ncredentials: %s" % (key, token, oauth)
        spec = dict(DELIVER, result="Environment read:\n" + dump + "\nDelivered.",
                    records=[{"text": dump}, {"tool_use": {"name": "Bash", "input": {"command": "env", "output": dump}}}])
        spec["write"] = dict(DELIVER["write"], **{"prompts/slug-fix/notes.md": dump})
        proc = self.run_harness([spec], env={"SKILL_TEST_API_KEY": key, "SERVICE_AUTH_TOKEN": token,
                                             "GIT_AUTHOR_NAME": "Alexandra"})
        self.assertIn(proc.returncode, (0, 3), proc.stdout + proc.stderr)
        seen = []
        for folder, _, files in os.walk(self.result_dir()):
            for name in files:
                text = read(os.path.join(folder, name))
                seen.append(name)
                for secret in (key, token, oauth):
                    self.assertNotIn(secret, text, name)
        self.assertIn("notes.md", seen)
        turns = read(os.path.join(self.result_dir(), "turns.jsonl"))
        for label in ("SKILL_TEST_API_KEY", "SERVICE_AUTH_TOKEN", "credentials"):
            self.assertIn("<redacted:%s>" % label, turns)
        self.assertIn("Alexandra", turns)  # a name is not a secret: GIT_AUTHOR is not an AUTH segment
        self.assertNotIn(key, proc.stdout + proc.stderr)

    def test_the_default_allowlist_runs_only_the_skill_s_own_python(self):
        """No `python3 *`, `env`, `printenv` or `find`, while the skill's own commands pass: its linter, the uuid
        one-liner and the read-only commands. Each python3 rule is anchored to the bench's copy, so no code can come
        before the path; rules are read literal up to the trailing `*`."""
        skill_dir = "/bench/project/" + COPY
        rules = run_skill.default_allowed_tools(skill_dir, NAME)
        for gone in ("Bash(python3 *)", "Bash(env)", "Bash(env *)", "printenv", "find", "{OWN}", "Bash(python3 *.",
                     "Bash(python3 -c 'import collections", "Bash(claude"):
            self.assertNotIn(gone, rules)
        patterns = rule_patterns(rules)
        own = ['python3 "%s/scripts/lint_prompt.py" "/bench/project/prompts/t/master-prompt.md" --decisions '
               '"/bench/project/prompts/t/decisions.md"' % skill_dir,
               "python3 %s/scripts/lint_prompt.py prompts/t/master-prompt.md" % COPY,
               "python3 -c 'import uuid; print(uuid.uuid4())'", "date -u", "ls prompts", "wc -w prompts/t/master-prompt.md",
               "grep -n Seats prompts/t/master-prompt.md", "head -5 x", "cat x"]
        for command in own:
            self.assertTrue(any(p.match(command) for p in patterns), command)
        for command in ("python3 /tmp/x.py", "python3 -c 'import os; os.system(\"id\")'", "env python3 x.py",
                        "env", "printenv", "printenv CLAUDE_CODE_OAUTH_TOKEN", "printenv ANTHROPIC_API_KEY",
                        "claude --version", "python3 -c 'import collections,glob,json,os;print(1)'",
                        "find . -exec rm {} ;",
                        "python3 -c 'import os; os.system(\"id\")' %s/scripts/lint_prompt.py" % skill_dir,
                        "python3 /tmp/evil.py %s/scripts/lint_prompt.py" % skill_dir,
                        "python3 /tmp/other/%s/scripts/lint_prompt.py x" % COPY,
                        'python3 -c "exec(input())" %s/scripts/lint_prompt.py' % COPY):
            self.assertFalse(any(p.match(command) for p in patterns), command)
        # the commands the skill's own text runs are the ones the rules admit
        skill_md = read(os.path.join(SKILL, "SKILL.md"))
        self.assertEqual(run_skill.SKILL_SCRIPTS, ("scripts/lint_prompt.py",))
        self.assertIn("python3 -c 'import uuid; print(uuid.uuid4())'", skill_md)
        self.assertIn('python3 "<this skill\'s directory>/%s"' % run_skill.SKILL_SCRIPTS[0], skill_md)
        for script in run_skill.SKILL_SCRIPTS:
            self.assertTrue(os.path.isfile(os.path.join(SKILL, *script.split("/"))), script)

    def test_the_docstring_names_each_rule_that_can_read_any_file(self):
        """A `Bash(<command> *)` rule for a command that prints what a file holds reads any file this account can.
        The module's docstring names each one the default allowlist keeps, and where the evals belong."""
        rules = run_skill.default_allowed_tools("/bench/project/" + COPY, NAME)
        readers = [name for name in ("cat", "grep", "head", "tail", "less", "more", "sed", "awk", "od", "xxd",
                                     "strings", "base64") if "Bash(%s *)" % name in rules]
        self.assertTrue(readers)
        doc = " ".join(run_skill.__doc__.split())
        named = re.search(r"It does keep (.*?) with any argument, which can read any file this account can", doc)
        self.assertIsNotNone(named, "the docstring says which rules can read any file")
        self.assertEqual(sorted(re.findall(r"`(\w+)`", named.group(1))), sorted(readers))
        self.assertIn("run the evals on a disposable machine", doc)

    def test_url_credentials_never_reach_the_copied_files_whatever_the_variable(self):
        """A URL's `user:password@` in HTTPS_PROXY or DATABASE_URL, or a token as a URL's user, is never copied."""
        # built at run time, and fake by name, so no file holds anything shaped like a real credential or URL with one
        proxy_pw, db_pw, user_token = "fake-proxy-" + "pw4411", "fake-db-" + "pw9922", "fake_" + "user_token_0123456789"
        proxy = "http://" + "proxyuser" + ":" + proxy_pw + "@proxy.example:3128"
        database = "postgres://" + "admin" + ":" + db_pw + "@db.example:5432/app"
        origin = "https://" + user_token + "@" + "github.com/org/repo.git"
        dump = ("HTTPS_PROXY=%s\nDATABASE_URL=%s\norigin %s\n"
                "see https://www.npmjs.com/package/@scope/name" % (proxy, database, origin))
        spec = dict(DELIVER, result="Environment read:\n" + dump + "\nDelivered.",
                    records=[{"tool_use": {"name": "Bash", "input": {"command": "env", "output": dump}}}])
        spec["write"] = dict(DELIVER["write"], **{"prompts/slug-fix/notes.md": dump})
        proc = self.run_harness([spec], env={"HTTPS_PROXY": proxy})
        self.assertIn(proc.returncode, (0, 3), proc.stdout + proc.stderr)
        seen = []
        for folder, _, files in os.walk(self.result_dir()):
            for name in files:
                text = read(os.path.join(folder, name))
                seen.append(name)
                for secret in (proxy_pw, db_pw, user_token, "proxyuser:"):
                    self.assertNotIn(secret, text, name)
        self.assertIn("notes.md", seen)
        turns = read(os.path.join(self.result_dir(), "turns.jsonl"))
        self.assertIn("http://" + run_skill.URL_REDACTED + "proxy.example:3128", turns)
        self.assertIn("postgres://" + run_skill.URL_REDACTED + "db.example:5432/app", turns)
        self.assertIn("https://www.npmjs.com/package/@scope/name", turns)  # an @ in a path is not a credential
        self.assertEqual(run_skill.scrub_bytes(b"\xff https://" + b"u:" + db_pw.encode() + b"@h/x"),
                         b"\xff https://" + run_skill.URL_REDACTED.encode("ascii") + b"h/x")

    def test_the_account_email_never_reaches_the_copied_files(self):
        """A headless transcript carries the account's address in a session_context attachment (userEmail, then again
        in `rendered`), main and subagent alike. Every address such an attachment names becomes <user-email> in every
        file the harness writes or copies, the produced prompt's copy included; any other address is kept."""
        # built at run time, on reserved names (RFC 2606, RFC 6761), so no file holds an address shaped like a real one
        address, other = "account.holder" + "@" + "mail.example", "bench" + "@" + "example.invalid"
        seat = {"agent-a1": {"meta": SEAT, "models": [MODEL]}}
        first = dict(ASK, user_email=address, records=[{"text": "Noted: the owner is %s." % address}], subagents=seat)
        last = dict(DELIVER, user_email=address, result="Delivered; %s is named as the owner." % address)
        last["write"] = dict(DELIVER["write"], **{"prompts/slug-fix/notes.md": "owner %s\nOWNER %s\nfixture %s\n" % (
            address, address.upper(), other)})
        proc = self.run_harness([first, last], person=[{"result": "Write to %s." % address, "user_email": address}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn(address, proc.stdout + proc.stderr)
        seen = {}
        for folder, _, files in os.walk(self.result_dir()):
            for name in files:
                path = os.path.join(folder, name)
                text = read(path)
                self.assertNotIn(address.lower(), text.lower(), path)
                seen[os.path.relpath(path, self.result_dir()).replace(os.sep, "/")] = text
        main = [name for name in seen if name.startswith("transcripts/") and name.count("/") == 1]
        self.assertEqual(len(main), 1)
        for name in (main[0], "transcripts/subagents/agent-a1.jsonl", "turns.jsonl", "commands.txt",
                     "prompt/slug-fix/notes.md"):
            self.assertIn("<user-email>", seen[name], name)
        self.assertEqual(seen["prompt/slug-fix/notes.md"], "owner <user-email>\nOWNER <user-email>\nfixture %s\n" % other)
        context = [json.loads(line) for line in seen[main[0]].splitlines() if '"session_context"' in line]
        self.assertEqual(len(context), 2)  # one per call; each record still parses
        self.assertIn("<user-email>", context[0]["attachment"]["context"]["userEmail"])
        # the person's calls are transcripts of the run too: an address only theirs names is redacted as well
        self.reset()
        proc = self.run_harness([ASK, DELIVER], person=[{"result": "Write to %s." % address, "user_email": address}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for name in ("turns.jsonl", "commands.txt"):
            text = read(os.path.join(self.result_dir(), name))
            self.assertNotIn(address, text, name)
            self.assertIn("Write to <user-email>.", text, name)

    def test_account_email_forms(self):
        """The address is taken from the session_context attachment alone, and redacted as the secret values are:
        plain and JSON-escaped, in any case, and byte for byte in a binary file."""
        address, other = "account.hölder" + "@" + "mail.example", "someone" + "@" + "mail.example"
        context = {"type": "attachment", "attachment": {"type": "session_context", "context": {
            "userEmail": "The user's email address is %s. Use it only to identify the user." % address}}}
        records = [context, {"type": "attachment", "attachment": {"type": "file", "content": other}},
                   {"type": "user", "message": {"role": "user", "content": "userEmail: " + other}}]
        emails = run_skill.AccountEmails()
        self.assertEqual(run_skill.AccountEmails().text(address), address)  # nothing noted, nothing changed
        self.assertEqual(emails.note(records), {address})
        self.assertEqual(emails.note(records), set())  # already noted
        escaped = json.dumps(address)[1:-1]
        self.assertNotEqual(escaped, address)
        self.assertEqual(emails.text("a %s b %s c %s d %s" % (address, escaped, address.upper(), other)),
                         "a <user-email> b <user-email> c <user-email> d %s" % other)
        self.assertEqual(emails.data(b"\xff " + address.encode("utf-8") + b" " + other.encode("ascii")),
                         b"\xff <user-email> " + other.encode("ascii"))

    def test_a_secret_holding_the_account_address_is_redacted_whole(self):
        """The secret values are replaced first, then the address, so a secret holding the address (`email:token`, a
        common basic-auth form, printed by the allowed `env`) still matches whole and its token is never copied."""
        # built at run time, and fake by name, so no file holds anything shaped like a real credential
        address = "account.holder" + "@" + "mail.example"
        basic = "-".join(("fake", "basic", "token", "0123456789"))
        dump = "SERVICE_AUTH=%s:%s\nOTHER=1" % (address, basic)
        spec = dict(DELIVER, user_email=address, result="Environment read:\n" + dump + "\nDelivered.",
                    records=[{"tool_use": {"name": "Bash", "input": {"command": "env", "output": dump}}}])
        spec["write"] = dict(DELIVER["write"], **{"prompts/slug-fix/notes.md": dump})
        proc = self.run_harness([spec], env={"SERVICE_AUTH": "%s:%s" % (address, basic)})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        seen = {}
        for folder, _, files in os.walk(self.result_dir()):
            for name in files:
                path = os.path.join(folder, name)
                text = seen[os.path.relpath(path, self.result_dir()).replace(os.sep, "/")] = read(path)
                for part in (basic, basic[:10], basic[-10:], address):
                    self.assertNotIn(part, text, path)
        main = [name for name in seen if name.startswith("transcripts/") and name.count("/") == 1][0]
        for name in (main, "turns.jsonl", "prompt/slug-fix/notes.md"):
            self.assertIn("SERVICE_AUTH=<redacted:SERVICE_AUTH>", seen[name], name)

    def test_an_address_known_only_from_the_environment_is_redacted_from_the_first_call(self):
        """The address is also seeded from CLAUDE_CODE_USER_EMAIL in the harness's own environment, used only as a
        pattern to redact, never printed: a line of the append-only commands.txt or turns.jsonl written before any
        transcript names it (the opening turn is written before the first call) never holds it."""
        address = "account.holder" + "@" + "mail.example"
        task = self.task(opening="prepare the prompt so another session fixes slugger; the owner is %s" % address)
        proc = self.run_harness([dict(DELIVER, result="Delivered; %s is named as the owner." % address)], task=task,
                                env={"CLAUDE_CODE_USER_EMAIL": address})  # and no transcript names it
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn(address, proc.stdout + proc.stderr)
        for folder, _, files in os.walk(self.result_dir()):
            for name in files:
                self.assertNotIn(address, read(os.path.join(folder, name)), name)
        turns = self.turns()
        self.assertEqual(turns[0]["text"], "prepare the prompt so another session fixes slugger; the owner is <user-email>")
        self.assertEqual(turns[1]["text"], "Delivered; <user-email> is named as the owner.")
        commands = read(os.path.join(self.result_dir(), "commands.txt"))
        self.assertIn("the owner is <user-email>", commands.split("skill call 1:")[1].split("\n\n")[0])

    def test_the_url_encoded_address_is_redacted(self):
        """The address in a URL's query (`account.holder%40mail.example`) is redacted too, as text and as bytes."""
        address = "account.holder" + "@" + "mail.example"
        emails = run_skill.AccountEmails()
        emails.note([{"type": "attachment", "attachment": {"type": "session_context", "context": {"userEmail": address}}}])
        encoded = address.replace("@", "%40")
        self.assertEqual(emails.text("https://x.example/?to=%s&a=1" % encoded), "https://x.example/?to=<user-email>&a=1")
        self.assertEqual(emails.data(b"\xff to=" + encoded.upper().encode("ascii")), b"\xff to=<user-email>")

    def test_a_bench_path_that_would_break_the_default_rules_is_refused(self):
        bench = os.path.join(self.tmp, "bench (copy)")
        proc = self.run_harness([DELIVER], bench=bench)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("pass --allowed-tools", proc.stderr)
        self.assertEqual(self.calls(), [])
        proc = self.run_harness([DELIVER], bench=bench, args=["--allowed-tools", "Bash(git status)"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_outputs_carry_home_never_the_home_path(self):
        bench = os.path.join(self.home, "bench")
        spec = dict(DELIVER, result="Delivered at {CWD}/prompts/slug-fix/master-prompt.md.")
        proc = self.run_harness([spec], bench=bench)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for folder, _, files in os.walk(self.result_dir()):
            for name in files:
                text = read(os.path.join(folder, name))
                self.assertNotIn(self.home, text, name)
        self.assertIn("$HOME/bench/project/prompts", read(os.path.join(self.result_dir(), "turns.jsonl")))


if __name__ == "__main__":
    unittest.main()
