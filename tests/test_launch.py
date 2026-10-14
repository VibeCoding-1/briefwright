"""Tests for the launch blocks and the allowlists of the harness guides.

The Claude Code guide's unattended launch block is filled and run under every shell found here (bash, sh, zsh) with a
stand-in CLI (fixtures/fake_claude.py) first on PATH: no real CLI call is made. Each case checks one property the
block promises: the run folder is created, the prompt reaches the CLI on stdin, the model flag appears only for a model
the person named and no subagent-model variable is set, a `- [!]` line stops the loop, open `- [ ]` lines resume it at
most three times with a message that approves nothing, no variable leaks out of the subshell, and both command forms
reach a folder with a space or one given as `$HOME/...`. The headless-seat line runs in two calls; the run's own
allowlist covers every command the blocks tell the executor to run, and no command the run executes holds a variable
the shell expands. The cloud block says that a permissions file committed for a run outlives it. The Codex guide's
unattended block is checked for shell syntax and run the same way with a stand-in `codex`. On quick, which keeps no
ledger, every guide's unattended block drops its resume loop: one call, and no line about the loop.
"""
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

import support
from support import FAKE_CLAUDE, clean_env, read, write, write_json

import lint_prompt as lp

SKILL = support.SKILL
CLAUDE_GUIDE = os.path.join(SKILL, "references", "harness-claude-code.md")
TEMPLATE = os.path.join(SKILL, "templates", "decisions.md")
REVIEW = os.path.join(SKILL, "references", "review.md")
GUIDES = {h: lp.load_guide(SKILL, h) for h in ("claude-code", "codex", "generic")}
MODEL = "example-model-1"
SESSION = "0b7e6c1a-3f52-4d8e-9a61-5c2f0e4b7d93"
TASK = "api-router-migration"
RUN_DIR = "prompts/%s/run" % TASK
ALLOWED = "Bash(date *),Bash(mkdir *),Bash(pwd),Bash(git commit *)"
SHELLS = [shell for shell in ("bash", "sh", "zsh") if shutil.which(shell)]
FRAMING = {"effort": "high", "launch": "headless", "model": MODEL, "size": "standard"}   # quick drops the loop
AFTER = 'printf "AFTER|%s|%s|%s\\n" "${CLAUDE_CODE_EFFORT_LEVEL-unset}" "${open-unset}" "${n-unset}"'


def block(harness, block_id, framing=None):
    return lp.expand_fragments(GUIDES[harness].blocks[block_id], dict(FRAMING, **(framing or {})))[0]


def subagent_keys(env):
    """The logged environment's subagent settings: a launch sets none."""
    return [key for key in env if "SUBAGENT" in key]


def section4():
    """The Claude Code guide's §4 prose, where the allowlist is written."""
    return GUIDES["claude-code"].section(4)


def attended_lines(framing=None):
    """The two command lines of the attended block (the `cd` line and the CLI line), dedented."""
    return [line.strip() for line in block("claude-code", "launch-attended", framing).split("\n") if line.startswith("    ")]


def launch_block(harness="claude-code", framing=None):
    """The indented command lines of a guide's unattended block, dedented."""
    return "\n".join(line[4:] for line in block(harness, "launch-headless", framing).split("\n") if line.startswith("    "))


def section4_allowlist():
    """The whole list §4 builds for a run with seats that commits, runs headless seats and runs pytest, filled, each
    rule as §4 writes it (before any quoting for the launch)."""
    text = section4()
    own = re.search(r"`(Bash\(date \*\)[^`]*)`", text)
    git = re.search(r"When the run commits, `(Bash\(git [^`]+)`", text)
    headless = re.search(r"With headless seats, `(Bash\(env -u [^`]+)` and `(Bash\(python3 -c [^`]+)`", text)
    bar = re.search(r"`(Bash\(python3 -m pytest \*\))`", text)
    assert own and git and headless and bar, "the guide's §4 names its rules"
    rules = ",".join((own.group(1), git.group(1), headless.group(1), headless.group(2), bar.group(1)))
    assert not re.search(r"\{[A-Z_]+[}:]", rules), rules
    return rules


def launch_quoted(allowed):
    """The list as §4 says to write it inside the launch's single quotes."""
    rule = re.search(r"write each `'` in it as `([^`]+)`", section4())
    return allowed.replace("'", rule.group(1))


def headless_text(framing=None):
    return block("claude-code", "headless-line", framing)


def headless_filled(values, brief_allowlist="", framing=None):
    """The headless line's seat command with its slots filled and its run-time placeholders filled by a lead: the
    fresh id, a turn limit, the seat id and the seat's allowlist quoted as the line says."""
    text = headless_text(framing)
    command = re.search(r"`([^`]*env -u CLAUDE_CODE_SESSION_ID [^`]+)`", text).group(1)
    escape = re.search(r"each `'` of the seat's allowlist is written `([^`]+)`", text)
    filled = re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)], command)
    for placeholder, value in (("<uuid>", SESSION), ("<n>", "12"), ("<seat-id>", "critic-1"),
                               ("<seat-model>", "example-model-2"),
                               ("<the seat's allowlist>", brief_allowlist.replace("'", escape.group(1)))):
        filled = filled.replace(placeholder, value)
    return filled


def headless_calls(values, allowlist="", framing=None):
    """The headless line's calls, in order, filled as a lead fills them: each backtick span of its first paragraph
    that is a command (`mkdir -p …`, then `cd … && env -u … claude -p …`)."""
    first = headless_text(framing).split("\n\n")[0]
    spans = [span for span in re.findall(r"`([^`]+)`", first) if span.startswith(("mkdir ", "cd ", "env "))]
    out = []
    for span in spans:
        if "env -u CLAUDE_CODE_SESSION_ID" in span:
            out.append(headless_filled(values, allowlist, framing))
        else:
            out.append(re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)], span).replace("<seat-id>", "critic-1"))
    return out


