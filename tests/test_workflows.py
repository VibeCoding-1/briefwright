"""The workflows: parsed as a strict YAML subset with the standard library, then held to their safety rules.

The subset: block mappings and block sequences only, two-space indentation, one key per line; no anchors,
aliases, tags or merge keys; no flow mappings; a flow sequence only on one line; multi-line scalars only as
`run: |` or `script: |`; an empty value only for `workflow_dispatch:`; comments on their own lines. Anything
else fails rather than being guessed at. Dependabot's configuration and the issue chooser's are parsed the same
way. The rules are per workflow and per job: the events each workflow may run on, and the few jobs that may hold
more than contents: read, each with exactly its permissions and the only actions it may use. Every job runs its
own steps on a GitHub-hosted ubuntu- runner, so no code reaches a run that these rules have not read: no job calls
a reusable workflow, hands secrets on, or brings a container or services, and the script of a job that only runs
the script action may not run a command, load code or reach the network. Every rule is also run on the workflows
as a Dependabot pull request leaves them, so such a pull request passes these tests unchanged.
"""
import hashlib
import os
import re
import unittest

import support

WORKFLOWS = os.path.join(support.ROOT, ".github", "workflows")
DEPENDABOT_CONFIG = os.path.join(support.ROOT, ".github", "dependabot.yml")
ISSUE_TEMPLATES = os.path.join(support.ROOT, ".github", "ISSUE_TEMPLATE")
ISSUE_CONFIG = os.path.join(ISSUE_TEMPLATES, "config.yml")
# The issue chooser's links: each a name, a url on this repository and a one-line about, and between them a route
# for questions and one for reporting a vulnerability privately. The staged layout still holds the repository's
# placeholder, which the export fills.
STAGED = os.path.isdir(os.path.join(support.ROOT, "packaging"))
REPO = re.escape("{{" + "REPO" + "}}") if STAGED else r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+"
CONTACT_KEYS = {"name", "url", "about"}
CONTACT_ROUTES = ("/discussions", "/security/advisories/new")
REVIEW_PROMPT = ".github/codex/review-prompt.md"
PUBLIC_WARNING = ("Never print environment variables, tokens, or files outside the checkout; your message is posted "
                  "publicly.")
CODEX_ACTION = "openai/codex-action@"
CODEX_INPUTS = {"openai-api-key", "codex-version", "prompt-file", "permission-profile", "safety-strategy"}
# The Codex CLI the review action installs and runs with the key: one exact release, raised only by hand, here
# and in the workflow together. The read-only permission profile needs 0.138.0 or later.
CODEX_CLI = "0.160.0"
READ_ONLY = {"contents": "read"}
GUARD = ("vars.CODEX_REVIEW == 'true'", "github.event.pull_request.head.repo.full_name == github.repository")
# The key reaches no run Dependabot starts, and no run on a pull request Dependabot opened: the second clause reads
# the pull request's author, so a person's push to that branch, or a person's re-run, does not open the guard.
DEPENDABOT = ("github.actor != 'dependabot[bot]'", "github.event.pull_request.user.login != 'dependabot[bot]'")
# Each workflow and the events it may run on; a file not listed may run on nothing. pull_request_target and issues
# run with the repository's token for anyone who opens a pull request or an issue, so they appear only where
# every job is a fixed script (the rule below). workflow_run and issue_comment appear nowhere.
TRIGGERS = {
    "ci.yml": {"push", "pull_request"},
    "codex-review.yml": {"pull_request"},
    "release.yml": {"push"},
    "latest-tools.yml": {"schedule", "workflow_dispatch"},
    "welcome.yml": {"issues", "pull_request_target"},
    "labels.yml": {"workflow_dispatch"},
    "scorecard.yml": {"push", "schedule", "workflow_dispatch"},
    "codeql.yml": {"push", "pull_request", "schedule", "workflow_dispatch"},
}
REVIEW_TYPES = {"opened", "synchronize", "reopened"}
SCRIPT_ACTION, CHECKOUT = "actions/github-script@", "actions/checkout@"
CODE_SCANNING = "github/codeql-action/"
# The only jobs that may hold more than contents: read: (workflow, job) -> the exact permissions, and the actions
# its steps may use. None of them may have a run: step. The script-only ones check out nothing.
WRITERS = {
    ("codex-review.yml", "comment"): ({"pull-requests": "write"}, (SCRIPT_ACTION,)),
    ("release.yml", "release"): ({"contents": "write"}, (SCRIPT_ACTION,)),
    ("latest-tools.yml", "report"): ({"issues": "write"}, (SCRIPT_ACTION,)),
    ("welcome.yml", "issue"): ({"issues": "write"}, (SCRIPT_ACTION,)),
    ("welcome.yml", "pull-request"): ({"pull-requests": "write"}, (SCRIPT_ACTION,)),
    ("labels.yml", "labels"): ({"issues": "write"}, (SCRIPT_ACTION,)),
    ("scorecard.yml", "analysis"): ({"security-events": "write"},
                                     (CHECKOUT, "ossf/scorecard-action@", CODE_SCANNING + "upload-sarif@")),
    ("codeql.yml", "analyze"): ({"security-events": "write", "contents": "read"},
                                (CHECKOUT, CODE_SCANNING + "init@", CODE_SCANNING + "analyze@")),
}
# A job with one of these keys runs code that no rule here reads: a reusable workflow, the secrets handed to it, or
# a container or service image. Every job runs on a GitHub-hosted runner whose label starts with RUNNER.
FOREIGN_JOB_KEYS = ("uses", "secrets", "container", "services")
RUNNER = "ubuntu-"
# What the script of a job that runs only the script action may not do: run a command, load code or reach the
# network. The script action hands every script its exec and require.
SCRIPT_REACH = re.compile(r"\b(exec\.|child_process|require\(|import\(|eval\(|Function\(|fetch\()")
EMPTY_KEYS = ("workflow_dispatch",)
KEY = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?: (.*))?$")
EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}")
EVENT_FIELD = re.compile(r"github\.event\.pull_request\.(title|body|head\.ref|head\.label)\b|github\.head_ref\b"
                         r"|head_commit\.(message|author)"
                         r"|github\.event\.(commits|issue|comment|review|review_comment)\b")
PINNED = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")
USES_LINE = re.compile(r"^( *)(- )?uses: ([\w.-]+/[\w.-]+)")


class SubsetError(ValueError):
    pass


