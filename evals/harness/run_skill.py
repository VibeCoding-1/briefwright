#!/usr/bin/env python3
"""run_skill.py: one headless run of one version of the skill in Claude Code, the one runner there is.

A bench holds the skill and the task's fixtures; the skill session runs with `claude -p`, and a
scripted person answers each turn from a hidden brief through `--resume`, until the prompt is
delivered or a stop fires. The produced prompt, the transcripts and the metrics are collected.
A runner for another harness provides the same three operations (evals/README.md).

Usage:
    python3 run_skill.py --skill <skill dir> --task <task.json> --bench <dir> --out <dir>
        --arm <label> --max-budget-usd X --model <model id> [--effort <level>] [--max-turns 80]
        [--max-person-turns N] [--person-prompt <file>] [--linter <lint_prompt.py>]
        [--allowed-tools <rules>] [--claude-bin claude] [--timeout-s 3600] [--dry-run]

The skill's name is its SKILL.md frontmatter `name`: the bench copy is `.claude/skills/<name>` and a
task with `"invoke": "slash"` opens with `/<name>`. Where the person states a model, a task's opening and
hidden brief hold the slot `{MODEL}`, filled with --model before the first call, so the prompt is written
for the model the run really uses. --model is also the model the skill session runs on; the skill's helper
seats choose theirs by the skill's guideline.

Exit: 0 delivered; 3 not delivered (max-turns, max-budget, max-person-turns); 4 a `claude` call errored or
timed out; 2 usage or refusal.

Refusals (exit 2): a bench inside a git repository or not empty; a missing or non-positive
--max-budget-usd; an output folder for this task and arm that is not empty; a malformed task; with the
default allowlist, a working folder whose path holds a character that would break its rules.

Every call runs from <bench>/<working_folder> (the person's from <bench>/person/) with
CLAUDE_CODE_SESSION_ID, CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, CLAUDE_EFFORT and CLAUDE_CODE_EFFORT_LEVEL
removed, then, with --effort, CLAUDE_CODE_EFFORT_LEVEL=<--effort> and `--effort` on each call (without it, no
effort is set). Each call gets --max-budget-usd equal to what the run has left. What the run has spent is
the sum of each call's own cost: a `--resume` call reports in total_cost_usd the session's cumulative
cost, so its own cost is that figure minus the session's previous one, or the figure itself when it
fell (the counter restarted: the budget is never undercounted); a first call and a person call (a fresh
session each) count their figure as reported. The prompt text is passed after `--`, so a reply
that starts with a dash is never read as an option. A --claude-bin ending in .py runs under this
Python (the tests' fake CLI).

The person is shown every main-chain assistant text the skill's call wrote, in order, read from the
session's transcript from where it ended before the call (no sidechain text, no tool result, no API
error or `<synthetic>` record); the call's `result` when the transcript cannot be read. The delivered test reads the `result`, the closing
message. Each person call runs in a session of its own (a fresh --session-id).

The produced prompt is the newest prompts/*/master-prompt.md under the working folder or, when there is
none there, under any folder up to three levels below it (.claude, .git and node_modules skipped); a
master-prompt.md the task's fixtures put in the bench counts once its content changes. Its prompts/
folder is collected and the prompt linted; metrics.json records its folder (prompt_dir), every
candidate and every modelUsage key of every call.

The skill folder is copied as it is, caches aside; the evals live outside it, so a hidden brief never
sits in the bench. Every text
the harness writes has the home directory replaced by $HOME, and every secret this process can see
replaced by <redacted:NAME>: the value (six characters or more) of each environment variable whose name
has a segment TOKEN, KEY, APIKEY, SECRET, PASSWORD, PASSWD, PASS, CREDENTIAL(S), AUTH, PAT or COOKIE (or one
ending in KEY, TOKEN, SECRET or PASSWORD), and the string values of the CLI's credentials file, since a
transcript that ran `env` or read that file is copied into an evidence tree that gets committed. The
user-information part of any URL (a user and password, or a token as the user, before the host's `@`) becomes
<redacted:url-credentials>, whatever variable or file it came from. Then every address that a
session_context attachment of any of the run's transcripts names as the user's email, or that
CLAUDE_CODE_USER_EMAIL holds in this process's environment, becomes <user-email>, in any case, plain,
JSON-escaped and URL-encoded (binary files byte for byte), since the CLI writes the account's address
there; after the secrets, so a secret that holds the address still matches whole.

The default allowlist runs python3 only for the skill's linter (scripts/lint_prompt.py), each rule anchored
to the bench's copy of the skill (its absolute path and its path from the working folder, unquoted and in
double quotes: a rule is literal up to its trailing `*`, so no code can come before the path), and for
the uuid one-liner. It holds no `env`, no `printenv` and no find. It does keep `cat`, `grep` and `head` with
any argument, which can read any file this account can, and the redaction above catches only the secrets
it names: run the evals on a disposable machine. The bench is taken as its canonical path (symlinks
resolved), the folder Claude Code runs in and shows, so the absolute rules match on a symlinked bench too.

Standard library only; runs on python3 3.9 or newer.
"""
import argparse
import datetime
import glob
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import uuid

# {OWN} becomes the skill's linter anchored to the bench's copy (own_rules below).
DEFAULT_ALLOWED_TOOLS = ("Skill,{OWN},Bash(python3 -c 'import uuid; print(uuid.uuid4())'),"
                         "Bash(ls *),Bash(wc *),Bash(date *),Bash(grep *),Bash(head *),Bash(cat *)")
