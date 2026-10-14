#!/usr/bin/env python3
"""check_skill.py: the skill's self-check, run by the people who change the skill (an agent using the skill never
runs it, so it is not installed with it).

Usage: python3 tools/check_skill.py [--skill <skill dir>] [--only S16,S17] [--json]
The default --skill is the only folder under ../skills/ (beside this tools/ folder) that holds a SKILL.md.
Exit: 0 clean; 1 findings; 2 usage.

Output has the linter's shape: one line per finding, `S16 ERROR line 12: references/x.md: <message>` (no `line N`
for a finding about a whole file), then `errors: N, warnings: 0, allowed: 0`. --json prints {skill, errors,
warnings, allowed, findings [{rule, level, line, message, match, reason, file}]}.

Rules:
  S04 every backticked path in SKILL.md and references/*.md that starts with references/, templates/, scripts/ or
      packs/ exists.
  S06 the frozen texts: SKILL.md's two question blocks, the `helper seat: ` prefix, the linter command, the
      helper seats' no-subagents fallback and the autonomy paragraph's two phrase lists the linter parses; the
      master-prompt template's headings, {SEATS_BLOCK} slot, fallback paragraph, thirteen run-rule labels, RS5, RS8 and RS12 lines, wait-rule label and
      `Goal: {GOAL}`; the decisions template's framing line, D1 and D2 rows, two frozen headers and allowance form;
      the quick template's identity line, short plateau, RS1 and RS13 labels, push line, unattended line and
      decisions skeleton.
  S07 SKILL.md at most 200 lines, and each file's words under its ceiling (its count when set, plus 10%).
  S08 SKILL.md frontmatter: spec keys only; `name` equals the folder and meets the spec rule; the frozen
      description (at most 400 characters, ASCII, no `<` or `>`); `license: Apache-2.0`; `compatibility` at most
      500 characters.
  S09 no home path naming a person anywhere in the folder.
  S13 every pack (packs/*.md, TEMPLATE.md included, README.md aside): the pack headings in order, and each §3 block
      with one When, one Where and one Adapt line, exactly one ```text fence, and a When that, its <…> placeholders
      removed, opens on no size, run length or blanket word.
  S14 no `<!-- verbatim`, `<!-- /verbatim` or `<!-- lint-allow` in SKILL.md, references/**, templates/** or packs/**.
  S15 V1, V2, the review sentence and the delegation sentence verbatim in references/methods.md §10; the fused
      one-sentence form nowhere.
  S16 no model family, version or id anywhere in the folder (LICENSE aside) but a placeholder, the harness files
      included; no harness token outside the harness files (the Claude Code and Codex guides and
      agents/openai.yaml). Host names are blanked before the model patterns run.
  S17 self-containment: (a) every skill path a Markdown file names (a backticked token or link target starting with
      references/, templates/, scripts/, packs/ or agents/, or a `<this skill's directory>/` path anywhere in a code
      span) resolves, a <…> or {…} segment matching at least one file; (b) no Markdown file outside the harness files
      names `../` or an absolute path; (c) the scripts import only the standard library and modules of the folder;
      (d) a URL only in a guide's §5 Sources and in NOTICE.
  S18 the frontmatter `name`, as a word in any case, in no file but that `name:` line and agents/openai.yaml's
      `display_name:` line whose whole value is that name.
  S19 each guide (references/harness-*.md; the generic one required): the five headings in order, the required block
      ids, each block one ```text fence; every line of §1–§4 outside fences ends with a source key, and every key is
      in §5 with a URL and a date; the fences use only the known slots and fragments.

The frozen texts the linter checks prompts against (run-rule labels, the fallback paragraph, the headers, V1, V2)
are read from the skill's own scripts/lint_prompt.py, so the templates are held to what the linter expects; a rule
that needs it reports a finding when that file is missing or does not import.

Standard library only; runs on python3 3.9 or newer.
"""
import argparse
import ast
import glob
import importlib.util
import json
import os
import re
import sys
import sysconfig

RULES = ("S04", "S06", "S07", "S08", "S09", "S13", "S14", "S15", "S16", "S17", "S18", "S19")
NEEDS_LINTER = ("S06", "S15", "S19")

DESCRIPTION = (
    "Turns a task into a master prompt that a fresh agent session runs alone: interviews for what it cannot find out, "
    "designs the method and the bar, writes the prompt and reviews it. Use for a master, system or handoff prompt, a "
    "prompt for a cloud or unattended run, completing or auditing a draft prompt, or a builder/critic loop on an "
    "existing artifact. Not for doing the task now or a one-line prompt.")
FRONTMATTER_KEYS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# ---------------------------------------------------------------- S06: the frozen texts of SKILL.md and the templates
QUESTION_HARNESS = (
    "**Q<n>. Where will the run execute?**\n"
    "Why it matters: the launch, and how each seat gets its model, depend on it.\n"
    "Recommended: this harness, the one this session runs in.\n"
    "Options: (a) recommended · (b) another harness: name it")
QUESTION_AUTONOMY = (
    "**Q<n>. Will you watch this run, or start it and leave it?**\n"
    "Why it matters: a watched run can ask you; an unwatched one decides alone and launches differently.\n"
    "Recommended: <the option> — <one line from what you know of the run>.\n"
    "Options: (a) I watch it · (b) I leave it, started headless on this machine · (c) I leave it, in a cloud session "
    "· (d) I leave it, started another way")
UNATTENDED_PHRASES = ["start it and walk away", "leave it running", "overnight", "while I sleep", "I won't be around",
                      "check it in the morning", "unattended"]
ATTENDED_PHRASES = ["I'll watch it", "I'll be here", "step by step with me"]
HELPER_PREFIX = "`helper seat: `"
# SKILL.md § Your own helper seats: what this session does where the harness starts no subagent.
NO_SUBAGENTS = ("- **No subagents.** Where the harness cannot start a subagent, or refuses one, do each seat's work "
                "yourself, in order and from its brief alone: the red team once the frontier is empty; then the cold "
                "read, answered from the prompt file reread from disk and the folder, before you open `decisions.md` "
                "again; then the review against `decisions.md`. Record in § Review that the seats ran in this session, "
                "so the cold read was not cold, and say so in delivery.")