class Parser:
    def __init__(self, text):
        if "\t" in text:
            raise SubsetError("a tab character")
        self.lines = text.split("\n")
        self.i = 0

    def fail(self, message):
        raise SubsetError("line %d: %s" % (self.i + 1, message))

    def peek(self):
        """(indent, content) of the next line that is neither blank nor a comment, or None at the end."""
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            content = raw.strip()
            if content and not content.startswith("#"):
                if content in ("---", "..."):
                    self.fail("a document marker")
                return len(raw) - len(raw.lstrip(" ")), content
            self.i += 1
        return None

    def document(self):
        value = self.mapping(0)
        if self.peek() is not None:
            self.fail("unexpected indentation")
        return value

    def block(self, indent):
        head = self.peek()
        if head is None or head[0] != indent:
            self.fail("a nested block must be indented two spaces more than its key")
        return self.sequence(indent) if head[1].startswith("-") else self.mapping(indent)

    def mapping(self, indent, first=None):
        result = {}
        while True:
            if first is not None:
                content, first = first, None
            else:
                head = self.peek()
                if head is None or head[0] < indent:
                    return result
                if head[0] > indent:
                    self.fail("unexpected indentation")
                content = head[1]
            match = KEY.match(content)
            if not match:
                self.fail("not a 'key: value' line: %r" % content[:40])
            key, rest = match.group(1), match.group(2)
            if key in result:
                self.fail("duplicate key %r" % key)
            self.i += 1
            if not rest:
                head = self.peek()
                if key in EMPTY_KEYS and (head is None or head[0] <= indent):
                    result[key] = None
                else:
                    result[key] = self.block(indent + 2)
            elif rest == "|":
                if key not in ("run", "script"):
                    self.fail("a block scalar outside run: or script:")
                result[key] = self.literal(indent)
            else:
                result[key] = self.scalar(rest)

    def sequence(self, indent):
        items = []
        while True:
            head = self.peek()
            if head is None or head[0] < indent:
                return items
            if head[0] > indent or not head[1].startswith("- ") or head[1][2:3] == " ":
                self.fail("a sequence item must be '- ' and its value, at the sequence's indentation")
            item = head[1][2:]
            if KEY.match(item):
                items.append(self.mapping(indent + 2, first=item))
            else:
                self.i += 1
                items.append(self.scalar(item))

    def literal(self, indent):
        body = []
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if raw.strip():
                depth = len(raw) - len(raw.lstrip(" "))
                if depth <= indent:
                    break
                if depth < indent + 2:
                    self.fail("block text must be indented two spaces more than its key")
            body.append(raw[indent + 2:])
            self.i += 1
        while body and not body[-1].strip():
            body.pop()
        if not body:
            self.fail("an empty block scalar")
        return "\n".join(body) + "\n"

    def scalar(self, text):
        if text[0] in "&*!{|>%@`" or text.startswith("- ") or text.startswith("<<"):
            self.fail("an anchor, alias, tag, flow mapping or folded scalar: %r" % text[:40])
        if text[0] == "[":
            items = [item.strip() for item in text[1:-1].split(",")] if text.endswith("]") else []
            if not items or not all(re.match(r"^[A-Za-z0-9_.-]+$", item) for item in items):
                self.fail("a flow sequence must be one line of plain words")
            return items
        if text[0] == '"':
            if len(text) < 2 or not text.endswith('"') or '"' in text[1:-1] or "\\" in text:
                self.fail("a double-quoted scalar with an escape or a trailing part")
            return text[1:-1]
        if text[0] == "'":
            inner = text[1:-1]
            if len(text) < 2 or not text.endswith("'") or "'" in inner.replace("''", ""):
                self.fail("a single-quoted scalar with a trailing part")
            return inner.replace("''", "'")
        if " #" in text:
            self.fail("a comment after a value; comments go on their own lines")
        if ": " in text or text.endswith(":"):
            self.fail("a plain scalar holding ': '")
        return text


def parse(text):
    return Parser(text).document()