SKILL_SCRIPTS = ("scripts/lint_prompt.py",)
# Nobody answers the skill's ask tool in a headless run; with it absent, the skill asks its rounds as text.
SKILL_DISALLOWED = ("AskUserQuestion",)
PERSON_DISALLOWED = ("Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch", "Agent", "Skill")
UNSET = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "CLAUDE_EFFORT", "CLAUDE_CODE_EFFORT_LEVEL")
SKILL_COPY_SKIP = ("__pycache__", ".git")   # never copied into the bench, nor any *.pyc
PACK_NOT_PACKS = ("README.md", "TEMPLATE.md")  # files in packs/ that are not packs
TASK_KEYS = ("id", "opening", "working_folder", "fixtures", "hidden_brief", "max_person_turns", "invoke")
MODEL_SLOT = "{MODEL}"   # the model the person states, in a task's opening and hidden brief: --model at run time
DEFAULT_PERSON_TURNS = 8
PROMPT_PATTERN = os.path.join("prompts", "*", "master-prompt.md")
PROMPT_DEPTH = 3                                   # how deep a folder holding prompts/ may sit
PROMPT_SKIP = (".claude", ".git", "node_modules")  # never searched for a prompt
HERE = os.path.dirname(os.path.abspath(__file__))

QUESTION_LINE = re.compile(r"^\s*\*\*Q\d+")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
TRAILING_MARKUP = " \t*_`)\"'”’"
FRAMING_QUESTION = re.compile(r"Where will the run execute", re.I)   # the harness question

HOME = os.path.expanduser("~")
URL_USERINFO = re.compile(r"(?<=://)[^\s/?#@\"'<>\\`]+@")   # `user:password@` in any URL
URL_USERINFO_BYTES = re.compile(URL_USERINFO.pattern.encode("ascii"))
URL_REDACTED = "<redacted:url-credentials>@"
_HOME_RE = re.compile(re.escape(HOME) + r"(?![A-Za-z0-9._-])") if len(HOME) > 1 else None
SECRET_SEGMENTS = {"TOKEN", "KEY", "SECRET", "PASSWORD", "PASSWD", "PASS", "CREDENTIAL", "CREDENTIALS", "AUTH", "PAT",
                   "COOKIE", "APIKEY"}
SECRET_SUFFIXES = ("KEY", "TOKEN", "SECRET", "PASSWORD")
SECRET_MIN_LENGTH = 6
EMAIL_ADDRESS = re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)+")
EMAIL_REDACTED = "<user-email>"


def secret_name(name):
    parts = [part for part in name.upper().split("_") if part]
    return any(part in SECRET_SEGMENTS or part.endswith(SECRET_SUFFIXES) for part in parts)


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for text in _strings(item):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in _strings(item):
                yield text


def find_secrets(environ):
    """{value: label} for the values to redact: secret-named variables and the CLI's credentials file."""
    found = {}
    for name, value in environ.items():
        if secret_name(name) and len(value) >= SECRET_MIN_LENGTH:
            found.setdefault(value, name)
    config = environ.get("CLAUDE_CONFIG_DIR") or os.path.join(environ.get("HOME") or HOME, ".claude")
    try:
        with open(os.path.join(config, ".credentials.json"), encoding="utf-8") as handle:
            for text in _strings(json.load(handle)):
                if len(text) >= 16:
                    found.setdefault(text, "credentials")
    except (OSError, ValueError):
        pass
    forms = {}
    for value, label in found.items():
        for form in (value, json.dumps(value)[1:-1]):
            forms.setdefault(form, label)
    return sorted(forms.items(), key=lambda item: -len(item[0]))


SECRETS = find_secrets(os.environ)


class Refusal(Exception):
    """A usage error or a refusal: exit 2."""


def scrub(text):
    for value, label in SECRETS:
        text = text.replace(value, "<redacted:%s>" % label)
    text = URL_USERINFO.sub(URL_REDACTED, text)
    return _HOME_RE.sub("$HOME", text) if _HOME_RE else text


def scrub_bytes(data):
    for value, label in SECRETS:
        data = data.replace(value.encode("utf-8"), ("<redacted:%s>" % label).encode("utf-8"))
    return URL_USERINFO_BYTES.sub(URL_REDACTED.encode("ascii"), data)


def _email_texts(value, named=False):
    """The strings held under a key that names an email (`userEmail`), at any depth of `value`."""
    if isinstance(value, str):
        if named:
            yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            for text in _email_texts(item, named or "email" in str(key).lower()):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in _email_texts(item, named):
                yield text


def session_emails(records):
    """The addresses a `session_context` attachment names as the user's email. The CLI
    writes one into each transcript, main and subagent: `attachment.context.userEmail`, a sentence holding
    the account's address, which the record repeats in `rendered`."""
    found = set()
    for record in records:
        attachment = record.get("attachment") if record.get("type") == "attachment" else None
        if isinstance(attachment, dict) and attachment.get("type") == "session_context":
            for text in _email_texts(attachment):
                found.update(EMAIL_ADDRESS.findall(text))
    return found


class AccountEmails(object):
    """The account's addresses, noted from the run's transcripts as they appear (and seeded from
    CLAUDE_CODE_USER_EMAIL), and redacted to <user-email> as the secret values are: plain,
    JSON-escaped and URL-encoded (`%40`), in any case, and byte for byte in a binary file. Any other address
    is kept."""

    def __init__(self):
        self.found = set()
        self.text_pattern = self.bytes_pattern = None

    def note(self, records):
        return self.add(session_emails(records))

    def add(self, addresses):
        new = set(addresses) - self.found
        if new:
            self.found |= new
            bases = {form for address in self.found for form in (address, address.replace("@", "%40"))}
            forms = sorted({form for base in bases for form in (base, json.dumps(base)[1:-1])},
                           key=lambda form: (-len(form), form))
            self.text_pattern = re.compile("|".join(re.escape(form) for form in forms), re.I)
            self.bytes_pattern = re.compile(b"|".join(re.escape(form.encode("utf-8")) for form in forms), re.I)
        return new

    def text(self, text):
        return self.text_pattern.sub(EMAIL_REDACTED, text) if self.text_pattern else text

    def data(self, data):
        return self.bytes_pattern.sub(EMAIL_REDACTED.encode("ascii"), data) if self.bytes_pattern else data