LINT_COMMAND = ('python3 "<this skill\'s directory>/scripts/lint_prompt.py" "<folder>/prompts/<task-id>/master-prompt.md" '
                '--decisions "<folder>/prompts/<task-id>/decisions.md"')
QUICK_PUSH = ("{DISPOSABLE: This machine is discarded when the session ends: commit and push on `{BRANCH}` before the "
              "final report; nothing left only on its disk counts as delivered.}")
QUICK_IDENTITY = "Work alone: dispatch no subagent."
SEATS_SLOT = "{SEATS_BLOCK}"
GOAL_NEEDLE = "Goal: {GOAL}"
RS5_LINE = ("- **A fresh reviewer every round.** Every review, critique and re-review is a new dispatch that has not "
            "seen earlier rounds: never resumed or sent a follow-up, even after an interruption. Never start a reviewer, "
            "critic, judge or cold read as a seat that inherits your conversation.")
RS8_LINE = (
    "- **Long operations run detached.** Anything over ten minutes runs in the background, logging to "
    "`{RUN_DIR}/logs/<name>.log` with a way to tell it finished; check it at intervals while you work, never blocking "
    "a turn on it. {ATTENDED: When a long wait starts, say once that interrupting the session stops every running "
    "seat.}{HEADLESS: This run was launched headless, where a turn that ends ends the run: while a detached operation{ "
    "or a seat} runs, keep the turn going, checking at most ten minutes apart, until it finishes or fails. A message "
    "with no tool call ends the turn: take the next step rather than announce it, offer it or ask about it.}{OTHER: "
    "Nobody is watching and nobody will send another message: a turn that ends with nothing running ends the run. "
    "While a detached operation{ or a seat} runs, end a turn only if its completion will wake you (a task notification "
    "or a scheduled check); otherwise keep it going, checking at most ten minutes apart, until it finishes or fails. A "
    "message with no tool call ends the turn: take the next step rather than announce it, offer it or ask about it.}")
RS12_LINE = ("- **The work leaves the machine as it goes.** This machine is discarded at the end: commit and push on "
             "`{BRANCH}` at each closed piece, records and evidence included — these pushes are authorised in advance; "
             "nothing left only on its disk counts as delivered.")
FRAMING_LINE = ("Framing: size=<quick|standard|deep>; autonomy=<attended|unattended>; harness=<claude-code|codex|generic>; "
                "launch=<interactive|headless|cloud|other>; model=<model id|choose>; effort=<level|default>; "
                "run=<one-session|one-day|multi-session>; machine=<personal|disposable>; seat=<alone|implementer|lead>; "
                "review=<fresh|none>; folder=<absolute path>")
D1_ROW = ("| D1 | Harness | <harness and launch; a model or effort the person named> | <the person's words or answer, "
          "or \"this session's own, accepted\"> | <Stated, Interview or Default accepted> | YYYY-MM-DD | live |")
D2_ROW = ("| D2 | Autonomy | <attended, or unattended and its harness> | <the person's words, quoted, or the answer to "
          "the autonomy question> | <Stated or Interview> | YYYY-MM-DD | live |")
MASTER = "templates/master-prompt.md"
DECISIONS = "templates/decisions.md"
QUICK = "templates/quick-prompt.md"

# ---------------------------------------------------------------- S07: word ceilings (the count when set, plus 10%)
SKILL_MAX_LINES = 200
CEILINGS = {
    "SKILL.md": 2427,                              # 2,207 words of its body
    "references/contracts.md": 1994,               # 1,813
    "references/harness-claude-code.md": 2317,     # 2,107
    "references/harness-codex.md": 1731,           # 1,574
    "references/harness-generic.md": 632,          # 575
    "references/interview.md": 2932,               # 2,666
    "references/method-catalog.md": 2057,          # 1,870
    "references/methods.md": 2973,                 # 2,703
    "references/orchestration.md": 1002,           # 911
    "references/review.md": 1653,                  # 1,503
    "references/writing-rules.md": 1331,           # 1,210
    "templates/decisions.md": 790,                 # 719
    "templates/master-prompt.md": 1911,            # 1,738
    "templates/quick-prompt.md": 701,              # 638
    "packs/README.md": 431,                        # 392
    "packs/TEMPLATE.md": 222,                      # 202
}

# ---------------------------------------------------------------- S09
# A home folder that names a person; built so that this file does not match itself.
HOME_PATH_RES = [re.compile(r"/Us[e]rs/([^/\s`'\"<>]+)/"), re.compile(r"/hom[e]/([^/\s`'\"<>]+)/"),
                 re.compile(r"[A-Za-z]:\\Us[e]rs\\([^\\\s`'\"<>]+)\\")]
PLACEHOLDER_CHARS = set("<>{}$*…")

# ---------------------------------------------------------------- S13: the pack format
PACK_HEADINGS = ("## 1. Facts", "## 2. Default behaviour", "## 3. Include", "## 4. Leave out",
                 "## 5. Failure modes and counters", "## 6. Review checks", "## 7. Sources")
PACK_TITLE_RE = re.compile(r"^# .+: guidance pack$")
SIZE_WHEN_RE = re.compile(r"(quick|standard|deep|size)\b", re.I)
BLANKET_WHEN_RE = re.compile(r"(long[\s-]+run(?:s|ning)?|every\s+run|all\s+runs|any\s+run|always)\b", re.I)
MARKER_RE = re.compile(r"<!--\s*(?:/?verbatim|lint-allow)\b")   # S14
FUSED = "put its output in the report; independent review"       # S15