def scalars(value, path=()):
    """Every (path, scalar) of a parsed value; a list index is an int in the path."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from scalars(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from scalars(child, path + (index,))
    else:
        yield path, value


def where(path):
    return ".".join(str(step) for step in path)


def triggers(doc):
    on = doc.get("on")
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return dict.fromkeys(on)
    return on if isinstance(on, dict) else {}


def untagged(text):
    """Every action whose step has no comment naming the action's repository and a release tag: on the step's
    own lines above its uses:, or on the comment lines right above the step."""
    lines = text.split("\n")
    found = []
    for number, line in enumerate(lines):
        match = USES_LINE.match(line)
        if not match:
            continue
        indent, repository = len(match.group(1)), match.group(3)
        step_indent = indent if match.group(2) else indent - 2
        start = number
        while start > 0 and not lines[start].startswith(" " * step_indent + "- "):
            start -= 1
        block = lines[start:number]
        above = start - 1
        while above >= 0 and lines[above].strip().startswith("#"):
            block.append(lines[above])
            above -= 1
        tag = re.compile(r"^\s*# %s v[0-9]" % re.escape(repository))
        if not any(tag.match(candidate) for candidate in block):
            found.append(repository)
    return found


def steps_outside(steps, actions):
    """The indexes of the steps that are not a `uses:` of one of `actions`, or that run a shell."""
    return [index for index, step in enumerate(steps) if not isinstance(step, dict) or "run" in step
            or not str(step.get("uses", "")).startswith(actions)]


def problems(workflow, text, root=None):
    """Every rule the workflow file `workflow` (its name) with this text breaks, as messages; [] when it is safe."""
    found = []
    pin_token = "<" + "pin:"
    if pin_token in text:
        found.append("an unresolved %s placeholder" % pin_token)
    for match in EVENT_FIELD.finditer(text):
        found.append("an attacker-controlled event field: %s" % match.group(0))
    for repository in untagged(text):
        found.append("action %s has no comment above it with its release tag (# %s v...)" % (repository, repository))
    try:
        doc = parse(text)
    except SubsetError as error:
        return found + ["outside the YAML subset (%s)" % error]

    events = triggers(doc)
    if not events:
        found.append("no trigger")
    for event in events:
        if event not in TRIGGERS.get(workflow, ()):
            found.append("forbidden trigger %r in %s" % (event, workflow))
    if "schedule" in events and "workflow_dispatch" not in events:
        found.append("a scheduled workflow without a manual trigger (workflow_dispatch)")

    secret_jobs = set()
    for path, value in scalars(doc):
        if not isinstance(value, str):
            continue
        expressions = EXPRESSION.findall(value)
        if path[-1] == "if" and "${{" not in value:
            expressions.append(value)
        if path[-1] in ("run", "script") and expressions:
            found.append("an expression inside a %s: body at %s (pass it through env:)" % (path[-1], where(path)))
        if any(re.search(r"\bgithub\.token\b", expression) for expression in expressions):
            found.append("the job's token handed over by name at %s: an action takes it by default, and a run: step "
                         "never gets it" % where(path))
        if not any(re.search(r"\bsecrets\b", expression) for expression in expressions):
            continue
        in_step = len(path) == 6 and path[0] == "jobs" and path[2] == "steps"
        step = doc["jobs"][path[1]]["steps"][path[3]] if in_step else {}
        allowed = (path[4:] == ("with", "openai-api-key") and str(step.get("uses", "")).startswith(CODEX_ACTION)
                   and value.strip() == "${{ secrets.OPENAI_API_KEY }}")
        if allowed:
            secret_jobs.add(path[1])
        else:
            found.append("a secret referenced outside the review action's openai-api-key input, at %s" % where(path))

    top = doc.get("permissions")
    if top != READ_ONLY:
        found.append("top-level permissions must be only contents: read, not %r" % (top,))

    for name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            found.append("job %s is not a mapping" % name)
            continue
        steps = job.get("steps") or []
        for key in FOREIGN_JOB_KEYS:
            if key in job:
                found.append("job %s has a %s: key: a job runs only its own steps, so it calls no reusable workflow, "
                             "hands no secrets on and brings no container or services" % (name, key))
        runner = job.get("runs-on")
        if not (isinstance(runner, str) and runner.startswith(RUNNER)):
            found.append("job %s runs on %r, not on a GitHub-hosted %s runner" % (name, runner, RUNNER))
        permissions = job.get("permissions")
        grant = WRITERS.get((workflow, name))
        if grant and grant[1] == (SCRIPT_ACTION,):
            for index, step in enumerate(steps):
                inputs = step.get("with") if isinstance(step, dict) else None
                script = inputs.get("script") if isinstance(inputs, dict) else None
                for match in SCRIPT_REACH.finditer(script if isinstance(script, str) else ""):
                    found.append("job %s's script at steps.%d calls %s: a writer's script runs no command, loads no "
                                 "code and reaches no network" % (name, index, match.group(0)))
        if grant and permissions == grant[0]:
            others = steps_outside(steps, grant[1])
            if others:
                found.append("job %s may hold %s only with no run: step and every step one of %s (not steps %s)"
                             % (name, sorted(permissions), ", ".join(grant[1]), others))
        elif permissions not in (None, READ_ONLY):
            found.append("job %s's permissions %r are outside the allowlist: contents: read%s"
                         % (name, permissions, ", or %r for this job alone" % (grant[0],) if grant else ""))
        if "pull_request_target" in events:
            others = steps_outside(steps, (SCRIPT_ACTION,))
            if others:
                found.append("job %s runs on pull_request_target, so it may check out nothing and run no run: step: "
                             "every step the script action alone (not steps %s)" % (name, others))
        for index, step in enumerate(steps):
            uses = step.get("uses") if isinstance(step, dict) else None
            if uses is None:
                continue
            if not PINNED.match(uses):
                found.append("action not pinned by a commit SHA: %s" % uses)
            if uses.startswith(CHECKOUT) and (step.get("with") or {}).get("persist-credentials") != "false":
                found.append("checkout without persist-credentials: false at jobs.%s.steps.%d" % (name, index))
            if uses.startswith(CODEX_ACTION):
                inputs = step.get("with") if isinstance(step.get("with"), dict) else {}
                extra = sorted(set(inputs) - CODEX_INPUTS)
                if extra:
                    found.append("the Codex action takes inputs outside its allowlist: %s" % ", ".join(extra))
                if inputs.get("codex-version") != CODEX_CLI:
                    found.append("the Codex action must pin codex-version to %s, not %r"
                                 % (CODEX_CLI, inputs.get("codex-version")))
                if index != len(steps) - 1:
                    found.append("the Codex action is not the last step of job %s" % name)
                if "prompt" in inputs or inputs.get("prompt-file") != REVIEW_PROMPT:
                    found.append("the Codex action must read its prompt only from %s" % REVIEW_PROMPT)
                if inputs.get("permission-profile") != ":read-only" or "sandbox" in inputs:
                    found.append("the Codex action must run with permission-profile :read-only")
                if inputs.get("safety-strategy") != "drop-sudo":
                    found.append("the Codex action must run with safety-strategy drop-sudo")
                if root is not None and not os.path.isfile(os.path.join(root, REVIEW_PROMPT)):
                    found.append("the review prompt %s is missing" % REVIEW_PROMPT)
        if name not in secret_jobs:
            continue
        guard = re.sub(r"\s+", " ", str(job.get("if", "")))
        clauses = [clause.strip() for clause in guard.split("&&")]
        if "||" in guard or not all(clause in clauses for clause in GUARD):
            found.append("job %s holds a secret without the guard %s" % (name, " && ".join(GUARD)))
        for clause in DEPENDABOT:
            if clause not in clauses:
                found.append("job %s's guard lacks the Dependabot clause %s" % (name, clause))
        if job.get("permissions") != {"contents": "read"}:
            found.append("job %s holds a secret, so its permissions must be only contents: read, not %r"
                         % (name, job.get("permissions")))

    if secret_jobs:
        for event, config in events.items():
            if event != "pull_request":
                found.append("a workflow holding a secret runs on %r" % event)
                continue
            types = config.get("types") if isinstance(config, dict) else None
            if not isinstance(types, list) or not types or set(types) - REVIEW_TYPES:
                found.append("pull_request types must be within %s, not %r" % (sorted(REVIEW_TYPES), types))
    return found


def contact_problems(doc):
    """What keeps the issue chooser's contact links from each holding a name, a url on this repository and an
    about, and from routing questions and vulnerability reports."""
    links = doc.get("contact_links")
    if not isinstance(links, list) or not links:
        return ["no contact_links"]
    problems = []
    for index, link in enumerate(links):
        if not isinstance(link, dict) or set(link) != CONTACT_KEYS \
                or not all(isinstance(value, str) and value.strip() for value in link.values()):
            problems.append("contact_links.%d: not exactly a name, a url and an about" % index)
        elif not re.fullmatch(r"https://github\.com/%s/[\w./-]+" % REPO, link["url"]):
            problems.append("contact_links.%d: %s is not on this repository" % (index, link["url"]))
    urls = [link.get("url", "") for link in links if isinstance(link, dict)]
    problems += ["no link to %s" % route for route in CONTACT_ROUTES if not any(url.endswith(route) for url in urls)]
    return problems


def read_workflow(name):
    return support.read(os.path.join(WORKFLOWS, name))


def run_lines(job):
    """Every non-blank line of the job's run: steps, stripped."""
    return [line.strip() for step in job.get("steps", []) for line in step.get("run", "").split("\n")
            if line.strip()]


def template_labels():
    """{template file: the labels its front matter applies}."""
    found = {}
    for name in sorted(os.listdir(ISSUE_TEMPLATES)):
        if not name.endswith(".md"):
            continue
        front = support.read(os.path.join(ISSUE_TEMPLATES, name)).split("---\n")[1]
        value = re.search(r"^labels:(.*)$", front, re.M).group(1).strip().strip("[]")
        found[name] = [label.strip().strip("\"'") for label in value.split(",") if label.strip().strip("\"'")]
    return found


def listed_labels(text):
    """[(name, colour, description)] of the labels workflow's list."""
    return re.findall(r'\{ name: "([^"]+)", color: "([^"]+)", description: "([^"]+)" \}', text)


def bumped(text):
    """The workflow as a Dependabot pull request leaves it, its tag comments then corrected by hand: every action
    moved to another full commit SHA, and every release tag named in a comment raised."""
    text = re.sub(r"(uses: [\w.-]+/[\w./-]+@)([0-9a-f]{40})\b",
                  lambda match: match.group(1) + hashlib.sha1(match.group(2).encode("ascii")).hexdigest(), text)
    return re.sub(r"(# [\w.-]+/[\w.-]+ v)[0-9]+(?:\.[0-9]+)*", r"\g<1>99.0.0", text)