def skill_name(skill_dir):
    """The `name` of a skill's SKILL.md frontmatter, or None."""
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as handle:
            lines = handle.read().split("\n")
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].rstrip() != "---":
        return None
    for line in lines[1:]:
        if line.rstrip() == "---":
            break
        found = re.match(r"^name:\s*[\"']?([a-z0-9]+(?:-[a-z0-9]+)*)[\"']?\s*$", line)
        if found:
            return found.group(1)
    return None


def in_bench(name):
    """The skill copy's path from the working folder."""
    return ".claude/skills/%s" % name


def own_rules(skill_dir, name):
    """The allowlist rules for the skill's linter, anchored to the bench's copy at
    `skill_dir` (absolute) and at its path from the working folder, each unquoted and in double quotes,
    since SKILL.md writes `python3 "<this skill's directory>/scripts/..."`."""
    rules = []
    for script in SKILL_SCRIPTS:
        for base in (skill_dir, in_bench(name)):
            path = "%s/%s" % (base.replace(os.sep, "/"), script)
            rules += ["Bash(python3 %s *)" % path, 'Bash(python3 "%s" *)' % path]
    return ",".join(rules)


def default_allowed_tools(skill_dir, name):
    return DEFAULT_ALLOWED_TOOLS.replace("{OWN}", own_rules(skill_dir, name))


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


# ------------------------------------------------------------------ reading the skill's messages
def units(text, split_items=True):
    """Paragraphs outside fences (lines between blank lines); with split_items each list item apart."""
    out, current, fence = [], [], ""
    for line in text.split("\n"):
        opened = FENCE.match(line)
        if fence:
            if opened and opened.group(1)[0] == fence[0] and len(opened.group(1)) >= len(fence) and \
                    not line.strip().strip(fence[0]):
                fence = ""
            continue
        if opened:
            fence = opened.group(1)
            if current:
                out.append(current)
            current = []
            continue
        if not line.strip():
            if current:
                out.append(current)
            current = []
            continue
        if split_items and current and LIST_ITEM.match(line):
            out.append(current)
            current = []
        current.append(line)
    if current:
        out.append(current)
    return out


def unit_questions(unit):
    count = sum(1 for line in unit if QUESTION_LINE.match(line))
    if not count and " ".join(unit).rstrip(TRAILING_MARKUP).endswith("?"):
        count = 1
    return count


def asks(text):
    """The message asks something: a `**Qn` line, or a paragraph (or list item) ending with `?`."""
    return any(unit_questions(unit) for unit in units(text))


def questions_in(text):
    return sum(unit_questions(unit) for unit in units(text))


def is_framing_question(text):
    """The message asks the harness question (SKILL.md's "Where will the run execute")."""
    return any("?" in " ".join(unit) and FRAMING_QUESTION.search(" ".join(unit)) for unit in units(text, split_items=False))


# ------------------------------------------------------------------ task
def load_task(path):
    try:
        with open(path, encoding="utf-8") as handle:
            task = json.load(handle)
    except (OSError, ValueError) as error:
        raise Refusal("cannot read the task file: %s" % error)
    if not isinstance(task, dict):
        raise Refusal("the task file must hold a JSON object")
    base = os.path.dirname(os.path.abspath(path))
    extra = sorted(set(task) - set(TASK_KEYS))
    if extra:
        sys.stderr.write("run_skill: ignoring unknown task keys: %s\n" % ", ".join(extra))
    if not isinstance(task.get("id"), str) or not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", task["id"]):
        raise Refusal("task id must be kebab-case")
    if not isinstance(task.get("opening"), str) or not task["opening"].strip():
        raise Refusal("task opening must be a non-empty string")
    folder = task.get("working_folder")
    if not isinstance(folder, str) or not folder or os.path.isabs(folder) or ".." in folder.replace("\\", "/").split("/"):
        raise Refusal("working_folder must be a relative path inside the bench")
    folder = folder.strip("/")
    if folder == "person":
        raise Refusal("working_folder 'person' is the scripted person's folder")
    fixtures = task.get("fixtures", {})
    if not isinstance(fixtures, dict):
        raise Refusal("fixtures must map bench-relative destinations to sources")
    resolved = {}
    for dest, src in fixtures.items():
        norm = dest.replace("\\", "/")
        if os.path.isabs(dest) or ".." in norm.split("/") or not norm.startswith(folder + "/"):
            raise Refusal("fixture destination %r must be a bench-relative path inside %s/" % (dest, folder))
        source = os.path.normpath(os.path.join(base, src))
        if not os.path.isfile(source):
            raise Refusal("fixture source %r does not exist (paths are relative to the task file)" % src)
        resolved[norm] = source
    brief = task.get("hidden_brief")
    if not isinstance(brief, str) or not os.path.isfile(os.path.join(base, brief)):
        raise Refusal("hidden_brief must name a file beside the task")
    with open(os.path.join(base, brief), encoding="utf-8") as handle:
        brief_text = handle.read()
    turns = task.get("max_person_turns", DEFAULT_PERSON_TURNS)
    if not isinstance(turns, int) or isinstance(turns, bool) or turns < 0:
        raise Refusal("max_person_turns must be a non-negative integer")
    invoke = task.get("invoke", "auto")
    if invoke not in ("auto", "slash"):
        raise Refusal("invoke must be 'auto' or 'slash'")
    return {"id": task["id"], "opening": task["opening"], "working_folder": folder, "fixtures": resolved,
            "hidden_brief": brief_text, "max_person_turns": turns, "invoke": invoke}


def with_model(task, model):
    """The task with every {MODEL} in its opening and hidden brief replaced by `model` (--model)."""
    return dict(task, opening=task["opening"].replace(MODEL_SLOT, model),
                hidden_brief=task["hidden_brief"].replace(MODEL_SLOT, model))


