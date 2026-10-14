"""Every install route has its acceptance steps.

Each route of docs/install.md's table has a section of docs/acceptance.md whose Install step carries that row's one
line: each code span of the line, a chain joined by `&&` taken command by command, stands whole as a code span of the
step, in the line's order. Every route's section has a Versions, an Install, a Use and a Report step. The table of what
each route does with a private repository has one row per route, in install.md's order. No status in install.md
differs from STATUSES: a status changes only after its acceptance steps pass, and then it changes here as well as in
tests/test_readme.py. Each check is a function that returns what it found, and each has a test that plants the
mutation it exists to catch.
"""
import os
import re
import unittest

from support import ROOT, read

DOCS = os.path.join(ROOT, "docs")
ACCEPTANCE = os.path.join(DOCS, "acceptance.md")
INSTALL = os.path.join(DOCS, "install.md")

ROUTES_HEADER = "| Harness | One line | Status |"
PRIVATE_HEADER = "| Route | Reaches a private repository? |"
# Every route's status as it stands after the acceptance run of 2026-10-13. A run that passes changes its route's line
# here, in install.md and in tests/test_readme.py together.
STATUSES = (
    ("Claude Code", "tested on 2.1.296, 2026-10-13 (marketplace; `--plugin-dir` tested earlier)"),
    ("Codex", "tested on 0.162.1, 2026-10-13"),
    ("Gemini CLI", "installs and removes cleanly from a clone (0.63.0, 2026-10-13)"),
    ("Copilot CLI", "documented"),
    ("GitHub CLI", "documented"),
    ("Cursor", "documented"),
    ("OpenCode", "tested on 1.19.0, 2026-10-13"),
    ("claude.ai", "tested on 2026-10-13"),
    ("Antigravity", "tested on 2.23.0, 2026-10-13"),
)
# The steps every route's section has. The Codex section calls its use step "A prompt".
REQUIRED_STEPS = (("Versions",), ("Install",), ("Use", "A prompt"), ("Report",))
STEP = re.compile(r"^\d+\. \*\*(.+?)\.\*\*")
ROUTE_HEADING = re.compile(r"^## \d+\. (.+)$")


def table_rows(text, header):
    """The rows of the Markdown table whose header row starts with `header`, header and rule left out, each a list of
    stripped cells; None when there is no such table."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith(header)), None)
    if start is None:
        return None
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def route_sections(text):
    """{name: body} of each `## <n>. <title>` section, the name being the title up to its first colon; a heading
    inside fenced code is no heading, and a body runs to the next `## ` heading."""
    sections, name, fenced = {}, None, False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        heading = None if fenced else ROUTE_HEADING.match(line)
        if heading:
            name = heading.group(1).split(":", 1)[0].strip()
            sections[name] = []
        elif not fenced and line.startswith("## "):
            name = None
        elif name is not None:
            sections[name].append(line)
    return {key: "\n".join(lines) for key, lines in sections.items()}


def steps(body):
    """{label: text} of a section's numbered steps, `N. **Label.** …`; a step runs to the next one or the end."""
    found, label = {}, None
    for line in body.split("\n"):
        match = STEP.match(line)
        if match:
            label = match.group(1)
            found[label] = []
        if label is not None:
            found[label].append(line)
    return {key: "\n".join(lines) for key, lines in found.items()}


def code_spans(text):
    return re.findall(r"`([^`]+)`", text)


def install_rows(install):
    return table_rows(install, ROUTES_HEADER) or []