class Subset(unittest.TestCase):
    def test_a_small_workflow_parses(self):
        text = ("name: Example\non: [push, pull_request]\npermissions:\n  contents: read\njobs:\n  one:\n"
                "    runs-on: ubuntu-24.04\n    steps:\n      # a comment\n      - name: Say it\n"
                "        run: |\n          echo one\n\n          echo two\n      - name: \"Quoted\"\n")
        doc = parse(text)
        self.assertEqual(doc["on"], ["push", "pull_request"])
        self.assertEqual(doc["jobs"]["one"]["steps"][0]["run"], "echo one\n\necho two\n")
        self.assertEqual(doc["jobs"]["one"]["steps"][1]["name"], "Quoted")

    def test_a_manual_trigger_parses_empty(self):
        self.assertEqual(parse("on:\n  workflow_dispatch:\n")["on"], {"workflow_dispatch": None})
        self.assertEqual(parse("on:\n  workflow_dispatch:\n  push:\n    branches:\n      - main\n")["on"],
                         {"workflow_dispatch": None, "push": {"branches": ["main"]}})

    def test_anything_outside_the_subset_fails(self):
        cases = {
            "an anchor": "a: &x 1\n",
            "an alias": "a: *x\n",
            "a tag": "a: !!str 1\n",
            "a merge key": "a:\n  <<: b\n",
            "a flow mapping": "a: {b: 1}\n",
            "a multi-line flow sequence": "a: [b,\n  c]\n",
            "a folded scalar": "a: >\n  text\n",
            "a block scalar on another key": "name: |\n  text\n",
            "a trailing comment": "a: b # note\n",
            "a tab": "a:\n\tb: 1\n",
            "four-space indentation": "a:\n    b: 1\n",
            "a sequence at its key's indentation": "a:\n- b\n",
            "two keys on one line": "a: b: c\n",
            "a duplicate key": "a: 1\na: 2\n",
            "a document marker": "---\na: 1\n",
            "a double-quoted escape": "a: \"b\\n\"\n",
            "an empty value on another key": "on:\n  pull_request:\n  push:\n    branches:\n      - main\n",
            "an empty value at the end": "a:\n",
            "a manual trigger with an empty flow mapping": "on:\n  workflow_dispatch: {}\n",
        }
        for label, text in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(SubsetError):
                    parse(text)