def inside_git(path):
    probe = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(probe, ".git")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent


# ------------------------------------------------------------------ transcripts
def read_jsonl(path, offset=0, only=None):
    """The object records of a JSONL file from byte `offset` on; with `only`, the lines holding that text."""
    records = []
    try:
        with open(path, "rb") as handle:
            handle.seek(offset)
            for line in handle:
                if only is not None and only not in line:
                    continue
                try:
                    record = json.loads(line.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
    except OSError:
        pass
    return records


def main_chain_texts(records):
    """The text blocks of the main-chain assistant records, in order. A sidechain record, a tool result
    and a background seat's notification (user records) hold none of them; nor does an API error the
    CLI retried (`isApiErrorMessage`) or any record of the `<synthetic>` model, which are the CLI's, not
    the skill's."""
    for record in records:
        if record.get("type") != "assistant" or record.get("isSidechain") is True or record.get("isApiErrorMessage"):
            continue
        message = record.get("message")
        if isinstance(message, dict) and message.get("model") == "<synthetic>":
            continue
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str) \
                    and block["text"].strip():
                yield block["text"]


def tool_uses(records):
    for record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name"), block.get("input") if isinstance(block.get("input"), dict) else {}


def usage_keys(result):
    """The modelUsage keys of a call's result: every model the call billed, internal helpers included."""
    usage = (result or {}).get("modelUsage")
    return sorted(usage) if isinstance(usage, dict) else []


def user_texts(records):
    for record in records:
        if record.get("type") != "user":
            continue
        message = record.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            yield content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    yield block["text"]