# ---------------------------------------------------------------- S16: model names and harness tokens
MODEL_PATTERNS = [re.compile(p) for p in (
    r"\bClaude\b(?!\s+Code\b)",
    r"(?i)\b(opus|sonnet|haiku|fable|mythos)\b",
    r"(?i)\bclaude-(\d|instant|opus|sonnet|haiku|fable|mythos)[\w.-]*",
    r"\bGPT[-\s]?\d",
    r"(?i)\bgpt-[\w.]+",
    r"\bo[1-9](-mini|-pro|-preview)?\b",
    r"(?i)\b(davinci|codex-mini|gpt-oss)\b",
    r"\b(Gemini|Gemma|PaLM|Bard)\b",
    r"\b(Llama|LLaMA|Mistral|Mixtral|Codestral|Qwen|DeepSeek|Grok|Kimi|Nemotron)\b",
    r"\bGLM-\d|\bPhi-\d",
)]
HOST_RE = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|ai|dev|app|sh)\b")
MODEL_PLACEHOLDERS = re.compile(r"\{MODEL_ID\}|<model-id>|\[you fill this in:[^\]]*\]")
HARNESS_TOKENS = [re.compile(p) for p in (
    r"\bClaude Code\b",
    r"(?i)\bChatGPT\b",
    r"\b(CLAUDE|CODEX|ANTHROPIC|OPENAI|GEMINI)_[A-Z_]+",
    r"\bclaude\s+(-p\b|--\w|plugin\b|mcp\b|setup-token\b|config\b|resume\b)",
    r"\bcodex\s+(exec\b|e\b|resume\b|plugin\b|login\b|-)",
    r"\bgemini\s+(skills|extensions)\b|\bcopilot\s+plugin\b|\bgh\s+skill\b|\bnpx\s+skills\b",
    r"--(permission-mode|allowed-?tools|allowedTools|disallowed-?[Tt]ools|dangerously-[\w-]+|append-system-prompt[\w-]*"
    r"|max-budget-usd|max-turns|plugin-dir|add-dir|session-id|output-format|effort|ask-for-approval|sandbox|yolo"
    r"|full-auto|output-last-message|skip-git-repo-check|ephemeral|approve-for-me)\b",
    r"\b(model_reasoning_effort|default_subagent_\w+|agents\.max_\w+|agents\.enabled|multi_agent|approval_policy"
    r"|sandbox_mode)\b",
    r"\b(acceptEdits|bypassPermissions|workspace-write|danger-full-access)\b",
    r"\b(Agent|Task) tool\b|\bsubagent_type\b|\bspawn_agent\b|\b(built-in )?Explore (agent|subagent)s?\b"
    r"|\bgeneral-purpose\b|\bBash\(|\bWebFetch\b|\bWebSearch\b|\bTodoWrite\b",
    r"(?<![\w./-])/(model|effort|goal|agents?|plugins?|skills|compact|resume|clear)\b",
    r"\.claude/|\.codex/|~/\.claude|~/\.codex|\bCLAUDE\.md\b|\bGEMINI\.md\b|\bAGENTS\.override\.md\b"
    r"|\.agents/(skills|plugins)|\.claude-plugin|\.codex-plugin|rollout-[\w*]*\.jsonl",
    r"\bCodex\b|\bCopilot\b|\bCursor\b|\bOpenCode\b|\bclaude\.ai\b|\bchatgpt\.com\b",
)]
HARNESS_FILES = ("references/harness-claude-code.md", "references/harness-codex.md", "agents/openai.yaml")
HARNESS_FOLDERS = ()

# ---------------------------------------------------------------- S17
SKILL_PREFIXES = ("references/", "templates/", "scripts/", "packs/", "agents/")
SKILL_DIR_MARK = "<this skill's directory>/"
URL_RE = re.compile(r"https?://")

# ---------------------------------------------------------------- S19: the harness guides
GUIDE_BLOCKS = ("seats-models", "reviewer-facts", "launch-attended", "launch-headless", "launch-cloud")
GUIDE_EXTRA_BLOCKS = {"references/harness-claude-code.md": ("headless-line",)}
REQUIRED_GUIDES = ("references/harness-generic.md",)
GUIDE_SLOTS = ("MODEL_ID", "EFFORT", "RUN_DIR", "FOLDER", "TASK_ID", "SANDBOX", "TIMEOUT",
               "BENCH_ROOT", "SEAT_BUDGET_USD", "SESSION_ID", "PERMISSION_MODE", "ALLOWED_TOOLS", "EXTRA_FLAGS",
               "BENCH_MKDIR", "ADD_DIR")
SOURCE_KEY_RE = re.compile(r"\[([^\[\]]+)\]\.?\s*$")
KEY_ITEM_RE = re.compile(r"^(skill|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)(?:\s+#\S.*)?$")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


class Finding(object):
    def __init__(self, rule, file, line, message, match=None):
        self.rule, self.file, self.line, self.message, self.match = rule, file, line, message, match

    def as_dict(self):
        return {"rule": self.rule, "level": "ERROR", "line": self.line,
                "message": "%s: %s" % (self.file, self.message) if self.file else self.message,
                "match": self.match, "reason": None, "file": self.file}

    def as_text(self):
        where = " line %d" % self.line if self.line is not None else ""
        prefix = "%s: " % self.file if self.file else ""
        return "%s ERROR%s: %s%s" % (self.rule, where, prefix, self.message)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def fence_states(lines):
    """For each line: (inside a fence or on its delimiter, the fence's info string, whether it opens the fence)."""
    out, char, length, info = [], "", 0, ""
    for raw in lines:
        if length:
            out.append((True, info, False))
            stripped = raw.strip()
            if stripped and set(stripped) == {char} and len(stripped) >= length:
                length = 0
            continue
        opened = FENCE_OPEN_RE.match(raw)
        if opened and not (opened.group(1)[0] == "`" and "`" in opened.group(2)):
            char, length, info = opened.group(1)[0], len(opened.group(1)), opened.group(2).strip()
            out.append((True, info, True))
            continue
        out.append((False, "", False))
    return out


def md_sections(lines, level=2):
    """{heading line: (first index, last index exclusive)} for headings of `level`, outside fences."""
    states = fence_states(lines)
    marks = [i for i, raw in enumerate(lines) if not states[i][0] and re.match(r"^#{%d}\s" % level, raw)]
    return {lines[i].rstrip(): (i, marks[k + 1] if k + 1 < len(marks) else len(lines)) for k, i in enumerate(marks)}