def and_parts(command):
    """The parts of a `&&` list, split outside quotes, as the CLI checks a compound command part by part."""
    parts, current, quote, i = [], "", "", 0
    while i < len(command):
        char = command[i]
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif command.startswith("&&", i):
            parts.append(current.strip())
            current, i = "", i + 2
            continue
        current += char
        i += 1
    return parts + [current.strip()]


def fill(text, folder, extra_flags="", allowed=ALLOWED, bench_mkdir="", add_dir=""):
    values = {"FOLDER": folder, "RUN_DIR": RUN_DIR, "TASK_ID": TASK, "EFFORT": "high", "MODEL_ID": MODEL,
              "SESSION_ID": SESSION, "PERMISSION_MODE": "acceptEdits", "ALLOWED_TOOLS": allowed,
              "EXTRA_FLAGS": extra_flags, "BENCH_MKDIR": bench_mkdir, "ADD_DIR": add_dir}
    filled = re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)], text)
    assert not re.search(r"\{[A-Z_]+\}", filled), filled
    return filled


def bash_rules(text):
    """The `Bash(<pattern>)` rules in a text; a pattern may nest parentheses two deep (the uuid rule)."""
    return re.findall(r"Bash\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)", text)


def rules_to_regex(rules):
    """Permission rules `Bash(<pattern>)` read as the CLI documents them: literal but for each `*`, which matches any
    text; a trailing ` *` that is the rule's only `*` also matches the bare command."""
    out = []
    for rule in bash_rules(rules):
        pattern = rule[5:-1]
        if pattern.endswith(" *") and pattern.count("*") == 1:
            out.append(re.compile("^" + re.escape(pattern[:-2]) + "(?: .*)?$"))
        else:
            out.append(re.compile("^" + ".*".join(re.escape(part) for part in pattern.split("*")) + "$"))
    return out


def cli_split(value):
    """An allowlist split into rules as the CLI's own parser does it: a `(` opens, any `)` closes, with no count of
    nesting, and a comma or a space outside splits; observed in the CLI's parser, not documented."""
    rules, current, inside = [], "", False
    for char in value:
        if char in "()":
            inside = char == "("
        elif char in ", " and not inside:
            if current.strip():
                rules.append(current.strip())
            current = ""
            continue
        current += char
    if current.strip():
        rules.append(current.strip())
    return rules


def segments(command):
    """The parts of a pipeline, split on `|` outside quotes, with redirections to /dev/null dropped."""
    parts, current, quote = [], "", ""
    for char in command:
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "|":
            parts.append(current)
            current = ""
            continue
        current += char
    parts.append(current)
    return [re.sub(r"\s*2>/dev/null", "", part).strip() for part in parts]


def need_a_shell(case):
    """The shell tests loop over SHELLS: with none found they would assert nothing, so they fail instead."""
    if not SHELLS:
        case.fail("no POSIX shell (bash, sh or zsh) on PATH: the launch blocks cannot be run")