# ------------------------------------------------------------------ the run
class Run(object):
    def __init__(self, args, task):
        self.args, self.task = args, task
        self.bench = os.path.realpath(args.bench)   # the canonical path Claude Code runs in, symlinks resolved
        self.work = os.path.join(self.bench, task["working_folder"])
        self.person_dir = os.path.join(self.bench, "person")
        self.dest = os.path.join(os.path.abspath(args.out), task["id"], args.arm)
        self.session = str(uuid.uuid4())
        self.spent = 0.0           # the sum of the calls' own costs
        self.session_reported = 0.0  # the skill session's last reported total_cost_usd (cumulative on --resume)
        self.emails = AccountEmails()
        # the account's address from this process's environment, before the first call, so nothing written
        # before a transcript names it can hold it; only ever a pattern to redact, never printed
        self.emails.add(EMAIL_ADDRESS.findall(os.environ.get("CLAUDE_CODE_USER_EMAIL") or ""))
        self.calls = []            # dicts: role, argv, rc, wall_s, result, cost (own), reported_cost
        self.turns = []
        self.skill_texts = []
        self.person_sessions = []  # the fresh --session-id of each person call
        self.skill_calls = self.person_calls = 0
        self.env = self.environment()
        self.fixture_hashes = {}   # bench-relative path: sha256 at setup
        self.name = skill_name(args.skill)
        self.allowed_tools = args.allowed_tools if args.allowed_tools is not None else \
            default_allowed_tools(os.path.join(self.work, *in_bench(self.name).split("/")), self.name)
        self.max_person_turns = args.max_person_turns if args.max_person_turns is not None else task["max_person_turns"]
        with open(args.person_prompt or os.path.join(HERE, "person.md"), encoding="utf-8") as handle:
            self.person_template = handle.read()

    # ---- environment and commands
    def environment(self):
        env = dict(os.environ)
        for name in UNSET:
            env.pop(name, None)
        if self.args.effort:
            env["CLAUDE_CODE_EFFORT_LEVEL"] = self.args.effort
        return env

    def env_prefix(self):
        parts = ["env"] + ["-u %s" % name for name in UNSET]
        if self.args.effort:
            parts.append("CLAUDE_CODE_EFFORT_LEVEL=%s" % self.args.effort)
        return " ".join(parts)

    def remaining(self):
        return self.args.max_budget_usd - self.spent

    def base(self):
        return [sys.executable, self.args.claude_bin] if self.args.claude_bin.endswith(".py") else [self.args.claude_bin]

    def common(self, max_turns):
        effort = ["--effort", self.args.effort] if self.args.effort else []
        return ["-p", "--model", self.args.model] + effort + ["--max-turns", str(max_turns), "--output-format", "json",
                                                              "--permission-mode", "acceptEdits", "--strict-mcp-config",
                                                              "--max-budget-usd", "%.6f" % self.remaining()]

    def skill_argv(self, prompt, first):
        session = ["--session-id", self.session] if first else ["--resume", self.session]
        return self.base() + self.common(self.args.max_turns) + session + \
            ["--allowed-tools", self.allowed_tools, "--disallowed-tools", ",".join(SKILL_DISALLOWED), "--", prompt]

    def person_argv(self, prompt, session):
        return self.base() + self.common(1) + ["--session-id", session, "--disallowed-tools", ",".join(PERSON_DISALLOWED),
                                               "--", prompt]

    def new_person_session(self):
        """A person call with no --session-id, launched inside another session, would take that session's id and
        write into its transcripts; each gets a fresh id, the skill's and no other's."""
        session = str(uuid.uuid4())
        while session == self.session or session in self.person_sessions:
            session = str(uuid.uuid4())
        self.person_sessions.append(session)
        return session

    # ---- one call
    def call(self, role, argv, cwd, session, resumed=False):
        started = time.time()
        out = err = ""
        rc, failure = None, None
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8",
                                    errors="replace", start_new_session=(os.name == "posix"))
            try:
                out, err = proc.communicate(timeout=self.args.timeout_s)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL) if os.name == "posix" else proc.kill()
                except OSError:
                    proc.kill()
                out, err = proc.communicate()
                failure = "timed out after %d s" % self.args.timeout_s
        except OSError as error:
            failure = "could not start: %s" % error.__class__.__name__
        wall = time.time() - started
        result = self.parse(out)
        if failure is None and result is None:
            failure = "no JSON result on stdout (exit %s)" % rc
        reported = result.get("total_cost_usd") if result else None
        cost = None
        if isinstance(reported, (int, float)) and not isinstance(reported, bool) and math.isfinite(reported):
            cost = self.own_cost(role, reported, resumed)
            self.spent += cost
        else:
            reported = None
        # the account's address, from this call's own session, before anything from it is written
        self.note_emails(session)
        record = {"role": role, "argv": argv, "cwd": cwd, "session": session, "rc": rc, "wall_s": wall, "result": result,
                  "failure": failure, "cost": cost, "reported_cost": reported, "stderr": err}
        self.calls.append(record)
        self.log(record)
        return record

    def own_cost(self, role, reported, resumed):
        """A `--resume` call reports the session's cumulative cost (the CLI restores the session's cost state), so
        its own cost is its figure minus the session's previous one; a figure below the previous one means the
        counter restarted, and the call counts it as reported, so the budget is never undercounted. A first call
        and a person call (a fresh session each) count their figure as reported."""
        own = reported
        if resumed:
            # rounded to 1e-10 dollars: the subtraction's binary noise (0.09250000000000003) never reaches turns.jsonl
            added = round(reported - self.session_reported, 10)
            own = added if added >= 0 else reported
        if role == "skill":
            self.session_reported = reported
        return own

    def transcripts_of(self, session):
        """A session's main transcript(s) and its subagents' transcripts, under <config>/projects/*/."""
        found = glob.glob(os.path.join(self.config_dir(), "projects", "*", glob.escape(session) + ".jsonl"))
        paths = list(found)
        for path in found:
            paths += sorted(glob.glob(os.path.join(glob.escape(path[:-6]), "subagents", "agent-*.jsonl")))
        return paths

    def note_emails(self, session):
        if isinstance(session, str) and session:
            for path in self.transcripts_of(session):
                self.emails.note(read_jsonl(path, only=b"session_context"))

    # the secret values first, then the address: a secret that holds the address (`email:token`, a basic-auth
    # form) must still match whole, or its token is copied
    def redact(self, text):
        return self.emails.text(scrub(text))

    def redact_bytes(self, data):
        return self.emails.data(scrub_bytes(data))

    @staticmethod
    def parse(out):
        text = (out or "").strip()
        if not text:
            return None
        candidates = [text] + [line for line in reversed(text.split("\n")) if line.strip().startswith(("{", "["))]
        for candidate in candidates:
            try:
                value = json.loads(candidate)
            except ValueError:
                continue
            if isinstance(value, list):
                value = next((v for v in reversed(value) if isinstance(v, dict) and v.get("type") == "result"), None)
            if isinstance(value, dict):
                return value
        return None

    def log(self, record):
        result = record["result"] or {}
        usage = usage_keys(result)
        where = os.path.relpath(record["cwd"], self.bench)
        lines = ["[%s] %s call %d: exit %s, %.1f s, subtype %s, is_error %s, cost %s, reported %s, modelUsage %s%s" % (
            now(), record["role"], len(self.calls), record["rc"], record["wall_s"], result.get("subtype"),
            result.get("is_error"), record["cost"], record["reported_cost"], usage,
            ", FAILED: %s" % record["failure"] if record["failure"] else ""),
            "$ cd <bench>/%s && %s %s" % (where, self.env_prefix(),
                                          " ".join(shlex.quote(a) for a in record["argv"]).replace(self.bench, "<bench>"))]
        if record["stderr"].strip():
            lines.append("stderr: %s" % record["stderr"].strip()[-2000:])
        self.append("commands.txt", "\n".join(lines) + "\n\n")

    def append(self, name, text):
        with open(os.path.join(self.dest, name), "a", encoding="utf-8") as handle:
            handle.write(self.redact(text))

    def turn(self, role, text, record, source):
        """`source`: where `text` came from — "task" (the opening), "transcript" or "result"."""
        result = (record or {}).get("result") or {}
        entry = {"turn": len(self.turns), "role": role, "text": text, "text_source": source,
                 "cost_usd": record["cost"] if record else None,
                 "reported_total_cost_usd": record["reported_cost"] if record else None,
                 "duration_ms": result.get("duration_ms") if isinstance(result.get("duration_ms"), int) else None,
                 "num_turns": result.get("num_turns") if isinstance(result.get("num_turns"), int) else None,
                 "session_id": result.get("session_id") if isinstance(result.get("session_id"), str) else
                 (record["session"] if record else self.session),
                 "is_error": bool(result.get("is_error")) or bool(record and record["failure"])}
        self.turns.append(entry)
        self.append("turns.jsonl", json.dumps(entry, ensure_ascii=False) + "\n")

    # ---- setup
    def setup(self):
        os.makedirs(self.work)
        os.makedirs(self.person_dir)
        skill_dest = os.path.join(self.work, *in_bench(self.name).split("/"))
        skill_root = os.path.abspath(self.args.skill)

        def ignore(folder, names):
            return [name for name in names if name in SKILL_COPY_SKIP or name.endswith(".pyc")]

        shutil.copytree(skill_root, skill_dest, ignore=ignore)
        self.fixture_hashes = {}
        for dest, source in sorted(self.task["fixtures"].items()):
            target = os.path.join(self.bench, *dest.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)
            self.fixture_hashes[dest] = sha256(target)
        copied = sum(len(files) for _, _, files in os.walk(skill_dest))
        self.append("commands.txt", "[%s] bench <bench>: skill copied to <bench>/%s/%s (%d files); %d fixture(s) copied "
                    "and hashed; person folder <bench>/person\n\n"
                    % (now(), self.task["working_folder"], in_bench(self.name), copied, len(self.fixture_hashes)))

    # ---- the loop
    def prompt_candidates(self):
        """Every produced `prompts/*/master-prompt.md`, first under the working folder itself;
        failing that, under any folder up to PROMPT_DEPTH levels below it, PROMPT_SKIP never entered (a skill
        writes into the project folder the person named: `<working folder>/<project>/prompts/<slug>/`). A
        master-prompt.md the task's fixtures put in the bench is not one until its content changes."""
        found = self.produced(self.work)
        if not found:
            for folder, dirs, _ in os.walk(self.work):
                rel = os.path.relpath(folder, self.work)
                depth = 0 if rel == os.curdir else len(rel.split(os.sep))
                dirs[:] = [] if depth >= PROMPT_DEPTH else sorted(name for name in dirs if name not in PROMPT_SKIP)
                if depth:
                    found += self.produced(folder)
        return sorted(found)

    def produced(self, folder):
        """The prompts/*/master-prompt.md files under `folder`, less the task's fixtures while unchanged."""
        found = []
        for path in glob.glob(os.path.join(glob.escape(folder), PROMPT_PATTERN)):
            before = self.fixture_hashes.get(os.path.relpath(path, self.bench).replace(os.sep, "/"))
            if os.path.isfile(path) and (before is None or sha256(path) != before):
                found.append(path)
        return found

    def prompt_path(self, candidates=None):
        """The produced prompt: the newest candidate by mtime."""
        found = self.prompt_candidates() if candidates is None else candidates
        return max(found, key=os.path.getmtime) if found else None

    def from_work(self, path):
        return os.path.relpath(path, self.work).replace(os.sep, "/")

    def person_prompt(self):
        parts = ["<person>\n%s\n</person>" % self.task["opening"]]
        for entry in self.turns[1:]:
            tag = "assistant" if entry["role"] == "skill" else "person"
            parts.append("<%s>\n%s\n</%s>" % (tag, entry["text"], tag))
        values = {"HIDDEN_BRIEF": self.task["hidden_brief"].strip(), "CONVERSATION": "\n\n".join(parts)}
        return re.sub(r"\{(HIDDEN_BRIEF|CONVERSATION)\}", lambda m: values[m.group(1)], self.person_template)

    def main_transcript(self):
        found = glob.glob(os.path.join(self.config_dir(), "projects", "*", self.session + ".jsonl"))
        return max(found, key=os.path.getmtime) if found else None

    def transcript_mark(self):
        """Where the skill session's transcript ends before a call: (path or None, byte size or None if unknown)."""
        path = self.main_transcript()
        try:
            return path, os.path.getsize(path) if path else 0
        except OSError:
            return path, None

    def skill_message(self, mark, closing):
        """What the person is shown — every main-chain assistant text the call appended to the
        transcript, in order. Every record past the mark follows the call's own prompt, so a user record in the
        middle of the turn (a background seat's notification, a tool result) does not hide the texts before it.
        Falls back to the call's `result` (`closing`) when the transcript cannot be read or holds no new text."""
        before, offset = mark
        path = self.main_transcript()
        if path is None or offset is None or (before is not None and path != before):
            return closing, "result"
        texts = list(main_chain_texts(read_jsonl(path, offset)))
        return ("\n\n".join(texts), "transcript") if texts else (closing, "result")

    def loop(self):
        opening = self.task["opening"]
        message = ("/%s %s" % (self.name, opening)) if self.task["invoke"] == "slash" else opening
        self.turn("person", message, None, "task")
        first = True
        while True:
            if self.remaining() <= 0:
                return "max-budget"
            mark = self.transcript_mark()
            record = self.call("skill", self.skill_argv(message, first), self.work, self.session, resumed=not first)
            self.skill_calls += 1
            first = False
            result = record["result"] or {}
            closing = result.get("result") if isinstance(result.get("result"), str) else ""
            shown, source = self.skill_message(mark, closing)
            self.skill_texts.append(shown)
            self.turn("skill", shown, record, source)
            # the call's own outcome first, then the delivered test, and only then the spend
            if record["failure"]:
                return "error"
            subtype = result.get("subtype")
            if subtype == "error_max_turns":
                return "max-turns"
            if subtype == "error_max_budget_usd":   # the CLI cut the call: a prompt file on disk may be unfinished
                return "max-budget"
            if result.get("is_error"):
                return "error"
            if self.prompt_path() and not asks(closing):   # the closing message decides
                return "delivered"
            if self.person_calls >= self.max_person_turns:
                return "max-person-turns"
            if self.remaining() <= 0:
                return "max-budget"
            session = self.new_person_session()
            record = self.call("person", self.person_argv(self.person_prompt(), session), self.person_dir, session)
            self.person_calls += 1
            result = record["result"] or {}
            reply = result.get("result").strip() if isinstance(result.get("result"), str) else ""
            self.turn("person", reply, record, "result")
            if record["failure"] or result.get("is_error") or not reply:
                return "max-budget" if result.get("subtype") == "error_max_budget_usd" else "error"
            message = reply

    # ---- collection
    def config_dir(self):
        return self.env.get("CLAUDE_CONFIG_DIR") or os.path.join(self.env.get("HOME") or HOME, ".claude")

    def copy_text_tree(self, source, target):
        for folder, _, files in os.walk(source):
            rel = os.path.relpath(folder, source)
            os.makedirs(os.path.join(target, rel), exist_ok=True)
            for name in files:
                src, dst = os.path.join(folder, name), os.path.join(target, rel, name)
                try:
                    with open(src, encoding="utf-8") as handle:
                        text = handle.read()
                    with open(dst, "w", encoding="utf-8") as handle:
                        handle.write(self.redact(text))
                except UnicodeDecodeError:
                    with open(src, "rb") as handle:
                        data = handle.read()
                    with open(dst, "wb") as handle:
                        handle.write(self.redact_bytes(data))

    def collect(self, stop, started):
        self.note_emails(self.session)   # every transcript copied below has been read for the address first
        # the prompts/ folder that holds the produced prompt, wherever it is, in the frozen layout
        candidates = self.prompt_candidates()
        prompt = self.prompt_path(candidates)
        prompts = os.path.dirname(os.path.dirname(prompt)) if prompt else os.path.join(self.work, "prompts")
        prompt_out = os.path.join(self.dest, "prompt")
        os.makedirs(prompt_out, exist_ok=True)
        if os.path.isdir(prompts):
            self.copy_text_tree(prompts, prompt_out)
        # transcripts: the skill session's main transcript and its subagents
        transcripts = os.path.join(self.dest, "transcripts")
        os.makedirs(transcripts, exist_ok=True)
        main = self.main_transcript()
        subagents = sorted(glob.glob(os.path.join(main[:-6], "subagents", "agent-*.jsonl"))) if main else []
        if main:
            self.copy_file(main, os.path.join(transcripts, self.session + ".jsonl"))
            for path in subagents:
                self.copy_file(path, os.path.join(transcripts, "subagents", os.path.basename(path)))
                meta = path[:-6] + ".meta.json"
                if os.path.isfile(meta):
                    self.copy_file(meta, os.path.join(transcripts, "subagents", os.path.basename(meta)))
        # fixtures after
        fixtures = {}
        for dest, before in sorted(self.fixture_hashes.items()):
            target = os.path.join(self.bench, *dest.split("/"))
            fixtures[dest] = {"before": before, "after": sha256(target) if os.path.isfile(target) else None}
        self.write_json("fixtures.json", fixtures)
        # lint
        lint = self.lint(prompt)
        self.write_json("lint.json", lint)
        metrics = self.metrics(stop, started, main, prompt, candidates, lint)
        self.write_json("metrics.json", metrics)
        return metrics

    def copy_file(self, source, target):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(source, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(self.redact(text))

    def write_json(self, name, value):
        with open(os.path.join(self.dest, name), "w", encoding="utf-8") as handle:
            handle.write(self.redact(json.dumps(value, indent=1, ensure_ascii=False)) + "\n")

    def linter_path(self):
        if self.args.linter:
            return os.path.abspath(self.args.linter)
        candidate = os.path.join(os.path.abspath(self.args.skill), *SKILL_SCRIPTS[0].split("/"))
        return candidate if os.path.isfile(candidate) else None

    def lint(self, prompt):
        linter = self.linter_path()
        if not linter:
            return {"skipped": "no linter (none given and the skill has no %s)" % SKILL_SCRIPTS[0]}
        if not prompt:
            return {"skipped": "no master-prompt.md was produced"}
        argv = [sys.executable, linter, prompt, "--json"]
        decisions = os.path.join(os.path.dirname(prompt), "decisions.md")
        if os.path.isfile(decisions):
            argv[3:3] = ["--decisions", decisions]
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                              encoding="utf-8", errors="replace")
        self.append("commands.txt", "[%s] lint: exit %d\n$ %s\n\n" % (now(), proc.returncode,
                                                                     " ".join(shlex.quote(a) for a in argv)))
        try:
            value = json.loads(proc.stdout)
        except ValueError:
            return {"error": "the linter printed no JSON", "exit": proc.returncode, "stderr": proc.stderr[-2000:]}
        return value if isinstance(value, dict) else {"error": "the linter printed a non-object", "exit": proc.returncode}

    def metrics(self, stop, started, main, prompt, candidates, lint):
        main_records = read_jsonl(main) if main else []
        billed = sorted({key for call in self.calls for key in usage_keys(call["result"])})

        def skill_reads(records, folder):
            """The basenames of the bench copy's <folder>/*.md files the records Read, sorted."""
            pattern = re.compile(r"(?:^|/)%s/%s/([^/]+\.md)$" % (re.escape(in_bench(self.name)), folder))
            names = set()
            for name, data in tool_uses(records):
                path = data.get("file_path")
                found = pattern.search(path.replace("\\", "/")) if name == "Read" and isinstance(path, str) else None
                if found:
                    names.add(found.group(1))
            return sorted(names)

        guides = [name for name in skill_reads(main_records, "references") if name.startswith("harness-")]
        packs = [name for name in skill_reads(main_records, "packs") if name not in PACK_NOT_PACKS]
        skill_md = in_bench(self.name) + "/SKILL.md"
        loaded = any(name == "Skill" and any(isinstance(v, str) and v.strip().lstrip("/") == self.name
                                             for v in data.values())
                     for name, data in tool_uses(main_records)) or \
            any("<command-name>/%s</command-name>" % self.name in text for text in user_texts(main_records)) or \
            any(name == "Read" and isinstance(data.get("file_path"), str) and
                data["file_path"].replace("\\", "/").endswith(skill_md)
                for name, data in tool_uses(main_records))
        with_prompt = None
        if prompt:
            with open(prompt, encoding="utf-8", errors="replace") as handle:
                with_prompt = len(handle.read().split())
        costs = [call["cost"] for call in self.calls if call["cost"] is not None]
        return {
            "task": self.task["id"], "arm": self.args.arm, "model": self.args.model,
            "delivered": stop == "delivered", "stop_reason": stop,
            "skill_turns": self.skill_calls, "person_turns": self.person_calls,
            "total_cost_usd": round(sum(costs), 6), "wall_s": round(time.time() - started, 1),
            "questions_asked": sum(questions_in(text) for text in self.skill_texts),
            "framing_question_turns": sum(1 for text in self.skill_texts if is_framing_question(text)),
            "guide_reads": guides,
            "pack_reads": packs,
            "skill_loaded": bool(loaded),
            "effort": self.args.effort, "budget_usd": self.args.max_budget_usd,
            "prompt_words": with_prompt,
            "lint_errors": lint.get("errors") if isinstance(lint.get("errors"), int) else None,
            "lint_warnings": lint.get("warnings") if isinstance(lint.get("warnings"), int) else None,
            "lint_allowed": lint.get("allowed") if isinstance(lint.get("allowed"), int) else None,
            "prompt_dir": self.from_work(os.path.dirname(prompt)) if prompt else None,
            "prompt_candidates": [self.from_work(os.path.dirname(path)) for path in candidates],
            "model_usage_keys": billed,
        }

    def shown(self, path):
        absolute = os.path.abspath(path)
        if absolute.startswith(self.bench + os.sep):
            return os.path.relpath(absolute, self.bench).replace(os.sep, "/")
        return self.redact(path)