class TheWorkflows(unittest.TestCase):
    def test_the_expected_files_exist(self):
        self.assertEqual(sorted(os.listdir(WORKFLOWS)), sorted(TRIGGERS))
        self.assertTrue(os.path.isfile(os.path.join(support.ROOT, REVIEW_PROMPT)))

    def test_every_workflow_is_in_the_subset_and_safe(self):
        for name in sorted(os.listdir(WORKFLOWS)):
            with self.subTest(workflow=name):
                self.assertEqual(problems(name, read_workflow(name), support.ROOT), [])

    def test_every_writer_in_the_allowlist_exists_and_holds_its_permissions(self):
        """The allowlist names no job that is gone: each entry is a job of its workflow, holding exactly what the
        list grants it."""
        for (workflow, job), (permissions, _) in sorted(WRITERS.items()):
            with self.subTest(workflow=workflow, job=job):
                self.assertEqual(parse(read_workflow(workflow))["jobs"][job].get("permissions"), permissions)

    def test_ci_runs_every_check(self):
        doc = parse(read_workflow("ci.yml"))
        self.assertEqual(doc["on"], ["push", "pull_request"])
        self.assertEqual(doc["permissions"], {"contents": "read"})
        test, validate = doc["jobs"]["test"], doc["jobs"]["validate"]
        self.assertEqual(test["strategy"]["matrix"]["python"], ["3.9", "3.14"])
        runs = [step.get("run", "") for step in test["steps"]]
        for command in ("tools/scan_public.py --tree . --commit HEAD --warn-metadata", "tests/run_tests.py",
                        "tools/check_skill.py", "tools/check_manifests.py"):
            self.assertTrue(any(command in run for run in runs), command)
        self.assertIn("scan_public.py", runs[2], "the scan runs before anything else writes to the tree")
        setup = [step for step in validate["steps"] if "setup-python" in step.get("uses", "")]
        self.assertEqual(setup[0]["with"]["python-version"], "3.13")
        text = "".join(step.get("run", "") for step in validate["steps"])
        for command in ("agentskills validate skills/", "check-jsonschema --schemafile "
                        "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugin.json",
                        "claude plugin validate . --strict"):
            self.assertIn(command, text)
        self.assertNotRegex(read_workflow("ci.yml"), r"\bsecrets\b\s*[.\[]")

    def test_the_dependabot_clauses_read_no_pull_request_text(self):
        """The author clause reads who opened the pull request, not its text: the rule against pull request text
        must not catch it."""
        self.assertEqual([clause for clause in DEPENDABOT if EVENT_FIELD.search(clause)], [])

    def test_the_review_job_shape(self):
        doc = parse(read_workflow("codex-review.yml"))
        review, comment = doc["jobs"]["review"], doc["jobs"]["comment"]
        self.assertEqual(review["steps"][-1]["uses"].split("@")[0], "openai/codex-action")
        self.assertEqual(review["steps"][-1]["with"]["codex-version"], CODEX_CLI)
        self.assertEqual(comment["needs"], "review")
        self.assertEqual(comment["permissions"], {"pull-requests": "write"})
        self.assertIn("needs.review.outputs.final-message", comment["steps"][0]["env"]["REVIEW"])
        self.assertIn("process.env.REVIEW", comment["steps"][0]["with"]["script"])

    def test_the_codex_cli_pin_is_an_exact_release_new_enough(self):
        self.assertRegex(CODEX_CLI, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertGreaterEqual(tuple(int(part) for part in CODEX_CLI.split(".")), (0, 138, 0))

    def test_the_review_prompt_says_the_message_is_public(self):
        prompt = " ".join(support.read(os.path.join(support.ROOT, REVIEW_PROMPT)).split())
        self.assertIn(PUBLIC_WARNING, prompt)

    def test_a_release_takes_its_notes_from_the_changelog_and_keeps_an_existing_one(self):
        doc = parse(read_workflow("release.yml"))
        self.assertEqual(doc["on"], {"push": {"tags": ["v*"]}})
        notes, release = doc["jobs"]["notes"], doc["jobs"]["release"]
        cut = [step for step in notes["steps"] if "run" in step]
        self.assertEqual(len(cut), 1)
        self.assertEqual(cut[0]["env"], {"TAG": "${{ github.ref_name }}"})
        self.assertIn('python3 tools/release_notes.py "$TAG"', cut[0]["run"])
        self.assertEqual(notes["outputs"]["notes"], "${{ steps.%s.outputs.notes }}" % cut[0]["id"])
        self.assertEqual(release["needs"], "notes")
        [step] = release["steps"]
        self.assertEqual(step["env"], {"NOTES": "${{ needs.notes.outputs.notes }}"})
        script = step["with"]["script"]
        for part in ("getReleaseByTag", "error.status !== 404", "already_exists", "createRelease",
                     "body: process.env.NOTES"):
            self.assertIn(part, script)
        self.assertLess(script.index("getReleaseByTag"), script.index("createRelease"),
                        "an existing release is looked for before one is created")

    def test_a_tag_with_a_hyphen_is_released_as_a_pre_release(self):
        """v1.1.0-rc.1 becomes a pre-release, which GitHub never marks as the latest release; v1.1.0 a full one."""
        [step] = parse(read_workflow("release.yml"))["jobs"]["release"]["steps"]
        self.assertRegex(step["with"]["script"], r'createRelease\(\{[^}]*\bprerelease: tag\.includes\("-"\)[^}]*\}\)')

    def test_the_weekly_check_runs_every_ci_check_on_the_newest_tools(self):
        ci = parse(read_workflow("ci.yml"))["jobs"]
        doc = parse(read_workflow("latest-tools.yml"))
        check, report = doc["jobs"]["check"], doc["jobs"]["report"]
        ci_lines = run_lines(ci["test"]) + run_lines(ci["validate"])
        installs = ("python -m pip install", "npm i -g")
        lines = run_lines(check)
        for line in ci_lines:
            if not line.startswith(installs):
                self.assertIn(line, lines)
        pinned = " ".join(line for line in ci_lines if line.startswith(installs))
        pip = [line.split() for line in lines if line.startswith("python -m pip install --upgrade ")]
        npm = [line.split() for line in lines if line.startswith("npm i -g ")]
        self.assertEqual((len(pip), len(npm)), (1, 1))
        for name in re.findall(r'"([\w.-]+)==[^"]+"', pinned):
            self.assertIn(name, pip[0])
        for name in re.findall(r'"(@[\w.-]+/[\w.-]+)@[^"]+"', pinned) + ["@openai/codex"]:
            self.assertIn(name + "@latest", npm[0])
        self.assertNotRegex(" ".join(lines), r"==|@[0-9]", "the weekly check pins nothing")
        setup = [step for step in check["steps"] if step.get("uses", "").startswith("actions/setup-python@")]
        self.assertEqual(setup[0]["with"], {"python-version": "3.x", "check-latest": "true"})
        self.assertNotRegex(read_workflow("latest-tools.yml"), r"\bsecrets\b\s*[.\[]")
        self.assertEqual(report["needs"], "check")
        self.assertTrue(report["if"].startswith("failure() && "), report["if"])
        script = report["steps"][0]["with"]["script"]
        for part in ("item.title === title", 'item.user.login === "github-actions[bot]"', "createComment",
                     "issues.create(", "context.runId"):
            self.assertIn(part, script)
        self.assertLess(script.index("createComment"), script.index("issues.create("),
                        "the open issue is updated before a new one would be opened")

    def test_the_weekly_workflows_have_a_schedule_and_a_manual_trigger(self):
        for name in ("latest-tools.yml", "scorecard.yml", "codeql.yml"):
            with self.subTest(workflow=name):
                events = triggers(parse(read_workflow(name)))
                self.assertEqual(len(events["schedule"]), 1)
                self.assertRegex(events["schedule"][0]["cron"], r"^[0-9]+ [0-9]+ \* \* [0-6]$")
                self.assertIn("workflow_dispatch", events)

    def test_the_welcome_posts_only_on_a_first_issue_or_pull_request(self):
        doc = parse(read_workflow("welcome.yml"))
        self.assertEqual(doc["on"], {"issues": {"types": ["opened"]}, "pull_request_target": {"types": ["opened"]}})
        for job, event, payload in (("issue", "issues", "context.payload.issue"),
                                    ("pull-request", "pull_request_target", "context.payload.pull_request")):
            with self.subTest(job=job):
                spec = doc["jobs"][job]
                self.assertEqual(spec["if"], "github.event_name == '%s'" % event)
                [step] = spec["steps"]
                script = step["with"]["script"]
                self.assertIn(payload, script)
                for part in ('user.type === "Bot"', '["OWNER", "MEMBER", "COLLABORATOR"]', "item.number !==",
                             "createComment"):
                    self.assertIn(part, script)
                self.assertNotIn("env", step)

    def test_every_label_a_template_applies_is_in_the_labels_list(self):
        listed = listed_labels(read_workflow("labels.yml"))
        names = [name for name, _, _ in listed]
        self.assertEqual(len(names), len(set(names)))
        for name, colour, description in listed:
            self.assertRegex(colour, r"^[0-9a-f]{6}$")
            self.assertLessEqual(len(description), 100, "GitHub keeps a label description to 100 characters")
        applied = template_labels()
        self.assertIn("bug", applied["bug_report.md"])
        for template, labels in applied.items():
            for label in labels:
                with self.subTest(template=template, label=label):
                    self.assertIn(label, names)

    def test_code_scanning_is_skipped_while_the_repository_is_private(self):
        for name, job in (("scorecard.yml", "analysis"), ("codeql.yml", "analyze")):
            with self.subTest(workflow=name):
                jobs = parse(read_workflow(name))["jobs"]
                gate = jobs["visibility"]
                self.assertNotIn("permissions", gate)
                [step] = gate["steps"]
                self.assertTrue(step["uses"].startswith(SCRIPT_ACTION))
                self.assertEqual(gate["outputs"], {"analyze": "${{ steps.%s.outputs.analyze }}" % step["id"]})
                script = step["with"]["script"]
                self.assertIn("github.rest.repos.get(context.repo)", script)
                self.assertRegex(script, r'core\.setOutput\("analyze", String\(!data\.private[ )&]')
                self.assertIn("core.notice(", script)
                self.assertEqual((jobs[job]["needs"], jobs[job]["if"]),
                                 ("visibility", "needs.visibility.outputs.analyze == 'true'"))

    def test_codeql_scans_the_python_code_and_the_workflows(self):
        analyze = parse(read_workflow("codeql.yml"))["jobs"]["analyze"]
        self.assertEqual(analyze["strategy"]["matrix"], {"language": ["actions", "python"]})
        init = [step for step in analyze["steps"] if step.get("uses", "").startswith(CODE_SCANNING + "init@")]
        self.assertEqual(init[0]["with"], {"languages": "${{ matrix.language }}", "build-mode": "none"})

    def test_scorecard_uploads_to_code_scanning(self):
        steps = parse(read_workflow("scorecard.yml"))["jobs"]["analysis"]["steps"]
        scorecard = [step for step in steps if step.get("uses", "").startswith("ossf/scorecard-action@")]
        self.assertEqual(scorecard[0]["with"], {"results_file": "results.sarif", "results_format": "sarif",
                                                "publish_results": "false"})
        self.assertEqual(steps[-1]["with"], {"sarif_file": "results.sarif"})
        self.assertTrue(steps[-1]["uses"].startswith(CODE_SCANNING + "upload-sarif@"))


class TheRulesBite(unittest.TestCase):
    """Each rule, broken once in a copy of a workflow, is reported. No case names a pin's commit or release tag:
    those move with every Dependabot pull request."""

    def workflow(self, name):
        return read_workflow(name)

    def mutate(self, old, new, workflow="codex-review.yml"):
        text = self.workflow(workflow)
        self.assertIn(old, text)
        return problems(workflow, text.replace(old, new, 1), support.ROOT)

    def pin(self, action, workflow="codex-review.yml"):
        """`<action>@<commit>` as the workflow pins it."""
        found = re.search(r"%s@[0-9a-f]{40}\b" % re.escape(action), self.workflow(workflow))
        self.assertIsNotNone(found, "%s is not pinned in %s" % (action, workflow))
        return found.group(0)

    def tag_comment(self, action, workflow):
        """The comment line above the action's step, with its release tag, as the workflow has it."""
        found = re.search(r"\n *# %s v[0-9][^\n]*\n" % re.escape(action), self.workflow(workflow))
        self.assertIsNotNone(found, "%s has no tag comment in %s" % (action, workflow))
        return found.group(0)

    def step(self, action, workflow, name="Planted"):
        """A step that uses the action as the workflow pins it."""
        return "      # %s v1.0.0\n      - name: %s\n        uses: %s\n" % (action, name, self.pin(action, workflow))

    def assertReported(self, found, fragment):
        self.assertTrue(any(fragment in message for message in found), "%r not in %r" % (fragment, found))

    def test_a_forbidden_trigger(self):
        for event in ("pull_request_target", "workflow_dispatch", "workflow_run", "issue_comment"):
            with self.subTest(event=event):
                self.assertReported(self.mutate("on:\n", "on:\n  %s:\n    types:\n      - opened\n" % event),
                                    "forbidden trigger %r" % event)
        self.assertReported(self.mutate("on:\n", "on:\n  push:\n    branches:\n      - main\n"),
                            "a workflow holding a secret runs on 'push'")
        self.assertReported(self.mutate("      - reopened\n", "      - reopened\n      - labeled\n"),
                            "pull_request types must be within")

    def test_a_trigger_outside_the_workflow_s_own_list(self):
        for workflow, event in (("release.yml", "pull_request"), ("welcome.yml", "workflow_run"),
                                ("latest-tools.yml", "pull_request_target"), ("labels.yml", "issues"),
                                ("codeql.yml", "pull_request_target"), ("scorecard.yml", "pull_request")):
            with self.subTest(workflow=workflow, event=event):
                found = self.mutate("\npermissions:\n", "\n  %s:\n    types:\n      - opened\n\npermissions:\n" % event,
                                    workflow)
                self.assertReported(found, "forbidden trigger %r in %s" % (event, workflow))
        found = self.mutate("on: [push, pull_request]\n", "on: [push, pull_request, workflow_dispatch]\n", "ci.yml")
        self.assertReported(found, "forbidden trigger 'workflow_dispatch' in ci.yml")
        found = problems("unknown.yml", self.workflow("ci.yml"), support.ROOT)
        self.assertReported(found, "forbidden trigger 'push' in unknown.yml")

    def test_a_scheduled_workflow_without_a_manual_trigger(self):
        for workflow in ("latest-tools.yml", "scorecard.yml", "codeql.yml"):
            with self.subTest(workflow=workflow):
                self.assertReported(self.mutate("  workflow_dispatch:\n", "", workflow),
                                    "a scheduled workflow without a manual trigger")

    def test_a_secret_outside_the_action_input(self):
        found = self.mutate("    runs-on: ubuntu-24.04\n    permissions:\n      contents: read\n",
                            "    runs-on: ubuntu-24.04\n    env:\n      KEY: ${{ secrets.OPENAI_API_KEY }}\n"
                            "    permissions:\n      contents: read\n")
        self.assertReported(found, "a secret referenced outside the review action's openai-api-key input")
        self.assertReported(self.mutate("          REVIEW: ${{ needs.review.outputs.final-message }}\n",
                                        "          REVIEW: ${{ secrets.GITHUB_TOKEN }}\n"),
                            "a secret referenced outside")

    def test_a_secret_in_a_job_anyone_can_start(self):
        """Anyone can open an issue or a pull request, and pull_request_target hands the job the repository's
        secrets even for a fork: no secret may appear there, nor in the other workflows a fork's pull request
        starts."""
        for workflow, anchor in (("welcome.yml", "        with:\n          script: |\n            const pull"),
                                 ("welcome.yml", "        with:\n          script: |\n            const issue"),
                                 ("codeql.yml", "        with:\n          languages:"),
                                 ("ci.yml", "        with:\n          python-version: ${{ matrix.python }}")):
            with self.subTest(workflow=workflow, anchor=anchor[-20:]):
                found = self.mutate(anchor, "        env:\n          KEY: ${{ secrets.ANY_KEY }}\n" + anchor,
                                    workflow)
                self.assertReported(found, "a secret referenced outside")

    def test_the_token_handed_over_by_name(self):
        anchor = "      - name: Run the tests\n"
        planted = ("      - name: List the issues\n        env:\n          GH_TOKEN: ${{ github.token }}\n"
                   "        run: |\n          gh issue list\n")
        found = self.mutate(anchor, planted + anchor, "latest-tools.yml")
        self.assertReported(found, "the job's token handed over by name")
        anchor = "          NOTES: ${{ needs.notes.outputs.notes }}\n"
        found = self.mutate(anchor, anchor + "          TOKEN: ${{ github.token }}\n", "release.yml")
        self.assertReported(found, "the job's token handed over by name")

    def test_a_missing_guard(self):
        found = self.mutate("    if: vars.CODEX_REVIEW == 'true' && ", "    if: ")
        self.assertReported(found, "holds a secret without the guard")
        found = self.mutate(" && github.event.pull_request.head.repo.full_name == github.repository", "")
        self.assertReported(found, "holds a secret without the guard")
        found = self.mutate("    if: vars.CODEX_REVIEW == 'true' && ", "    if: always() || ")
        self.assertReported(found, "holds a secret without the guard")

    def test_a_guard_without_either_dependabot_clause(self):
        for clause in ("github.actor != 'dependabot[bot]'",
                       "github.event.pull_request.user.login != 'dependabot[bot]'"):
            with self.subTest(clause=clause):
                self.assertReported(self.mutate(" && " + clause, ""), "lacks the Dependabot clause " + clause)

    def test_a_write_permission_in_the_review_job(self):
        found = self.mutate("    permissions:\n      contents: read\n    outputs:",
                            "    permissions:\n      contents: write\n    outputs:")
        self.assertReported(found, "its permissions must be only contents: read")
        for top in ("permissions:\n  contents: write\n", "permissions:\n  contents: read\n  issues: read\n",
                    "permissions: read-all\n"):
            with self.subTest(top=top):
                found = self.mutate("permissions:\n  contents: read\n\njobs:", top + "\njobs:")
                self.assertReported(found, "top-level permissions must be only contents: read")

    def test_a_write_permission_in_a_job_without_a_secret(self):
        found = self.mutate("  test:\n    name:", "  test:\n    permissions: write-all\n    name:", "ci.yml")
        self.assertReported(found, "job test's permissions 'write-all' are outside the allowlist")
        found = self.mutate("  validate:\n    name:", "  validate:\n    permissions:\n      pull-requests: write\n"
                            "    name:", "ci.yml")
        self.assertReported(found, "job validate's permissions {'pull-requests': 'write'} are outside the allowlist")
        found = self.mutate("      pull-requests: write\n", "      pull-requests: write\n      contents: write\n")
        self.assertReported(found, "job comment's permissions")

    def test_a_write_permission_outside_the_allowlist(self):
        """Only the listed jobs hold more than contents: read, each exactly what the list grants it."""
        cases = (
            ("latest-tools.yml", "  check:\n    name:", "  check:\n    permissions:\n      issues: write\n    name:",
             "job check's permissions"),
            ("latest-tools.yml", "      issues: write\n", "      issues: write\n      contents: write\n",
             "job report's permissions"),
            ("release.yml", "  notes:\n    name:", "  notes:\n    permissions:\n      contents: write\n    name:",
             "job notes's permissions"),
            ("release.yml", "      contents: write\n", "      contents: write\n      actions: write\n",
             "job release's permissions"),
            ("welcome.yml", "      issues: write\n", "      issues: write\n      pull-requests: write\n",
             "job issue's permissions"),
            ("welcome.yml", "      pull-requests: write\n", "      pull-requests: write\n      issues: write\n",
             "job pull-request's permissions"),
            ("labels.yml", "      issues: write\n", "      issues: write\n      contents: write\n",
             "job labels's permissions"),
            ("scorecard.yml", "      security-events: write\n", "      security-events: write\n      id-token: write\n",
             "job analysis's permissions"),
            ("scorecard.yml", "  visibility:\n    name:", "  visibility:\n    permissions:\n      security-events: "
             "write\n    name:", "job visibility's permissions"),
            ("codeql.yml", "      security-events: write\n      contents: read\n",
             "      security-events: write\n      contents: write\n", "job analyze's permissions"),
        )
        for workflow, old, new, fragment in cases:
            with self.subTest(workflow=workflow, fragment=fragment):
                self.assertReported(self.mutate(old, new, workflow), fragment + " ")

    def test_the_comment_job_may_only_post(self):
        anchor = "      # actions/github-script "
        checkout = ("      - name: Check out\n        uses: %s\n        with:\n          persist-credentials: false\n"
                    % self.pin("actions/checkout"))
        script = "      - name: Look around\n        run: |\n          ls\n"
        for label, step in (("a checkout", checkout), ("a run: step", script)):
            with self.subTest(step=label):
                self.assertReported(self.mutate(anchor, step + anchor),
                                    "job comment may hold ['pull-requests'] only with no run: step")

    def test_a_writer_that_runs_code_or_another_action(self):
        run = "      - name: Look around\n        run: |\n          ls\n"
        for workflow, job, anchor in (("release.yml", "release", "      # actions/github-script "),
                                      ("latest-tools.yml", "report", "      # actions/github-script "),
                                      ("labels.yml", "labels", "      # actions/github-script "),
                                      ("scorecard.yml", "analysis", "      # ossf/scorecard-action "),
                                      ("codeql.yml", "analyze", "      # github/codeql-action v")):
            with self.subTest(workflow=workflow, step="a run: step"):
                text = self.workflow(workflow)
                last = text.rindex(anchor)
                found = problems(workflow, text[:last] + run + text[last:], support.ROOT)
                self.assertReported(found, "job %s may hold" % job)
        # Appended to the file, the step joins the last job's steps.
        for workflow, job, action in (("release.yml", "release", "actions/checkout"),
                                      ("scorecard.yml", "analysis", "actions/github-script"),
                                      ("codeql.yml", "analyze", "actions/github-script")):
            with self.subTest(workflow=workflow, step=action):
                text = self.workflow(workflow).rstrip("\n") + "\n" + self.step(action, workflow)
                self.assertReported(problems(workflow, text, support.ROOT), "job %s may hold" % job)

    def test_a_job_that_brings_code_these_rules_never_read(self):
        """A reusable workflow, the secrets handed to it, a container or a service image: each runs code that no rule
        here reads. A reusable workflow's job has no steps, so every step rule passes it."""
        reusable = ("\n  greet:\n    # octo-org/shared v1.0.0\n    uses: octo-org/shared/.github/workflows/greet.yml@%s\n"
                    % ("0" * 40))
        runner = "    runs-on: ubuntu-24.04\n"
        for key, workflow, new in (("uses", "welcome.yml", None),
                                   ("secrets", "welcome.yml", runner + "    secrets: inherit\n"),
                                   ("container", "latest-tools.yml", runner + "    container:\n      image: node:24\n"),
                                   ("services", "ci.yml", runner + "    services:\n      cache:\n        image: redis:7\n")):
            with self.subTest(key=key, workflow=workflow):
                if new is None:
                    found = problems(workflow, self.workflow(workflow).rstrip("\n") + "\n" + reusable, support.ROOT)
                else:
                    found = self.mutate(runner, new, workflow)
                self.assertReported(found, "has a %s: key" % key)

    def test_a_job_off_a_github_hosted_ubuntu_runner(self):
        for runner in ("self-hosted", "[self-hosted, linux]", "${{ matrix.runner }}", "windows-2025", "macos-15"):
            with self.subTest(runner=runner):
                found = self.mutate("    runs-on: ubuntu-24.04\n", "    runs-on: %s\n" % runner, "ci.yml")
                self.assertReported(found, "job test runs on ")
                self.assertReported(found, "not on a GitHub-hosted ubuntu- runner")

    def test_a_writer_s_script_that_runs_a_command_loads_code_or_reaches_the_network(self):
        calls = ('await exec.exec("ls");', 'require("child_process").execSync("ls");', 'await import("node:fs");',
                 'eval("1");', 'new Function("return 1")();', 'await fetch("https://example.com");')
        for workflow, job in (("release.yml", "release"), ("latest-tools.yml", "report"), ("welcome.yml", "issue"),
                              ("labels.yml", "labels"), ("codex-review.yml", "comment")):
            for call in calls:
                with self.subTest(workflow=workflow, call=call):
                    found = self.mutate("          script: |\n", "          script: |\n            %s\n" % call,
                                        workflow)
                    self.assertReported(found, "job %s's script at steps.0 calls " % job)

    def test_a_pull_request_target_job_that_checks_out_or_runs(self):
        """Even a job with no write permission: under pull_request_target it runs with the repository's secrets
        and caches, so checking out or running the pull request's code is never allowed there."""
        job = ("\n  look:\n    runs-on: ubuntu-24.04\n    steps:\n%s")
        checkout = ("      # actions/checkout v1.0.0\n      - name: Check out\n        uses: %s\n        with:\n"
                    "          persist-credentials: false\n" % self.pin("actions/checkout", "ci.yml"))
        run = "      - name: Run it\n        run: |\n          make\n"
        setup = ("      # actions/setup-python v1.0.0\n      - name: Set up\n        uses: %s\n"
                 % self.pin("actions/setup-python", "ci.yml"))
        for label, steps in (("a checkout", checkout), ("a run: step", run), ("another action", setup)):
            with self.subTest(step=label):
                text = self.workflow("welcome.yml").rstrip("\n") + "\n" + job % steps
                self.assertReported(problems("welcome.yml", text, support.ROOT),
                                    "job look runs on pull_request_target")
        anchor = "      # actions/github-script v"
        text = self.workflow("welcome.yml")
        last = text.rindex(anchor)
        found = problems("welcome.yml", text[:last] + checkout + text[last:], support.ROOT)
        self.assertReported(found, "job pull-request runs on pull_request_target")

    def test_a_checkout_that_keeps_its_credentials(self):
        self.assertReported(self.mutate("          persist-credentials: false\n", ""),
                            "checkout without persist-credentials: false")
        for workflow in ("release.yml", "latest-tools.yml", "scorecard.yml", "codeql.yml"):
            with self.subTest(workflow=workflow):
                found = self.mutate("persist-credentials: false\n", "persist-credentials: true\n", workflow)
                self.assertReported(found, "checkout without persist-credentials: false")

    def test_a_pull_request_text_anywhere(self):
        for field in ("github.event.pull_request.title", "github.event.pull_request.body",
                      "github.event.head_commit.message", "github.head_ref"):
            with self.subTest(field=field):
                found = self.mutate("      - name: Review with Codex\n",
                                    "      - name: Review ${{ %s }}\n" % field)
                self.assertReported(found, "an attacker-controlled event field")
        for field in ("github.event.issue.title", "github.event.pull_request.body"):
            with self.subTest(workflow="welcome.yml", field=field):
                found = self.mutate("      - name: Welcome the author of a first issue\n",
                                    "      - name: Welcome ${{ %s }}\n" % field, "welcome.yml")
                self.assertReported(found, "an attacker-controlled event field")

    def test_an_expression_inside_a_script_or_run_body(self):
        self.assertReported(self.mutate("              body: process.env.REVIEW,\n",
                                        "              body: '${{ needs.review.outputs.final-message }}',\n"),
                            "an expression inside a script: body")
        found = self.mutate("      - name: Review with Codex\n",
                            "      - name: Show the number\n        run: |\n"
                            "          echo ${{ github.event.pull_request.number }}\n"
                            "      - name: Review with Codex\n")
        self.assertReported(found, "an expression inside a run: body")
        self.assertReported(self.mutate('python3 tools/release_notes.py "$TAG"',
                                        "python3 tools/release_notes.py ${{ github.ref_name }}", "release.yml"),
                            "an expression inside a run: body")
        self.assertReported(self.mutate("body: process.env.NOTES", "body: `${{ needs.notes.outputs.notes }}`",
                                        "release.yml"),
                            "an expression inside a script: body")

    def test_the_review_action_inputs(self):
        self.assertReported(self.mutate("          prompt-file: .github/codex/review-prompt.md\n",
                                        "          prompt: Review this pull request\n"),
                            "must read its prompt only from")
        self.assertReported(self.mutate("permission-profile: \":read-only\"", "permission-profile: \":workspace\""),
                            "permission-profile :read-only")
        self.assertReported(self.mutate("safety-strategy: drop-sudo", "safety-strategy: unsafe"),
                            "safety-strategy drop-sudo")

    def test_the_review_action_takes_only_its_allowlisted_inputs(self):
        for key, value in (("codex-args", "\"--full-auto\""), ("allow-users", "\"*\""), ("allow-bots", "\"true\""),
                           ("model", "example-model-1"), ("working-directory", "src")):
            with self.subTest(input=key):
                found = self.mutate("          safety-strategy: drop-sudo\n",
                                    "          safety-strategy: drop-sudo\n          %s: %s\n" % (key, value))
                self.assertReported(found, "inputs outside its allowlist: " + key)

    def test_the_codex_cli_is_pinned(self):
        pinned = "          codex-version: \"%s\"\n" % CODEX_CLI
        for label, new in (("absent", ""), ("older", pinned.replace(CODEX_CLI, "0.137.0")),
                           ("floating", "          codex-version: latest\n")):
            with self.subTest(version=label):
                self.assertReported(self.mutate(pinned, new), "must pin codex-version to " + CODEX_CLI)

    def test_the_review_action_is_the_last_step(self):
        found = self.mutate("          safety-strategy: drop-sudo\n",
                            "          safety-strategy: drop-sudo\n"
                            "      - name: After\n        run: |\n          true\n")
        self.assertReported(found, "is not the last step")

    def test_an_action_not_pinned_by_sha(self):
        for pin in (self.pin("openai/codex-action"), self.pin("actions/github-script")):
            with self.subTest(pin=pin):
                found = self.mutate(pin, pin.split("@")[0] + "@v1")
                self.assertReported(found, "action not pinned by a commit SHA")
        for workflow, action in (("scorecard.yml", "ossf/scorecard-action"),
                                 ("codeql.yml", "github/codeql-action/analyze"),
                                 ("welcome.yml", "actions/github-script")):
            with self.subTest(workflow=workflow, action=action):
                pin = self.pin(action, workflow)
                self.assertReported(self.mutate(pin, action + "@v4", workflow), "action not pinned by a commit SHA")

    def test_an_action_without_its_release_tag_in_a_comment(self):
        for workflow, action in (("welcome.yml", "actions/github-script"), ("scorecard.yml", "ossf/scorecard-action"),
                                 ("codeql.yml", "github/codeql-action"), ("ci.yml", "actions/setup-python"),
                                 ("codex-review.yml", "openai/codex-action")):
            with self.subTest(workflow=workflow, action=action):
                comment = self.tag_comment(action, workflow)
                for label, new in (("removed", "\n"), ("another action's", "\n      # actions/cache v4.0.0\n"),
                                   ("no tag", "\n      # %s, pinned\n" % action)):
                    with self.subTest(comment=label):
                        self.assertReported(self.mutate(comment, new, workflow),
                                            "action %s has no comment above it with its release tag" % action)

    def test_an_unresolved_pin(self):
        pin = self.pin("openai/codex-action")
        self.assertReported(self.mutate(pin, pin.split("@")[0] + "@<" + "pin: codex-action>"), "an unresolved")

    def test_a_workflow_outside_the_subset(self):
        self.assertReported(self.mutate("      - opened\n", "      - opened # first\n"), "outside the YAML subset")
        self.assertReported(self.mutate("  workflow_dispatch:\n", "  workflow_dispatch: {}\n", "labels.yml"),
                            "outside the YAML subset")


class TheRulesBiteAfterADependabotBump(TheRulesBite):
    """Every case above, run on the workflows as a Dependabot pull request leaves them."""

    def workflow(self, name):
        return bumped(read_workflow(name))

    def test_the_bumped_workflows_are_safe(self):
        for name in sorted(os.listdir(WORKFLOWS)):
            with self.subTest(workflow=name):
                text = self.workflow(name)
                self.assertNotEqual(text, read_workflow(name))
                self.assertEqual(problems(name, text, support.ROOT), [])


class TheMaintenanceFiles(unittest.TestCase):
    def test_dependabot_moves_the_action_pins_once_a_month_in_one_pull_request(self):
        doc = parse(support.read(DEPENDABOT_CONFIG))
        self.assertEqual(doc["version"], "2")
        self.assertEqual(len(doc["updates"]), 1)
        update = doc["updates"][0]
        self.assertEqual((update["package-ecosystem"], update["directory"]), ("github-actions", "/"))
        self.assertEqual(update["schedule"], {"interval": "monthly"})
        self.assertEqual(list(update["groups"].values()), [{"patterns": ["*"]}])
        self.assertGreaterEqual(int(update["cooldown"]["default-days"]), 1)

    def test_every_issue_starts_from_a_template(self):
        doc = parse(support.read(ISSUE_CONFIG))
        self.assertEqual(doc.get("blank_issues_enabled"), "false")
        self.assertLessEqual(set(doc), {"blank_issues_enabled", "contact_links"})
        templates = [name for name in os.listdir(os.path.dirname(ISSUE_CONFIG)) if name.endswith(".md")]
        self.assertTrue(templates)

    def test_questions_and_vulnerabilities_have_a_route_off_the_issue_list(self):
        self.assertEqual(contact_problems(parse(support.read(ISSUE_CONFIG))), [])

    def test_a_link_without_its_about_off_the_repository_or_missing_is_caught(self):
        text = support.read(ISSUE_CONFIG)
        about = re.search(r"\n    about: [^\n]*", text).group(0)
        url = re.search(r"url: (\S+)/discussions", text).group(1)
        security = re.search(r"\n  - name: [^\n]*\n    url: \S+/security/advisories/new\n    about: [^\n]*",
                             text).group(0)
        for planted, expected in ((text.replace(about, "", 1), "not exactly a name, a url and an about"),
                                  (text.replace(url, "https://example.com/project", 1), "is not on this repository"),
                                  (text.replace(security, "", 1), "no link to /security/advisories/new")):
            with self.subTest(expected=expected):
                self.assertNotEqual(planted, text)
                found = contact_problems(parse(planted))
                self.assertTrue(any(expected in problem for problem in found), found)


if __name__ == "__main__":
    unittest.main()