def stand_in(folder):
    """A `claude` on PATH that runs the fake CLI."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "claude")
    write(path, '#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, FAKE_CLAUDE))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class LaunchBlock(unittest.TestCase):
    def setUp(self):
        need_a_shell(self)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.folder = os.path.join(self.tmp, "project with space")
        self.elsewhere = os.path.join(self.tmp, "elsewhere")
        os.makedirs(self.elsewhere)
        self.prompt = "# Move the endpoints\n\nThis prompt is written for `%s`.\n" % MODEL + "x" * 2000 + "\n"
        write(os.path.join(self.folder, "prompts", TASK, "master-prompt.md"), self.prompt)
        self.bin = os.path.join(self.tmp, "bin")
        stand_in(self.bin)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def run_block(self, shell, specs, extra_flags="", folder=None, allowed=ALLOWED, bench_mkdir="", text=None,
                  framing=None):
        """Run the filled block under `shell` from another folder; return (process, calls)."""
        log = os.path.join(self.tmp, "calls-%s.jsonl" % shell)
        if os.path.exists(log):
            os.remove(log)
        script = os.path.join(self.tmp, "script.json")
        write_json(script, {"skill": specs})
        text = text or fill(launch_block(framing=framing), folder or self.folder, extra_flags, allowed, bench_mkdir)
        env = self.env(FAKE_CLAUDE_SCRIPT=script, FAKE_CLAUDE_LOG=log)
        proc = subprocess.run([shell, "-c", text + "\n" + AFTER + "\n"], cwd=self.elsewhere, env=env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=120)
        calls = []
        if os.path.exists(log):
            with open(log, encoding="utf-8") as handle:
                calls = [json.loads(line) for line in handle if line.strip()]
        return proc, calls

    def env(self, **extra):
        return clean_env(HOME=self.home, PATH=self.bin + os.pathsep + os.environ.get("PATH", ""), **extra)

    def ledger(self, text):
        return {"write": {RUN_DIR + "/ledger.md": "# Ledger\n\n## Tasks\n\n" + text}}

    def assert_no_leak(self, proc):
        after = [line for line in proc.stdout.split("\n") if line.startswith("AFTER|")]
        self.assertEqual(after, ["AFTER|unset|unset|unset"], proc.stdout + proc.stderr)

    def test_the_block_fills_every_slot_and_keeps_bang_inside_single_quotes(self):
        text = launch_block()
        self.assertTrue(text.startswith('{BENCH_MKDIR}cd "{FOLDER}" && mkdir -p {RUN_DIR} && ('), text)
        self.assertEqual(attended_lines()[0], '{BENCH_MKDIR}cd "{FOLDER}"')
        self.assertTrue(text.rstrip().endswith("done )"), text)
        for framing in ({"effort": "high"}, {"effort": "default"}, {"model": lp.MODEL_CHOOSE}):
            for line in launch_block(framing=framing).split("\n") + attended_lines(framing):
                outside = re.sub(r"'[^']*'", "", line)
                self.assertNotIn("!", outside, "a ! outside single quotes meets history expansion: " + line)
                self.assertNotIn("`", outside, "a backtick would run a command: " + line)

    def test_a_missing_run_folder_is_created_and_the_prompt_goes_in_on_stdin(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                shutil.rmtree(os.path.join(self.folder, RUN_DIR), True)
                proc, calls = self.run_block(shell, [{"result": "Done."}], extra_flags="--max-budget-usd 5 ")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(len(calls), 1, calls)
                first, argv = calls[0], calls[0]["argv"]
                self.assertEqual(first["stdin"], self.prompt)
                self.assertFalse(any(self.prompt.strip()[:40] in arg for arg in argv))
                self.assertEqual(argv[argv.index("--session-id") + 1], SESSION)
                self.assertNotIn("--resume", argv)
                self.assertEqual(argv[argv.index("--allowed-tools") + 1], ALLOWED)
                self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "5")
                self.assertEqual((argv[argv.index("--model") + 1], argv[argv.index("--effort") + 1]), (MODEL, "high"))
                self.assertEqual(os.path.realpath(first["cwd"]), os.path.realpath(self.folder))
                self.assertEqual(subagent_keys(first["env"]), [])
                self.assertIsNone(first["env"]["CLAUDE_CODE_EFFORT_LEVEL"])
                self.assertEqual(json.loads(read(os.path.join(self.folder, RUN_DIR, "launch-0.json")))["type"], "result")
                self.assert_no_leak(proc)

    def test_with_model_choose_no_model_flag_and_no_subagent_setting(self):
        text = fill(launch_block(framing={"model": lp.MODEL_CHOOSE}), self.folder)
        self.assertNotIn("--model", text)
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [self.ledger("- [ ] move the endpoints\n")], text=text)
                self.assertEqual((proc.returncode, len(calls)), (0, 4), proc.stderr)
                for call in calls:
                    self.assertNotIn("--model", call["argv"])
                    self.assertEqual(call["argv"][call["argv"].index("--effort") + 1], "high")
                    self.assertEqual(subagent_keys(call["env"]), [])
                self.assert_no_leak(proc)
        self.assertEqual(attended_lines({"model": lp.MODEL_CHOOSE, "effort": "default"})[1], "claude{ADD_DIR}")

    def test_with_the_default_effort_no_effort_is_set(self):
        text = fill(launch_block(framing={"effort": "default"}), self.folder)
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [{"result": "Done."}], text=text)
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
                self.assertNotIn("--effort", calls[0]["argv"])
                self.assertIsNone(calls[0]["env"]["CLAUDE_CODE_EFFORT_LEVEL"])

    def test_both_command_forms_reach_a_folder_with_a_space_or_given_as_home(self):
        home_folder = os.path.join(self.home, "work", "shop api")
        write(os.path.join(home_folder, "prompts", TASK, "master-prompt.md"), self.prompt)
        for value, real in ((self.folder, self.folder), ("$HOME/work/shop api", home_folder)):
            for shell in SHELLS:
                with self.subTest(folder=value.replace(self.tmp, "<tmp>"), shell=shell):
                    shutil.rmtree(os.path.join(real, RUN_DIR), True)
                    proc, calls = self.run_block(shell, [{"result": "Done."}], folder=value)
                    self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
                    self.assertEqual(os.path.realpath(calls[0]["cwd"]), os.path.realpath(real))
                    attended = subprocess.run([shell, "-c", fill(attended_lines()[0], value) + " && pwd"],
                                              cwd=self.elsewhere, env=self.env(), stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
                    self.assertEqual(attended.returncode, 0, attended.stderr)
                    self.assertEqual(os.path.realpath(attended.stdout.strip()), os.path.realpath(real))

    def test_a_tilde_folder_is_why_the_slot_never_starts_with_one(self):
        rule = next(line for line in read(TEMPLATE).split("\n") if "folder=" in line and "{FOLDER}" in line)
        self.assertIn("starts with /, $HOME or ${HOME}, never ~ (write $HOME for a ~ the person gave), and holds no "
                      "double quote, backtick, backslash, ! or other $", rule)
        write(os.path.join(self.home, "work", "shop api", "prompts", TASK, "master-prompt.md"), self.prompt)
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [{"result": "Done."}], folder="~/work/shop api")
                self.assertEqual(calls, [])
                self.assertIn("~/work/shop api", proc.stderr)   # the shell's cd error names the unexpanded path

    def test_the_whole_section_4_list_with_both_headless_rules_reaches_the_cli_byte_for_byte(self):
        allowed = section4_allowlist()
        self.assertIn(",Bash(python3 -c 'import uuid; print(uuid.uuid4())'),", allowed)
        self.assertEqual(len(bash_rules(allowed)), 11, allowed)
        self.assertEqual(cli_split(allowed), bash_rules(allowed))   # the CLI keeps every rule whole
        self.assertEqual(shlex.split("--allowed-tools '%s'" % launch_quoted(allowed)), ["--allowed-tools", allowed])
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [self.ledger("- [ ] move the endpoints\n")],
                                             allowed=launch_quoted(allowed))
                self.assertEqual((proc.returncode, len(calls)), (0, 4), proc.stderr)
                for call in calls:
                    received = call["argv"][call["argv"].index("--allowed-tools") + 1]
                    self.assertEqual(received, allowed)
                self.assert_no_leak(proc)
        self.assertEqual(launch_quoted("'"), "'\\''")
        self.assertIn("each `'` of an allowlist is written `'\\''`", read(REVIEW))

    def test_with_headless_seats_both_forms_make_the_bench_root_and_add_it_to_the_session(self):
        self.assertIn('`--add-dir "{BENCH_ROOT}"`', section4())
        root = os.path.join(self.tmp, "bench root")
        bench_mkdir, add_dir, extra = 'mkdir -p "%s" && ' % root, ' --add-dir "%s"' % root, '--add-dir "%s" ' % root
        self.assertIn('`{ADD_DIR}` (` --add-dir "{BENCH_ROOT}"`)', section4())
        for shell in SHELLS:
            with self.subTest(shell=shell, form="unattended"):
                shutil.rmtree(root, True)
                proc, calls = self.run_block(shell, [self.ledger("- [ ] move the endpoints\n")], extra_flags=extra,
                                             bench_mkdir=bench_mkdir)
                self.assertEqual((proc.returncode, len(calls)), (0, 4), proc.stderr)
                self.assertTrue(os.path.isdir(root))
                for call in calls:
                    argv = call["argv"]
                    self.assertEqual(argv[argv.index("--add-dir") + 1], root)
                    self.assertTrue(argv[argv.index("--add-dir") + 2].startswith("--"), argv)
            with self.subTest(shell=shell, form="attended"):
                shutil.rmtree(root, True)
                cd_line, cli_line = (fill(line, self.folder, bench_mkdir=bench_mkdir, add_dir=add_dir)
                                     for line in attended_lines())
                proc, calls = self.run_block(shell, [{"result": "ok"}], text=cd_line + "\n" + cli_line)
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
                self.assertTrue(os.path.isdir(root))
                argv = calls[0]["argv"]
                self.assertEqual(argv[argv.index("--add-dir") + 1:argv.index("--add-dir") + 4], [root, "--model", MODEL])

    def test_open_tasks_resume_at_most_three_times_with_a_message_that_approves_nothing(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [self.ledger("- [x] inventory\n- [ ] move the endpoints\n")])
                self.assertEqual((proc.returncode, len(calls)), (0, 4), proc.stderr)
                for n, call in enumerate(calls[1:], 1):
                    argv = call["argv"]
                    message = argv[argv.index("-p") + 1]
                    self.assertTrue(message.startswith("Automatic continuation from the launch loop, not the person: "
                                                       "it approves nothing you stopped to ask about."), message)
                    self.assertIn("- [ ] move the endpoints", message)
                    self.assertNotIn("inventory", message)
                    self.assertEqual(argv[argv.index("--resume") + 1], SESSION)
                    self.assertNotIn("--session-id", argv)
                    self.assertIsNone(call["stdin"])
                    self.assertTrue(os.path.isfile(os.path.join(self.folder, RUN_DIR, "launch-%d.json" % n)))
                self.assert_no_leak(proc)

    def test_a_blocked_task_stops_the_loop(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [self.ledger(
                    "- [ ] move the endpoints\n- [!] rotate the key — blocked: needs the production credential\n")])
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
                self.assert_no_leak(proc)

    def test_a_task_blocked_after_a_resume_stops_the_loop_and_done_tasks_end_it(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [self.ledger("- [ ] move the endpoints\n"),
                                                     self.ledger("- [ ] move the endpoints\n- [!] deploy — blocked: a push\n")])
                self.assertEqual(len(calls), 2)
                proc, calls = self.run_block(shell, [self.ledger("- [ ] move the endpoints\n"),
                                                     self.ledger("- [x] move the endpoints\n")])
                self.assertEqual(len(calls), 2)
                self.assert_no_leak(proc)


class HeadlessLine(unittest.TestCase):
    """A headless seat's brief goes in on stdin from its file, never as an argument the shell would run; each `'` of
    the seat's allowlist is written as the line says; the line runs from the lead's folder in two calls."""

    def setUp(self):
        need_a_shell(self)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.folder = os.path.join(self.tmp, "project with space")
        os.makedirs(self.folder)
        self.root = os.path.join(self.tmp, "bench root")
        os.makedirs(self.root)
        self.bench = os.path.join(self.root, "critic-1")
        self.bin = os.path.join(self.tmp, "bin")
        stand_in(self.bin)
        self.values = {"EFFORT": "high", "MODEL_ID": MODEL, "SEAT_BUDGET_USD": "3", "FOLDER": self.folder,
                       "RUN_DIR": RUN_DIR, "BENCH_ROOT": self.root}

    def test_the_seat_runs_in_its_bench_reads_its_brief_on_stdin_and_its_allowlist_survives_a_quote(self):
        ran = [os.path.join(self.tmp, "ran-backtick"), os.path.join(self.tmp, "ran-subst")]
        brief = ("# Critic brief\n\nThe span `touch %s` is text, and so is $(touch %s). Keep 'single', \"double\", "
                 "a back\\slash, $HOME and a bang! as they are.\n" % tuple(ran))
        write(os.path.join(self.folder, RUN_DIR, "briefs", "critic-1.md"), brief)
        for allowlist in ("Read,Grep,Bash(pytest *)",
                          "Read,Grep,Bash(python3 -c 'import uuid; print(uuid.uuid4())'),Bash(grep -E 'TODO|FIXME' *)"):
            commands = headless_calls(self.values, allowlist)
            for shell in SHELLS:
                with self.subTest(shell=shell, allowlist=allowlist):
                    log = os.path.join(self.tmp, "calls.jsonl")
                    for path in ran + [log]:
                        if os.path.exists(path):
                            os.remove(path)
                    shutil.rmtree(self.bench, True)
                    for command in commands:   # one shell per call, as the lead's shell tool runs them
                        proc = subprocess.run([shell, "-c", command], cwd=self.folder, stdin=subprocess.DEVNULL,
                                              env=clean_env(HOME=self.tmp, FAKE_CLAUDE_LOG=log,
                                                            PATH=self.bin + os.pathsep + os.environ.get("PATH", "")),
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                              timeout=60)
                        self.assertEqual(proc.returncode, 0, command + "\n" + proc.stderr)
                    self.assertEqual([path for path in ran if os.path.exists(path)], [], "the shell ran part of the brief")
                    with open(log, encoding="utf-8") as handle:
                        calls = [json.loads(line) for line in handle if line.strip()]
                    self.assertEqual(len(calls), 1, proc.stderr)
                    call, argv = calls[0], calls[0]["argv"]
                    self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.bench))
                    self.assertEqual(call["stdin"], brief)
                    self.assertEqual(argv[argv.index("--allowed-tools") + 1], allowlist)
                    self.assertEqual(argv[argv.index("--session-id") + 1], SESSION)
                    self.assertEqual((call["env"]["CLAUDE_CODE_SESSION_ID"], call["env"]["CLAUDE_CODE_EFFORT_LEVEL"]),
                                     (None, None))
                    self.assertEqual(subagent_keys(call["env"]), [])
                    self.assertEqual((argv[argv.index("--model") + 1], argv[argv.index("--effort") + 1]), (MODEL, "high"))

    def test_with_model_choose_the_lead_names_each_seat_s_model(self):
        framing = {"model": lp.MODEL_CHOOSE}
        self.assertIn("`<seat-model>` is the model the guideline above gives the seat's work", headless_text(framing))
        self.assertNotIn("<seat-model>", headless_text())
        write(os.path.join(self.folder, RUN_DIR, "briefs", "critic-1.md"), "# Critic brief\n")
        log = os.path.join(self.tmp, "calls.jsonl")
        for command in headless_calls(self.values, "Read", framing):
            proc = subprocess.run([SHELLS[0], "-c", command], cwd=self.folder, stdin=subprocess.DEVNULL,
                                  env=clean_env(HOME=self.tmp, FAKE_CLAUDE_LOG=log,
                                                PATH=self.bin + os.pathsep + os.environ.get("PATH", "")),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
            self.assertEqual(proc.returncode, 0, command + "\n" + proc.stderr)
        with open(log, encoding="utf-8") as handle:
            argv = json.loads(handle.readline())["argv"]
        self.assertEqual(argv[argv.index("--model") + 1], "example-model-2")

    def test_two_calls_whose_parts_are_what_the_allowlist_and_the_sandbox_see(self):
        """A `cd` and a write in one command need an explicit approval nobody gives in a headless run, so `mkdir` is a
        call of its own under the run's own `Bash(mkdir *)`; the second call is a `cd` into the bench and the seat under
        its literal rule, its brief redirected from inside the working folder."""
        calls = headless_calls(self.values, "Read")
        self.assertEqual(len(calls), 2, calls)
        own = rules_to_regex(re.search(r"`(Bash\(date \*\)[^`]*)`", section4()).group(1))
        self.assertEqual(and_parts(calls[0]), ['mkdir -p "%s"' % self.bench])
        self.assertTrue(any(rule.match(calls[0]) for rule in own), calls[0])
        cd, seat = and_parts(calls[1])
        self.assertEqual(cd, 'cd "%s"' % self.bench)
        for call in calls:
            parts = and_parts(call)
            self.assertFalse(any(p.startswith("cd ") for p in parts) and any(p.startswith("mkdir ") for p in parts), call)
        rule = re.search(r"With headless seats, `(Bash\(env -u [^`]+)`", section4()).group(1)
        self.assertTrue(rules_to_regex(rule)[0].match(seat), seat)
        redirect = re.search(r' < "([^"]+)"$', seat)
        self.assertTrue(redirect and redirect.group(1).startswith(self.folder + "/"), seat)


class OwnAllowlist(unittest.TestCase):
    """The allowlist every unattended launch starts with covers each command the guide's blocks and the template tell
    the executor to run, read part by part as the CLI reads a pipeline."""

    def own_rules(self):
        own = re.search(r"`(Bash\(date \*\)[^`]*)`", section4())
        self.assertIsNotNone(own, "the guide's §4 lists the run's own commands")
        return own.group(1)

    def test_the_run_s_own_commands_are_covered(self):
        """The template's clock, the headless line's bench and `pwd` are admitted by the run's own rules; no grep or
        sed is left to the CLI's read-only set."""
        self.assertEqual(bash_rules(self.own_rules()), ["Bash(date *)", "Bash(mkdir *)", "Bash(pwd)"])
        rules = rules_to_regex(self.own_rules())
        template = read(os.path.join(SKILL, "templates", "master-prompt.md"))
        commands = [span.replace("{RUN_DIR}", RUN_DIR).replace("{BENCH_ROOT}", "/srv/benches/api")
                    for text in (headless_text(), template) for span in re.findall(r"`([^`\n]+)`", text)
                    if span.startswith(("date -u", "mkdir "))]
        commands.append("pwd")
        self.assertGreaterEqual(len(commands), 3, commands)
        for command in commands:
            for part in segments(command):
                with self.subTest(part=part[:60]):
                    self.assertFalse(re.match(r"(grep|sed) ", part), part)
                    self.assertTrue(any(rule.match(part) for rule in rules), "not covered: %r" % part)

    def test_no_own_rule_prints_the_environment(self):
        rules = rules_to_regex(self.own_rules())
        for refused in ("env", "printenv", "printenv CLAUDE_CODE_OAUTH_TOKEN", "printenv ANTHROPIC_API_KEY",
                        "export -p", "sed -i 's/a/b/' ~/.profile", "env | grep TOKEN"):
            with self.subTest(refused=refused):
                self.assertFalse(any(rule.match(part) for rule in rules for part in segments(refused)
                                     if not part.startswith("grep ")), refused)
        for rule in bash_rules(self.own_rules()):
            self.assertFalse(lp.ENVIRONMENT_RULE_RE.fullmatch(lp.rule_command(rule)), rule)

    def test_a_run_that_commits_gets_its_git_subcommands_and_no_push(self):
        text = section4()
        git = re.search(r"When the run commits, `([^`]+)`", text)
        self.assertIsNotNone(git, "the guide's §4 names the rules a run that commits adds")
        self.assertIn("never `Bash(git *)`", text)
        rules = rules_to_regex(git.group(1))
        for command in ("git status", "git diff --stat", "git log --oneline -5", "git add src/router.py",
                        'git commit -m "close the inventory"'):
            self.assertTrue(any(rule.match(command) for rule in rules), command)
        for command in ("git push origin feature/run", "git -c alias.x='!id' x", "git -C . push origin main",
                        "git config core.hooksPath hooks", "git status; git push"):
            self.assertFalse(all(any(rule.match(part) for rule in rules) for part in re.split(r"\s*;\s*", command)),
                             command)
        push = re.search(r"a push only as `(Bash\(git push origin [^`]+\))`, where a decisions-log row records the "
                         r"person allowing it", text)
        self.assertIsNotNone(push)
        self.assertNotIn("*", push.group(1))

    def test_headless_seats_add_a_literal_seat_rule_and_the_uuid_rule(self):
        values = {"EFFORT": "high", "MODEL_ID": MODEL, "RUN_DIR": RUN_DIR, "SEAT_BUDGET_USD": "3",
                  "FOLDER": "/srv/projects/shop api", "BENCH_ROOT": "/srv/benches/api"}
        section = re.search(r"With headless seats, (`Bash\(env -u [^`]+`) and (`Bash\(python3 -c [^`]+`)", section4())
        self.assertIsNotNone(section)
        seat_rule, uuid_rule = (part.strip("`") for part in section.groups())
        self.assertTrue(seat_rule.endswith(" claude -p *)") and seat_rule.count("*") == 1, seat_rule)
        self.assertEqual(uuid_rule, "Bash(python3 -c 'import uuid; print(uuid.uuid4())')")
        seat, uuid = rules_to_regex(seat_rule)[0], rules_to_regex(uuid_rule)[0]
        for framing in (None, {"model": lp.MODEL_CHOOSE}, {"effort": "default"}):
            seat_command = and_parts(headless_filled(values, "Read,Bash(pytest *)", framing))[-1]
            self.assertTrue(seat.match(seat_command), seat_command)
        self.assertTrue(uuid.match(re.search(r"`(python3 -c 'import uuid[^`]+)`", headless_text()).group(1)))
        for refused in ("env -u CLAUDE_CODE_SESSION_ID rm -rf build", "env -u CLAUDE_CODE_SESSION_ID python3 x.py",
                        "env -u CLAUDE_CODE_SESSION_ID FOO=1 claude -p x", "python3 -c 'print(6*7)'"):
            with self.subTest(refused=refused):
                self.assertFalse(seat.match(refused) or uuid.match(refused))


class LiteralCommands(unittest.TestCase):
    """No command the run executes holds a variable the shell would expand, which a headless run refuses as
    uncheckable (the guide's §3)."""

    def test_no_command_the_run_executes_holds_a_variable_the_shell_expands(self):
        """Each code span with a space in the blocks the run executes, filled with the literal paths §3 asks for, in
        every variant; the bench root's default is literal too."""
        guide = GUIDES["claude-code"]
        self.assertTrue(guide.literal_commands())
        self.assertFalse(GUIDES["codex"].literal_commands() or GUIDES["generic"].literal_commands())
        default = re.search(r"by default `([^`]+)`", section4())
        self.assertEqual(default.group(1), "<the parent folder of {FOLDER}>/benches/<task-id>")
        self.assertNotIn("$HOME/benches", read(CLAUDE_GUIDE))
        values = {"MODEL_ID": MODEL, "EFFORT": "high", "RUN_DIR": RUN_DIR, "FOLDER": "/srv/projects/shop api",
                  "BENCH_ROOT": "/srv/projects/benches/" + TASK, "SEAT_BUDGET_USD": "3"}
        checked = 0
        for block_id in lp.SEATS_BLOCKS:
            for effort in ("high", "default"):
                for launch in ("headless", "cloud"):
                    for model in (MODEL, lp.MODEL_CHOOSE):
                        text = lp.expand_fragments(guide.blocks[block_id],
                                                   {"effort": effort, "launch": launch, "model": model})[0]
                        text = re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)], text)
                        for span in re.findall(r"`([^`\n]+)`", text):
                            if " " in span:
                                checked += 1
                                self.assertEqual(lp.shell_variables(span), [], (block_id, span))
        self.assertGreaterEqual(checked, 24)   # three commands in each of the headless line's eight variants