def exit_code(metrics):
    if metrics["stop_reason"] == "error":
        return 4
    return 0 if metrics["delivered"] else 3


def positive_budget(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("not a number: %r" % value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a positive number of dollars: %r" % value)
    return number


def parse_args(argv):
    parser = argparse.ArgumentParser(description="One headless run of a version of the skill.")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--bench", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--max-budget-usd", required=True, type=positive_budget)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort")
    parser.add_argument("--max-turns", type=int, default=80)
    parser.add_argument("--max-person-turns", type=int)
    parser.add_argument("--person-prompt")
    parser.add_argument("--linter")
    parser.add_argument("--allowed-tools")   # default: default_allowed_tools(<bench copy of the skill>, <name>)
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--timeout-s", type=int, default=3600)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if os.sep in args.claude_bin or "/" in args.claude_bin or args.claude_bin.endswith(".py"):
        args.claude_bin = os.path.abspath(args.claude_bin)  # every call runs from the bench, not from here
    return args


def check(args, task):
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", args.arm):
        raise Refusal("--arm must be a plain label (letters, digits, dot, dash, underscore)")
    if not os.path.isfile(os.path.join(args.skill, "SKILL.md")):
        raise Refusal("--skill must be a skill directory holding SKILL.md")
    if skill_name(args.skill) is None:
        raise Refusal("--skill: SKILL.md has no frontmatter `name` (lowercase letters, digits and single dashes)")
    if not args.model.strip() or any(c.isspace() for c in args.model):
        raise Refusal("--model must be a model id with no space")
    if args.max_turns < 1 or args.timeout_s < 1:
        raise Refusal("--max-turns and --timeout-s must be positive")
    if args.max_person_turns is not None and args.max_person_turns < 0:
        raise Refusal("--max-person-turns must not be negative")
    for flag in ("person_prompt", "linter"):
        path = getattr(args, flag)
        if path and not os.path.isfile(path):
            raise Refusal("--%s: no such file" % flag.replace("_", "-"))
    if args.person_prompt:
        with open(args.person_prompt, encoding="utf-8") as handle:
            template = handle.read()
        if "{HIDDEN_BRIEF}" not in template or "{CONVERSATION}" not in template:
            raise Refusal("--person-prompt must hold {HIDDEN_BRIEF} and {CONVERSATION}")
    bench = os.path.realpath(args.bench)
    if os.path.exists(bench) and (not os.path.isdir(bench) or os.listdir(bench)):
        raise Refusal("the bench must be a new or empty folder")
    repository = inside_git(bench)
    if repository:
        raise Refusal("the bench is inside a git repository (%s); put it outside any repository" % scrub(repository))
    dest = os.path.join(os.path.abspath(args.out), task["id"], args.arm)
    if os.path.isdir(dest) and os.listdir(dest):
        raise Refusal("the output folder for this task and arm is not empty: %s" % scrub(dest))
    skill = os.path.realpath(args.skill)
    if bench == skill or bench.startswith(skill + os.sep):
        raise Refusal("the bench must not be inside the skill")
    work = os.path.join(bench, task["working_folder"])
    if args.allowed_tools is None and re.search(r"[,()*\"']", work):
        raise Refusal("the default allowlist names the bench's working folder, so its path must not hold a comma, "
                      "a parenthesis, a star or a quote; move the bench or pass --allowed-tools")


def main(argv=None):
    args = parse_args(argv)
    try:
        task = load_task(args.task)
        check(args, task)
    except Refusal as refusal:
        sys.stderr.write("run_skill: refused: %s\n" % refusal)
        return 2
    task = with_model(task, args.model)
    run = Run(args, task)
    if args.dry_run:
        opening = ("/%s %s" % (run.name, task["opening"])) if task["invoke"] == "slash" else task["opening"]
        print("dry run: nothing is created and no claude call is made")
        print("task %s, arm %s, working folder <bench>/%s, %d fixture(s), person turns at most %d"
              % (task["id"], args.arm, task["working_folder"], len(task["fixtures"]), run.max_person_turns))
        print("environment: %s" % run.env_prefix())
        print("skill turn 1: cd <bench>/%s && %s" % (task["working_folder"], scrub(" ".join(
            shlex.quote(a) for a in run.skill_argv(opening, True)).replace(run.bench, "<bench>"))))
        print("person turns: cd <bench>/person && %s" % scrub(" ".join(
            shlex.quote(a) for a in run.person_argv("<person.md filled>", "<a new uuid4 per call>"))))
        return 0
    os.makedirs(run.dest, exist_ok=True)
    started = time.time()
    try:
        run.setup()
    except (OSError, shutil.Error) as error:
        sys.stderr.write("run_skill: refused: cannot set up the bench: %s\n" % scrub(str(error)))
        return 2
    stop = run.loop()
    metrics = run.collect(stop, started)
    code = exit_code(metrics)
    print(run.redact("task %s, arm %s: %s; cost $%.4f; skill turns %d, person turns %d; exit %d; out %s" % (
        task["id"], args.arm, stop, metrics["total_cost_usd"], metrics["skill_turns"],
        metrics["person_turns"], code, run.dest)))
    return code


if __name__ == "__main__":
    sys.exit(main())