def line_problems(acceptance, install):
    """Each route of install.md whose section is missing, has no Install step, or whose Install step does not carry
    every command of the route's one line, whole and in order."""
    sections, problems = route_sections(acceptance), []
    rows = install_rows(install)
    if not rows:
        return ["install.md has no table of routes"]
    for harness, line in ((row[0], row[1]) for row in rows):
        if harness not in sections:
            problems.append("%s: no section in acceptance.md" % harness)
            continue
        step = steps(sections[harness]).get("Install")
        if step is None:
            problems.append("%s: no Install step" % harness)
            continue
        commands = [command.strip() for span in code_spans(line) for command in span.split(" && ")]
        if not commands:
            problems.append("%s: no command in its install.md line" % harness)
        spans, at = code_spans(step), 0
        for command in commands:
            if command not in spans[at:]:
                problems.append("%s: the Install step does not carry %r in order" % (harness, command))
                break
            at = spans.index(command, at) + 1
    return problems


def steps_problems(acceptance, install):
    """Each step of REQUIRED_STEPS missing from a route's section."""
    sections, problems = route_sections(acceptance), []
    for harness in (row[0] for row in install_rows(install)):
        labels = steps(sections.get(harness, "")).keys()
        for names in REQUIRED_STEPS:
            if not any(name in labels for name in names):
                problems.append("%s: no %s step" % (harness, " or ".join(names)))
    return problems


def status_problems(install):
    """Each route whose status in install.md is not its status in STATUSES, and each route added or dropped."""
    found = [(row[0], row[2] if len(row) > 2 else "") for row in install_rows(install)]
    if [harness for harness, _ in found] != [harness for harness, _ in STATUSES]:
        return ["the routes are %r, expected %r" % ([h for h, _ in found], [h for h, _ in STATUSES])]
    return ["%s: %r, expected %r" % (harness, status, expected)
            for (harness, status), (_, expected) in zip(found, STATUSES) if status != expected]


def private_table_problems(acceptance, install):
    """What keeps the private-repository table from having one full row per route, in install.md's order."""
    rows = table_rows(acceptance, PRIVATE_HEADER)
    if rows is None:
        return ["no table headed %r" % PRIVATE_HEADER]
    expected = [row[0] for row in install_rows(install)]
    problems = []
    if [row[0] for row in rows] != expected:
        problems.append("the rows are %r, expected %r" % ([row[0] for row in rows], expected))
    problems += ["%s: an empty cell" % row[0] for row in rows if len(row) != 3 or not all(row)]
    return problems


def in_section(text, harness, old, new):
    """`text` with the first `old` inside the section of `harness` replaced by `new`; `old` must be there."""
    body = route_sections(text)[harness]
    assert old in body, (harness, old)
    return text.replace(body, body.replace(old, new, 1), 1)