# A stand-in `codex` for the unattended loop: it logs each call (argv, stdin, folder) and plays one scripted step per
# call: a JSONL stream on stdout that opens with `thread.started` when the step names a thread, then a subagent call
# whose `sender_thread_id` and `receiver_thread_ids` the loop must not take for the id; and files to write.
FAKE_CODEX = r"""import json, os, sys
log, script = os.environ["FAKE_CODEX_LOG"], os.environ["FAKE_CODEX_SCRIPT"]
with open(log, "a+", encoding="utf-8") as handle:
    handle.seek(0)
    n = sum(1 for line in handle if line.strip())
    stdin = sys.stdin.read() if "-" in sys.argv[1:] else None
    handle.write(json.dumps({"argv": sys.argv[1:], "stdin": stdin, "cwd": os.getcwd()}) + "\n")
steps = json.load(open(script, encoding="utf-8"))
step = steps[min(n, len(steps) - 1)]
if step.get("thread"):
    print(json.dumps({"type": "thread.started", "thread_id": step["thread"]}, separators=(",", ":")))
print(json.dumps({"type": "item.completed", "item": {"type": "collab_tool_call", "sender_thread_id": "main-thread",
                                                     "receiver_thread_ids": ["seat-thread"]}}, separators=(",", ":")))
for path, text in step.get("write", {}).items():
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
"""