def frontmatter(text):
    """({field: value} or None when unclosed, body). Reads plain, quoted and block-scalar values."""
    if not text.startswith("---\n"):
        return {}, text
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        return None, text
    fields, i = {}, 1
    while i < end:
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", lines[i])
        i += 1
        if not match:
            continue
        key, value = match.group(1), match.group(2).rstrip()
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []
            while i < end and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].strip())
                i += 1
            value = ("\n" if value.startswith("|") else " ").join(block).strip()
        elif value.startswith('"'):
            while not re.search(r'(?<!\\)"\s*$', value[1:]) and i < end:
                value += " " + lines[i].strip()
                i += 1
            try:
                value = json.loads(value)
            except ValueError:
                value = value.strip('"')
        elif value.startswith("'"):
            while not (len(value) > 1 and value.endswith("'") and not value.endswith("''") or value.endswith("'''")) and i < end:
                value += " " + lines[i].strip()
                i += 1
            value = value[1:-1].replace("''", "'")
        else:
            while i < end and lines[i].startswith((" ", "\t")) and lines[i].strip():
                value += " " + lines[i].strip()
                i += 1
        fields[key] = value
    return fields, "\n".join(lines[end + 1:])


def load_linter(skill):
    """The skill's own scripts/lint_prompt.py as a module, or None when it is missing or does not import."""
    path = os.path.join(skill, "scripts", "lint_prompt.py")
    if not os.path.isfile(path):
        return None
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # no cache left in the checked skill
    try:
        spec = importlib.util.spec_from_file_location("lint_prompt_of_checked_skill", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (Exception, SystemExit):   # a broken linter is a finding of the skill, never a crash of the check
        return None
    finally:
        sys.dont_write_bytecode = saved


def is_stdlib(name):
    if name in sys.builtin_module_names:
        return True
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return name in names
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return False
    if spec is None or not spec.origin:
        return False
    if spec.origin in ("built-in", "frozen"):
        return True
    stdlib = os.path.realpath(sysconfig.get_paths()["stdlib"])
    origin = os.path.realpath(spec.origin)
    return origin.startswith(stdlib + os.sep) and "site-packages" not in origin and "dist-packages" not in origin


class Checker(object):
    def __init__(self, skill):
        self.skill = skill
        self.findings = []
        self.lp = load_linter(skill)

    def add(self, rule, file, line, message, match=None):
        self.findings.append(Finding(rule, file, line, message, match))

    def path(self, rel):
        return os.path.join(self.skill, *rel.split("/"))

    def exists(self, rel):
        return os.path.exists(self.path(rel))

    def rel(self, path):
        return os.path.relpath(path, self.skill).replace(os.sep, "/")

    def files(self, *patterns):
        found = set()
        for pattern in patterns:
            for path in glob.glob(os.path.join(self.skill, pattern), recursive=True):
                if os.path.isfile(path) and "__pycache__" not in path.split(os.sep) and not path.endswith(".pyc"):
                    found.add(path)
        return sorted(found)

    def all_files(self):
        """Every file of the folder, as relative paths; hidden ones included, caches aside."""
        out = []
        for folder, dirs, names in os.walk(self.skill):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git"))
            for name in sorted(names):
                if not name.endswith(".pyc"):
                    out.append(self.rel(os.path.join(folder, name)))
        return out

    def text_files(self, rels=None):
        """[(relative path, text)] of the folder's files that are text."""
        out = []
        for rel in rels if rels is not None else self.all_files():
            try:
                with open(self.path(rel), encoding="utf-8") as handle:
                    out.append((rel, handle.read()))
            except (OSError, UnicodeDecodeError):
                continue
        return out

    def markdown(self):
        return [rel for rel in self.all_files() if rel.endswith(".md")]

    def skill_name(self):
        if not self.exists("SKILL.md"):
            return None
        fields = frontmatter(read(self.path("SKILL.md")))[0]
        return fields.get("name") if fields else None

    @staticmethod
    def harness_file(rel):
        return rel in HARNESS_FILES or rel.startswith(HARNESS_FOLDERS)

    # ------------------------------------------------------------------ S04
    def s04(self):
        for path in self.files("SKILL.md", "references/*.md"):
            rel = self.rel(path)
            lines = read(path).split("\n")
            states = fence_states(lines)
            for i, raw in enumerate(lines):
                if states[i][0]:
                    continue
                for span in re.findall(r"(`+)(.+?)\1", raw):
                    token = span[1].strip().split()[0] if span[1].strip() else ""
                    if not token.startswith(("references/", "templates/", "scripts/", "packs/")):
                        continue
                    if set(token) & PLACEHOLDER_CHARS - {"*"} or "..." in token:
                        continue
                    token = re.sub(r"(#.*|:\d+(-\d+)?)$", "", token).rstrip(".,;:)")
                    if "*" in token:
                        if not glob.glob(os.path.join(self.skill, token)):
                            self.add("S04", rel, i + 1, "backticked path %r matches no file" % token, token)
                    elif not self.exists(token.rstrip("/")):
                        self.add("S04", rel, i + 1, "backticked path %r does not exist" % token, token)

    # ------------------------------------------------------------------ S06
    def _holds(self, rel, needle, what, flat=False):
        if not self.exists(rel):
            return False
        text = read(self.path(rel))
        found = (self.lp.normalise(needle) in self.lp.normalise(text)) if flat else (needle in text)
        if not found:
            self.add("S06", rel, None, "%s is missing or changed: %r" % (what, needle[:100]), needle[:60])
        return found

    def s06(self):
        lp = self.lp
        for rel in ("SKILL.md", MASTER, DECISIONS, QUICK):
            if not self.exists(rel):
                self.add("S06", rel, None, "missing, so its frozen texts cannot be compared")
        if self.exists("SKILL.md"):
            for needle, what in ((QUESTION_HARNESS, "the harness question block"),
                                 (QUESTION_AUTONOMY, "the autonomy question block"),
                                 (HELPER_PREFIX, "the helper-seat prefix"), (LINT_COMMAND, "the linter command"),
                                 (NO_SUBAGENTS, "the helper seats' no-subagents fallback")):
                self._holds("SKILL.md", needle, what)
            lists = lp.parse_skill_md(read(self.path("SKILL.md")))["autonomy"]
            if lists is None:
                self.add("S06", "SKILL.md", None, "the autonomy paragraph's two English phrase lists cannot be parsed (the "
                         "linter's P34 (e) reads them between %r and the next marker)" % lp.AUTONOMY_LISTS[0][1])
            elif lists != {"unattended": UNATTENDED_PHRASES, "attended": ATTENDED_PHRASES}:
                self.add("S06", "SKILL.md", None, "the autonomy paragraph's phrase lists changed: unattended %s, attended %s"
                         % (lists["unattended"], lists["attended"]))
        if self.exists(MASTER):
            text = read(self.path(MASTER))
            lines = text.split("\n")
            for name in lp.SECTION_NAMES:
                regex = re.compile(lp.HEADING_PREFIX + re.escape(name) + r"\s*$", re.I)
                if not any(regex.match(raw.rstrip()) for raw in lines):
                    self.add("S06", MASTER, None, "the heading `## %s` is missing" % name, name)
            for needle, what in ((SEATS_SLOT, "the {SEATS_BLOCK} slot"),
                                 (lp.FALLBACK_PARAGRAPH, "the fallback paragraph"), (RS5_LINE, "RS5's text"),
                                 (RS8_LINE, "RS8's text"), (RS12_LINE, "RS12's text"),
                                 (lp.WAIT_RULE_LABEL, "the wait-rule label"), (GOAL_NEEDLE, "the goal line")):
                self._holds(MASTER, needle, what)
            for n, label in sorted(lp.RS_LABELS.items()):
                if label not in text:
                    self.add("S06", MASTER, None, "RS%d's label %s is missing" % (n, label), label)
        if self.exists(DECISIONS):
            text = read(self.path(DECISIONS))
            lines = text.split("\n")
            if FRAMING_LINE not in [raw.rstrip() for raw in lines]:
                self.add("S06", DECISIONS, None, "the framing line is missing or changed: %r" % FRAMING_LINE[:80],
                         FRAMING_LINE[:60])
            rows = [lp.table_cells(raw) for raw in lines if lp.TABLE_ROW_RE.match(raw)]
            for row, what in ((D1_ROW, "the D1 row"), (D2_ROW, "the D2 row"), (lp.WORDS_HEADER_LINE, "the person's words "
                              "header"), (lp.GUIDANCE_HEADER_LINE, "the guidance header")):
                if lp.table_cells(row) not in rows:
                    self.add("S06", DECISIONS, None, "%s is missing or changed: `%s`" % (what, row), row[:60])
            for heading in ("## " + lp.WORDS_SECTION, "## " + lp.GUIDANCE_SECTION, "## Launch"):
                if heading not in [raw.rstrip() for raw in lines]:
                    self.add("S06", DECISIONS, None, "the heading `%s` is missing" % heading, heading)
            self._holds(DECISIONS, lp.ALLOWANCE_FORM, "the allowance form")
        if self.exists(QUICK):
            self._quick_template()

    def _quick_template(self):
        lp = self.lp
        text = read(self.path(QUICK))
        for needle, what in ((QUICK_IDENTITY, "the identity line"), (lp.SHORT_PLATEAU, "the short plateau"),
                             (lp.RS_LABELS[1], "RS1's label"), (lp.RS_LABELS[13], "RS13's label"),
                             (lp.WAIT_RULE_LABEL, "the wait-rule label"), (GOAL_NEEDLE, "the goal line")):
            self._holds(QUICK, needle, what)
        self._holds(QUICK, QUICK_PUSH, "the push line a disposable machine keeps (P22)")
        self._holds(QUICK, "{UNATTENDED: %s}" % lp.QUICK_UNATTENDED_LINE, "the line an unattended run keeps (P44)")
        lines = text.split("\n")
        states = fence_states(lines)
        skeleton, i = None, 0
        while i < len(lines):
            if states[i][2]:
                j = i + 1
                while j < len(lines) and states[j][0] and not states[j][2]:
                    j += 1
                body = lines[i + 1:j - 1] if j - 1 > i else []
                if any(raw.startswith("Framing:") for raw in body):
                    skeleton = body
                    break
                i = j
                continue
            i += 1
        if skeleton is None:
            self.add("S06", QUICK, None, "no fenced decisions.md skeleton (a fence holding a `Framing:` line)")
            return
        heads = [raw.rstrip() for raw in skeleton if re.match(r"^##\s", raw)]
        if "## Launch" not in heads:
            self.add("S06", QUICK, None, "the skeleton has no `## Launch`: the launch puts a quick run on its model",
                     "## Launch")
        if FRAMING_LINE not in [raw.rstrip() for raw in skeleton]:
            self.add("S06", QUICK, None, "the skeleton's framing line is not the frozen one", FRAMING_LINE[:60])
        if self.exists(DECISIONS):
            template = read(self.path(DECISIONS)).split("\n")
            tstates = fence_states(template)
            order = iter([raw.rstrip() for k, raw in enumerate(template) if not tstates[k][0] and re.match(r"^##\s", raw)])
            if not all(head in order for head in heads):
                self.add("S06", QUICK, None, "the skeleton's `##` headers %s are not, in order, a subset of %s's"
                         % (", ".join(heads), DECISIONS))

    # ------------------------------------------------------------------ S07
    def s07(self):
        for rel, ceiling in sorted(CEILINGS.items()):
            if not self.exists(rel):
                self.add("S07", rel, None, "missing (it has a word ceiling)")
                continue
            text = read(self.path(rel))
            if rel == "SKILL.md":
                count = len(text.split("\n")) - (1 if text.endswith("\n") else 0)
                if count > SKILL_MAX_LINES:
                    self.add("S07", rel, None, "%d lines, over %d" % (count, SKILL_MAX_LINES))
                text = frontmatter(text)[1]
            words = len(text.split())
            if words > ceiling:
                self.add("S07", rel, None, "%d words, over the ceiling of %d" % (words, ceiling))

    # ------------------------------------------------------------------ S08
    def s08(self):
        rel = "SKILL.md"
        if not self.exists(rel):
            self.add("S08", rel, None, "missing")
            return
        text = read(self.path(rel))
        if not text.startswith("---\n"):
            self.add("S08", rel, 1, "the first line must be `---`")
            return
        fields = frontmatter(text)[0]
        if fields is None:
            self.add("S08", rel, 1, "the frontmatter is never closed with `---`")
            return
        for key in sorted(set(fields) - set(FRONTMATTER_KEYS)):
            self.add("S08", rel, None, "frontmatter key %r is not one of %s" % (key, ", ".join(FRONTMATTER_KEYS)), key)
        name, folder = fields.get("name"), os.path.basename(os.path.normpath(self.skill))
        if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
            self.add("S08", rel, None, "frontmatter name %r does not meet the spec (lowercase letters, digits and single "
                     "hyphens, at most 64 characters)" % (name,))
        elif name != folder:
            self.add("S08", rel, None, "frontmatter name %r is not the folder's name %r" % (name, folder), name)
        description = fields.get("description")
        if not isinstance(description, str):
            self.add("S08", rel, None, "frontmatter has no description")
        else:
            if len(description) > 400:
                self.add("S08", rel, None, "description is %d characters, over 400" % len(description))
            if not all(ord(char) < 128 for char in description) or re.search(r"[<>]", description):
                self.add("S08", rel, None, "description must be ASCII with no `<` or `>`")
            if description != DESCRIPTION:
                k = next((k for k, (a, b) in enumerate(zip(description, DESCRIPTION)) if a != b),
                         min(len(description), len(DESCRIPTION)))
                self.add("S08", rel, None, "description differs from the frozen text at character %d: ...%s..."
                         % (k + 1, description[max(0, k - 20):k + 20]))
        if fields.get("license") != "Apache-2.0":
            self.add("S08", rel, None, "frontmatter license is %r, not 'Apache-2.0'" % fields.get("license"))
        compatibility = fields.get("compatibility")
        if compatibility is not None and (not isinstance(compatibility, str) or len(compatibility) > 500):
            self.add("S08", rel, None, "compatibility is over 500 characters")

    # ------------------------------------------------------------------ S09
    def s09(self):
        for rel, text in self.text_files():
            for i, raw in enumerate(text.split("\n")):
                for regex in HOME_PATH_RES:
                    for m in regex.finditer(raw):
                        if set(m.group(1)) & PLACEHOLDER_CHARS or m.group(1) in (".", ".."):
                            continue
                        self.add("S09", rel, i + 1, "a home path naming a person: write $HOME or a relative path",
                                 m.group(0))

    # ------------------------------------------------------------------ S13
    def s13(self):
        for path in self.files("packs/*.md"):
            rel = self.rel(path)
            if os.path.basename(path) == "README.md":
                continue   # the format's description, not a pack
            lines = read(path).split("\n")
            states = fence_states(lines)
            headings = [raw.rstrip() for i, raw in enumerate(lines) if not states[i][0] and re.match(r"^#{1,2}\s", raw)]
            if not headings or not PACK_TITLE_RE.match(headings[0]) or headings[1:] != list(PACK_HEADINGS):
                self.add("S13", rel, None, "the headings are not the pack format's: `# <Model name>: guidance pack`, then "
                         "%s, in order" % ", ".join("`%s`" % h for h in PACK_HEADINGS))
            span = md_sections(lines).get("## 3. Include")
            if not span:
                continue
            starts = [i for i in range(*span) if not states[i][0] and lines[i].startswith("### ")]
            for k, start in enumerate(starts):
                end = starts[k + 1] if k + 1 < len(starts) else span[1]
                name = lines[start][4:].strip()
                keys = {key: [i for i in range(start + 1, end) if not states[i][0] and lines[i].startswith(key + ":")]
                        for key in ("When", "Where", "Adapt")}
                for key, found in keys.items():
                    if len(found) != 1:
                        self.add("S13", rel, start + 1, "block %r has %d `%s:` lines, not one" % (name, len(found), key),
                                 key)
                fences = [states[i][1] for i in range(start + 1, end) if states[i][2]]
                if fences != ["text"]:
                    self.add("S13", rel, start + 1, "block %r has %d fences (%s), not exactly one ```text fence"
                             % (name, len(fences), ", ".join(repr(f) for f in fences) or "none"))
                if len(keys["When"]) == 1:
                    at = keys["When"][0]
                    when = re.sub(r"<[^<>]*>", "", lines[at][len("When:"):]).strip()
                    found = SIZE_WHEN_RE.match(when) or BLANKET_WHEN_RE.match(when)
                    if found:
                        self.add("S13", rel, at + 1, "block %r goes in on %r: a block goes in on a fact of the task, "
                                 "never a size, a run length or every run" % (name, found.group(0)), found.group(0))

    # ------------------------------------------------------------------ S14
    def s14(self):
        for path in self.files("SKILL.md", "references/**/*", "templates/**/*", "packs/**/*"):
            rel = self.rel(path)
            for i, raw in enumerate(read(path).split("\n")):
                match = MARKER_RE.search(raw)
                if match:
                    self.add("S14", rel, i + 1, "a provenance marker (%r): the delivered prompt holds no HTML comment, so "
                             "the skill teaches none" % match.group(0), match.group(0))

    # ------------------------------------------------------------------ S15
    def s15(self):
        lp = self.lp
        rel = "references/methods.md"
        if not self.exists(rel):
            self.add("S15", rel, None, "missing, so its §10 cannot hold the verification sentences")
        else:
            lines = read(self.path(rel)).split("\n")
            span = next((s for heading, s in md_sections(lines).items() if heading.startswith("## 10.")), None)
            section = lp.normalise("\n".join(lines[span[0]:span[1]])) if span else ""
            for sentence, what in ((lp.V1, "V1"), (lp.V2, "V2"), (lp.REVIEW_SENTENCE, "the review sentence"),
                                   (lp.DELEGATE_SENTENCE, "the delegation sentence")):
                if lp.normalise(sentence) not in section:
                    self.add("S15", rel, span[0] + 1 if span else None, "§10 does not hold %s verbatim: %r"
                             % (what, sentence), sentence[:60])
        fused = lp.phrase_re(FUSED, re.I)
        for path in self.files("SKILL.md", "references/**/*", "templates/**/*", "packs/**/*"):
            text = read(path)
            for match in fused.finditer(text):
                self.add("S15", self.rel(path), text.count("\n", 0, match.start()) + 1, "the fused verification sentence "
                         "(%r): V1 goes above quick, V2 only beside a review seat" % match.group(0), match.group(0))

    # ------------------------------------------------------------------ S16
    def s16(self):
        for rel, text in self.text_files([rel for rel in self.all_files() if rel != "LICENSE"]):
            harness = self.harness_file(rel)
            for i, raw in enumerate(text.split("\n")):
                blanked = HOST_RE.sub(lambda m: " " * len(m.group(0)), MODEL_PLACEHOLDERS.sub(
                    lambda m: " " * len(m.group(0)), raw))
                for regex in MODEL_PATTERNS:
                    for m in regex.finditer(blanked):
                        self.add("S16", rel, i + 1, "names a model (%s): %r; the skill names none but a placeholder"
                                 % (regex.pattern, m.group(0)), m.group(0))
                if harness:
                    continue
                for regex in HARNESS_TOKENS:
                    for m in regex.finditer(raw):
                        self.add("S16", rel, i + 1, "a harness token outside the harness files (%s): %r"
                                 % (regex.pattern[:40], m.group(0)), m.group(0))

    # ------------------------------------------------------------------ S17
    def s17(self):
        files = self.all_files()
        for rel in self.markdown():
            text = read(self.path(rel))
            harness = self.harness_file(rel)
            for i, raw in enumerate(text.split("\n")):
                for token in self._skill_paths(raw):
                    if not self._resolves(token, files):
                        self.add("S17", rel, i + 1, "(a) the skill path %r resolves to no file of the folder" % token,
                                 token)
                if harness:
                    continue
                if "../" in raw:
                    self.add("S17", rel, i + 1, "(b) names `../`: the skill names no path outside its folder", "../")
                for span in re.findall(r"`([^`\n]+)`", raw):
                    if span.strip().startswith(("/", "~/", "$HOME/", "${")):
                        self.add("S17", rel, i + 1, "(b) names an absolute path %r: the skill names no path outside its "
                                 "folder" % span.strip(), span.strip())
        for rel in files:
            if rel.endswith(".py"):
                self._imports(rel, files)
        for rel, text in self.text_files([rel for rel in files if rel not in ("LICENSE", "NOTICE")]):
            guide = rel.startswith("references/harness-") and rel.endswith(".md")
            sources = False
            for i, raw in enumerate(text.split("\n")):
                if guide and raw.startswith("## "):
                    sources = raw.startswith("## 5. ")
                if URL_RE.search(raw) and not sources:
                    self.add("S17", rel, i + 1, "(d) a URL outside a guide's §5 Sources and NOTICE", URL_RE.search(raw).group(0))

    @staticmethod
    def _skill_paths(raw):
        """The skill paths a line names: backticked tokens and link targets starting with a skill folder, and every
        `<this skill's directory>/` path inside a code span."""
        out = []
        for span in re.findall(r"`([^`\n]+)`", raw) + re.findall(r"\]\(([^)\s]+)\)", raw):
            token = span.strip()
            if token.startswith(SKILL_PREFIXES):
                out.append(token.split()[0])
            for found in re.finditer(re.escape(SKILL_DIR_MARK) + r"([^\s\"'`]+)", token):
                out.append(SKILL_DIR_MARK + found.group(1))
        return out

    @staticmethod
    def _resolves(token, files):
        path = token[len(SKILL_DIR_MARK):] if token.startswith(SKILL_DIR_MARK) else token
        path = re.sub(r"(#.*|:\d+(-\d+)?)$", "", path).rstrip(".,;:)")
        if not path:
            return True
        parts = re.split(r"(<[^<>/]*>|\{[^{}/]*\}|\*)", path)
        regex = "".join("[^/]+" if part.startswith(("<", "{")) else "[^/]*" if part == "*" else re.escape(part)
                        for part in parts if part)
        regex = "^" + regex + ("" if path.endswith("/") else "(?:/.*)?$")
        return any(re.match(regex, rel) for rel in files)

    def _imports(self, rel, files):
        try:
            tree = ast.parse(read(self.path(rel)))
        except SyntaxError as error:
            self.add("S17", rel, error.lineno, "(c) the script does not parse, so its imports cannot be read")
            return
        local = {os.path.splitext(os.path.basename(f))[0] for f in files if f.endswith(".py")} | \
                {f.split("/")[-2] for f in files if f.endswith("/__init__.py")}
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if not (is_stdlib(top) or top in local):
                    self.add("S17", rel, node.lineno, "(c) imports %r, which is neither the standard library nor a "
                             "module of the folder" % name, name)

    # ------------------------------------------------------------------ S18
    def s18(self):
        name = self.skill_name()
        if not name:
            self.add("S18", "SKILL.md", None, "no frontmatter name to look for")
            return
        regex = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(name), re.I)
        for rel, text in self.text_files():
            for i, raw in enumerate(text.split("\n")):
                if rel == "SKILL.md" and re.match(r"^name:\s*[\"']?%s[\"']?\s*$" % re.escape(name), raw):
                    continue
                if rel == "agents/openai.yaml" and re.match(r'^\s+display_name:\s*("?)%s\1\s*$' % re.escape(name), raw):
                    continue
                for m in regex.finditer(raw):
                    self.add("S18", rel, i + 1, "names the skill (%r): its body never names itself, so the published "
                             "name can differ" % m.group(0), m.group(0))

    # ------------------------------------------------------------------ S19
    def s19(self):
        for rel in REQUIRED_GUIDES:
            if not self.exists(rel):
                self.add("S19", rel, None, "missing: every harness without a guide of its own uses it")
        for path in self.files("references/harness-*.md"):
            self._guide(self.rel(path))

    def _guide(self, rel):
        lp = self.lp
        lines = read(self.path(rel)).split("\n")
        states = fence_states(lines)
        headings = [raw.rstrip() for k, raw in enumerate(lines) if not states[k][0] and raw.startswith("## ")]
        if headings != list(lp.GUIDE_HEADINGS):
            self.add("S19", rel, None, "the headings are not the guide's five, in order: %s"
                     % ", ".join("`%s`" % h for h in lp.GUIDE_HEADINGS))
        blocks = {}
        for k, raw in enumerate(lines):
            if states[k][0] or not raw.startswith("### "):
                continue
            end = next((j for j in range(k + 1, len(lines)) if not states[j][0] and lines[j].startswith("#")), len(lines))
            fences = [j for j in range(k + 1, end) if states[j][2]]
            name = raw[4:].strip()
            blocks[name] = k
            if [states[j][1] for j in fences] != ["text"]:
                self.add("S19", rel, k + 1, "block %r has %d fences, not exactly one ```text fence" % (name, len(fences)),
                         name)
        for name in GUIDE_BLOCKS + GUIDE_EXTRA_BLOCKS.get(rel, ()):
            if name not in blocks:
                self.add("S19", rel, None, "the required block `### %s` is missing" % name, name)
        section, used = 0, {}
        for k, raw in enumerate(lines):
            if states[k][0]:
                if not states[k][2]:
                    self._fence_slots(rel, k, raw)
                continue
            number = re.match(r"^## (\d+)\. ", raw)
            if number:
                section = int(number.group(1))
                continue
            if not raw.strip() or raw.startswith("#") or not 1 <= section <= 4:
                continue
            tag = SOURCE_KEY_RE.search(raw)
            items = [item.strip() for item in tag.group(1).split(";")] if tag else []
            if not items or not all(KEY_ITEM_RE.match(item) for item in items):
                self.add("S19", rel, k + 1, "the line does not end with a source key (`[KEY #anchor]` or `[skill]`)",
                         raw.strip()[:60])
                continue
            for item in items:
                key = KEY_ITEM_RE.match(item).group(1)
                if key != "skill":
                    used.setdefault(key, k + 1)
        span = md_sections(lines).get("## 5. Sources")
        rows = {}
        for raw in lines[span[0]:span[1]] if span else []:
            if raw.strip().startswith("|"):
                cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
                rows[cells[0].strip("`* ")] = raw
        for key, line in sorted(used.items(), key=lambda kv: kv[1]):
            row = rows.get(key)
            if row is None:
                self.add("S19", rel, line, "the source key %s is not listed in §5" % key, key)
            elif not URL_RE.search(row) or not DATE_RE.search(row):
                self.add("S19", rel, line, "§5 lists %s without a URL and a retrieval date" % key, key)

    def _fence_slots(self, rel, k, raw):
        for m in re.finditer(r"(?<!\$)\{([A-Z][A-Z0-9_]*)(\}|:)", raw):
            name, kind = m.groups()
            if kind == "}" and name not in GUIDE_SLOTS:
                self.add("S19", rel, k + 1, "the slot {%s} is not one of the guides' slots" % name, name)
            elif kind == ":" and name not in self.lp.FRAGMENT_NAMES:
                self.add("S19", rel, k + 1, "the fragment {%s: …} is not one the linter expands (%s)"
                         % (name, ", ".join(self.lp.FRAGMENT_NAMES)), name)

    def run(self, wanted):
        for rule in RULES:
            if rule not in wanted:
                continue
            if rule in NEEDS_LINTER and self.lp is None:
                self.add(rule, "scripts/lint_prompt.py", None, "missing or does not import, so %s cannot run (it reads "
                         "the linter's frozen texts)" % rule)
                continue
            getattr(self, rule.lower())()
        order = {rule: k for k, rule in enumerate(RULES)}
        self.findings.sort(key=lambda f: (order[f.rule], f.file or "", f.line or 0))
        return self.findings