class AcceptanceSteps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = read(ACCEPTANCE)
        cls.install = read(INSTALL)

    def assertCaught(self, found, expected):
        self.assertTrue(any(expected in problem for problem in found), (expected, found))

    def test_every_route_has_a_section_whose_install_step_carries_its_line(self):
        self.assertEqual(len(install_rows(self.install)), len(STATUSES))
        self.assertEqual(line_problems(self.acceptance, self.install), [])

    def test_a_missing_section_a_changed_command_or_a_reordered_chain_is_caught(self):
        install_step = re.search(r"(?m)^2\. \*\*Install\.\*\* Run (`[^`]+`), then (`[^`]+`)", self.acceptance)
        self.assertIsNotNone(install_step)
        swapped = "2. **Install.** Run %s, then %s" % (install_step.group(2), install_step.group(1))
        for name, acceptance, install, expected in (
                ("no section", self.acceptance.replace("\n## 9. OpenCode\n", "\n## 9. Open Code\n", 1),
                 self.install, "OpenCode: no section"),
                ("no Install step", in_section(self.acceptance, "Cursor", "**Install.**", "**Set up.**"),
                 self.install, "Cursor: no Install step"),
                ("a flag added", in_section(self.acceptance, "Gemini CLI", " --path skills/", " --consent --path skills/"),
                 self.install, "Gemini CLI: the Install step does not carry"),
                ("the line changed", self.acceptance, self.install.replace(" -a opencode`", " -a opencode -y`", 1),
                 "OpenCode: the Install step does not carry"),
                ("a chain reordered", self.acceptance.replace(install_step.group(0), swapped, 1), self.install,
                 "Claude Code: the Install step does not carry"),
                ("a command dropped", in_section(self.acceptance, "claude.ai", "(`zip -r", "(zip -r"), self.install,
                 "claude.ai: the Install step does not carry")):
            with self.subTest(plant=name):
                self.assertNotEqual((acceptance, install), (self.acceptance, self.install))
                self.assertCaught(line_problems(acceptance, install), expected)

    def test_every_route_section_has_its_versions_install_use_and_report_steps(self):
        self.assertEqual(steps_problems(self.acceptance, self.install), [])

    def test_a_section_without_one_of_those_steps_is_caught(self):
        for harness, old, new, expected in (("Copilot CLI", "**Versions.**", "**Before.**", "no Versions step"),
                                            ("GitHub CLI", "**Install.**", "**Set up.**", "no Install step"),
                                            ("Cursor", "**Use.**", "**Try it.**", "no Use or A prompt step"),
                                            ("Codex", "**A prompt.**", "**Ask.**", "no Use or A prompt step"),
                                            ("claude.ai", "**Report.**", "**Close.**", "no Report step")):
            with self.subTest(harness=harness, step=old):
                planted = in_section(self.acceptance, harness, old, new)
                self.assertCaught(steps_problems(planted, self.install), "%s: %s" % (harness, expected))

    def test_no_status_in_install_md_has_changed(self):
        self.assertEqual(status_problems(self.install), [])

    def test_a_changed_added_or_dropped_status_is_caught(self):
        gemini = next(line for line in self.install.split("\n") if line.startswith("| Gemini CLI |"))
        cursor = next(line for line in self.install.split("\n") if line.startswith("| Cursor |"))
        for name, planted, expected in (
                ("tested", self.install.replace(gemini, gemini.replace("| installs and removes cleanly from a clone "
                                                                       "(0.63.0, 2026-10-13) |",
                                                                       "| tested on 0.63.0, 2026-10-13 |")),
                 "Gemini CLI"),
                ("documented tested", self.install.replace(cursor, cursor.replace("| documented |",
                                                                                  "| tested on 1.0, 2026-01-01 |")),
                 "Cursor"),
                ("narrowed", self.install.replace(" (marketplace; `--plugin-dir` tested earlier)", "", 1), "Claude Code"),
                ("another version", self.install.replace("tested on 0.162.1, 2026-10-13",
                                                         "tested on 0.163.0, 2026-10-13", 1), "Codex"),
                ("dropped", self.install.replace(cursor + "\n", "", 1), "the routes are")):
            with self.subTest(plant=name):
                self.assertNotEqual(planted, self.install)
                self.assertCaught(status_problems(planted), expected)

    def test_the_private_repository_table_has_one_full_row_per_route_in_order(self):
        self.assertEqual(private_table_problems(self.acceptance, self.install), [])

    def test_a_route_missing_out_of_order_or_empty_in_that_table_is_caught(self):
        rows = {row[0]: next(line for line in self.acceptance.split("\n") if line.startswith("| %s |" % row[0]))
                for row in table_rows(self.acceptance, PRIVATE_HEADER)}
        cursor, opencode = rows["Cursor"], rows["OpenCode"]
        for name, planted, expected in (
                ("missing", self.acceptance.replace(opencode + "\n", "", 1), "the rows are"),
                ("out of order", self.acceptance.replace(cursor + "\n" + opencode, opencode + "\n" + cursor, 1),
                 "the rows are"),
                ("empty", self.acceptance.replace(opencode, "| OpenCode |  | the line |", 1), "OpenCode: an empty cell"),
                ("no table", self.acceptance.replace(PRIVATE_HEADER, "| Route | Private? |", 1), "no table headed")):
            with self.subTest(plant=name):
                self.assertNotEqual(planted, self.acceptance)
                self.assertCaught(private_table_problems(planted, self.install), expected)


if __name__ == "__main__":
    unittest.main()