class StatedLimits(unittest.TestCase):
    """What an allowlist cannot bound is said in the block the person launches from, not left to be found."""

    def test_the_cloud_block_takes_a_committed_permissions_file_off_the_default_branch(self):
        self.assertIn("Also take any permissions file committed for the run, such as `.claude/settings.json`, off the "
                      "default branch: its allow rules apply to every later session on that repository.",
                      " ".join(GUIDES["claude-code"].blocks["launch-cloud"].split()))


class CodexLaunchLoop(unittest.TestCase):
    """The Codex guide's unattended block, filled and run under every shell found here with a stand-in `codex` first
    on PATH: the thread id comes from the first call's `thread.started` event, and each resume passes the first call's
    flags again (the model only where the person named one), before `resume`, by that id, at most three times."""

    THREAD = "019a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8"

    def setUp(self):
        need_a_shell(self)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.folder = os.path.join(self.tmp, "project with space")
        self.prompt = "# Port the parser\n\nThis prompt is written for `%s`.\n" % MODEL
        write(os.path.join(self.folder, "prompts", TASK, "master-prompt.md"), self.prompt)
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        fake = os.path.join(self.bin, "codex")
        write(fake, "#!/bin/sh\nexec \"%s\" \"%s\" \"$@\"\n" % (sys.executable, os.path.join(self.tmp, "fake_codex.py")))
        write(os.path.join(self.tmp, "fake_codex.py"), FAKE_CODEX)
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def run_loop(self, shell, steps, effort="high", timeout="", model=MODEL):
        log, script = os.path.join(self.tmp, "calls.jsonl"), os.path.join(self.tmp, "steps.json")
        for path in (log, os.path.join(self.folder, RUN_DIR, "ledger.md")):
            if os.path.exists(path):
                os.remove(path)
        write_json(script, steps)
        values = {"FOLDER": self.folder, "RUN_DIR": RUN_DIR, "TASK_ID": TASK, "MODEL_ID": MODEL, "EFFORT": effort,
                  "SANDBOX": "workspace-write", "TIMEOUT": timeout}
        text = re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)],
                      launch_block("codex", {"effort": effort, "launch": "headless", "model": model}))
        env = clean_env(PATH=self.bin + os.pathsep + os.environ.get("PATH", ""), FAKE_CODEX_LOG=log,
                        FAKE_CODEX_SCRIPT=script, HOME=self.tmp)
        proc = subprocess.run([shell, "-c", text], cwd=self.tmp, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
        calls = []
        if os.path.exists(log):
            with open(log, encoding="utf-8") as handle:
                calls = [json.loads(line) for line in handle if line.strip()]
        return proc, calls

    def ledger(self, text):
        return {RUN_DIR + "/ledger.md": "# Ledger\n\n## Tasks\n\n" + text}

    def test_the_loop_resumes_the_first_thread_by_its_id_with_model_effort_and_sandbox_first(self):
        timeouts = [""] + (["timeout 60 "] if shutil.which("timeout") else [])
        for shell in SHELLS:
            for timeout in timeouts:
                with self.subTest(shell=shell, timeout=timeout):
                    proc, calls = self.run_loop(shell, [{"thread": self.THREAD, "write": self.ledger("- [ ] port\n")},
                                                        {}], timeout=timeout)
                    self.assertEqual((proc.returncode, len(calls)), (0, 4), proc.stderr)
                    first = calls[0]
                    self.assertEqual(first["argv"], ["exec", "-m", MODEL, "-c", "model_reasoning_effort=high", "-s",
                                                     "workspace-write", "--json", "-o", RUN_DIR + "/last-0.md", "-"])
                    self.assertEqual(first["stdin"], self.prompt)
                    self.assertEqual(os.path.realpath(first["cwd"]), os.path.realpath(self.folder))
                    for n, call in enumerate(calls[1:], 1):
                        argv = call["argv"]
                        self.assertEqual(argv[:9], ["exec", "-m", MODEL, "-c", "model_reasoning_effort=high", "-s",
                                                    "workspace-write", "resume", self.THREAD], argv)
                        self.assertTrue(argv[9].startswith("Automatic continuation from the launch loop, not the "
                                                           "person: it approves nothing"), argv[9])
                        self.assertIn("- [ ] port", argv[9])
                        self.assertEqual(argv[10:], ["--json"])
                        self.assertNotIn("--last", argv)
                        self.assertIsNone(call["stdin"])
                        self.assertTrue(os.path.isfile(os.path.join(self.folder, RUN_DIR, "launch-%d.jsonl" % n)))

    def test_with_the_default_effort_no_effort_is_passed(self):
        proc, calls = self.run_loop(SHELLS[0], [{"thread": self.THREAD, "write": self.ledger("- [ ] port\n")},
                                                {"write": self.ledger("- [x] port\n")}], effort="default")
        self.assertEqual((proc.returncode, len(calls)), (0, 2), proc.stderr)
        self.assertEqual(calls[1]["argv"][:6], ["exec", "-m", MODEL, "-s", "workspace-write", "resume"])
        self.assertFalse(any("model_reasoning_effort" in arg for call in calls for arg in call["argv"]))

    def test_with_model_choose_no_model_is_passed(self):
        proc, calls = self.run_loop(SHELLS[0], [{"thread": self.THREAD, "write": self.ledger("- [ ] port\n")},
                                                {"write": self.ledger("- [x] port\n")}], model=lp.MODEL_CHOOSE)
        self.assertEqual((proc.returncode, len(calls)), (0, 2), proc.stderr)
        self.assertEqual(calls[0]["argv"][:4], ["exec", "-c", "model_reasoning_effort=high", "-s"])
        self.assertEqual(calls[1]["argv"][:6], ["exec", "-c", "model_reasoning_effort=high", "-s", "workspace-write",
                                                "resume"])
        self.assertFalse(any("-m" in call["argv"] for call in calls))

    def test_no_thread_id_a_blocked_task_or_no_open_task_stops_the_loop(self):
        for shell in SHELLS:
            with self.subTest(shell=shell, case="no id"):
                proc, calls = self.run_loop(shell, [{"write": self.ledger("- [ ] port\n")}])
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
            with self.subTest(shell=shell, case="blocked"):
                proc, calls = self.run_loop(shell, [{"thread": self.THREAD, "write": self.ledger(
                    "- [ ] port\n- [!] push — blocked: needs the person\n")}])
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
            with self.subTest(shell=shell, case="blocked after a resume"):
                proc, calls = self.run_loop(shell, [{"thread": self.THREAD, "write": self.ledger("- [ ] port\n")},
                                                    {"write": self.ledger("- [!] port — blocked: a question\n")}])
                self.assertEqual((proc.returncode, len(calls)), (0, 2), proc.stderr)
            with self.subTest(shell=shell, case="done"):
                proc, calls = self.run_loop(shell, [{"thread": self.THREAD, "write": self.ledger("- [x] port\n")}])
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)