def default_skill():
    """The only folder under ../skills/ that holds a SKILL.md, or None."""
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
    found = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(root, "*", "SKILL.md")))
    return found[0] if len(found) == 1 else None


def shown(path):
    home = os.path.expanduser("~")
    path = os.path.abspath(path)
    if len(home) > 1 and (path == home or path.startswith(home + os.sep)):
        return "$HOME" + path[len(home):]
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="The skill's self-check.")
    parser.add_argument("--skill")
    parser.add_argument("--only", default=",".join(RULES))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    wanted = [rule.strip().upper() for rule in args.only.split(",") if rule.strip()]
    unknown = [rule for rule in wanted if rule not in RULES]
    if unknown or not wanted:
        sys.stderr.write("check_skill: unknown rule(s) in --only: %s (known: %s)\n"
                         % (", ".join(unknown) or "none given", ", ".join(RULES)))
        return 2
    skill = args.skill or default_skill()
    if skill is None:
        sys.stderr.write("check_skill: no single skill folder under ../skills/; name it with --skill <dir>\n")
        return 2
    if not os.path.isfile(os.path.join(skill, "SKILL.md")):
        sys.stderr.write("check_skill: no SKILL.md in --skill %s\n" % shown(skill))
        return 2
    findings = Checker(os.path.abspath(skill)).run(set(wanted))
    if args.json:
        print(json.dumps({"skill": shown(skill), "errors": len(findings), "warnings": 0, "allowed": 0,
                          "findings": [f.as_dict() for f in findings]}, indent=1, ensure_ascii=False))
    else:
        for finding in findings:
            print(finding.as_text())
        print("errors: %d, warnings: 0, allowed: 0" % len(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