class Codex(unittest.TestCase):
    def test_the_unattended_block_filled_is_valid_shell(self):
        if not shutil.which("sh"):
            self.fail("no sh on PATH")
        for effort, model in (("high", MODEL), ("default", MODEL), ("high", lp.MODEL_CHOOSE)):
            for timeout in ("timeout 3600 ", ""):
                with self.subTest(effort=effort, model=model, timeout=timeout):
                    text = launch_block("codex", {"effort": effort, "launch": "headless", "model": model})
                    values = {"FOLDER": "/srv/projects/shop api", "RUN_DIR": RUN_DIR, "TASK_ID": TASK, "MODEL_ID": MODEL,
                              "EFFORT": effort, "SANDBOX": "workspace-write", "TIMEOUT": timeout}
                    filled = re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)], text)
                    self.assertNotRegex(filled, r"\{[A-Z_]+[}:]")
                    proc = subprocess.run(["sh", "-n", "-c", filled], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          universal_newlines=True, timeout=60)
                    self.assertEqual(proc.returncode, 0, proc.stderr + filled)
                    self.assertIn("resume \"$tid\"", filled)
                    self.assertNotIn("--last", filled)


class QuickHasNoLoop(unittest.TestCase):
    """A quick run keeps no ledger, so its unattended launch is one call: the `{LOOP: …}` text goes on quick."""

    setUp, run_block, env = LaunchBlock.setUp, LaunchBlock.run_block, LaunchBlock.env
    ledger, assert_no_leak = LaunchBlock.ledger, LaunchBlock.assert_no_leak

    def test_every_guide_s_unattended_block_drops_the_loop_on_quick(self):
        for harness in ("claude-code", "codex", "generic"):
            with self.subTest(harness=harness):
                quick, standard = (block(harness, "launch-headless", {"size": size}) for size in ("quick", "standard"))
                for text, kept in ((quick, False), (standard, True)):
                    self.assertEqual("at most three times" in " ".join(text.split()), kept, text)
                    self.assertEqual("for n in 1 2 3" in text, kept and harness != "generic", text)
                self.assertNotRegex(quick, r"\{LOOP:")

    def test_the_quick_block_runs_one_call_however_the_ledger_reads(self):
        text = fill(launch_block(framing={"size": "quick"}), self.folder)
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self.run_block(shell, [self.ledger("- [ ] move the endpoints\n")], text=text)
                self.assertEqual((proc.returncode, len(calls)), (0, 1), proc.stderr)
                self.assertNotIn("--resume", calls[0]["argv"])
                self.assert_no_leak(proc)

    def test_the_quick_codex_block_is_valid_shell(self):
        values = {"FOLDER": "/srv/projects/shop api", "RUN_DIR": RUN_DIR, "TASK_ID": TASK, "MODEL_ID": MODEL,
                  "EFFORT": "high", "SANDBOX": "workspace-write", "TIMEOUT": ""}
        filled = re.sub(r"\{([A-Z_]+)\}", lambda m: values[m.group(1)], launch_block("codex", {"size": "quick"}))
        proc = subprocess.run(["sh", "-n", "-c", filled], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr + filled)
        self.assertNotIn("resume", filled)



if __name__ == "__main__":
    unittest.main()
