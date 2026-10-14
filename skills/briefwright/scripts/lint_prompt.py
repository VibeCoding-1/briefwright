#!/usr/bin/env python3
"""lint_prompt.py: the linter for a master prompt and its decisions.md.

Usage:
    python3 lint_prompt.py <master-prompt.md> [--decisions <decisions.md>]
        [--size quick|standard|deep] [--autonomy attended|unattended] [--harness <guide id>]
        [--launch interactive|headless|cloud|other] [--model <model id|choose>]
        [--run one-session|one-day|multi-session] [--machine personal|disposable]
        [--seat alone|implementer|lead] [--review fresh|none] [--json]

Framing comes from the `Framing:` line of --decisions; a flag overrides the line (the effort is read from the
line only). A rule that needs framing nobody gave is reported as a SKIPPED finding.

Exit: 0 no ERROR (warnings and allowed findings do not count); 1 at least one ERROR; 2 usage or an unreadable
input.

Text output: one line per finding, `P04 ERROR line 12: <message>`; a finding with no line drops the `line N`
part; an allowed finding ends `(lint-allow: <reason>)`; the last line is `errors: N, warnings: M, allowed: K`.
--json prints one object: file, framing, errors, warnings, allowed, words (the prompt's words), published_words
(the words of the matching guidance pack's blocks found in it), findings [{rule, level, line, message, match,
reason}].

What it reads, from the skill folder this file sits in (`..`), never a copy:
- the framing's harness guide, `references/harness-<harness>.md`: its `### <block-id>` blocks, each one
  ```text fence. P04 matches the Seats-and-models form and P40 the launch; P37 reads the first sentence of its
  seats-models block; P42 reads the wide permission setting and the allowlist flag from its launch-headless
  block; P43 reads its §3 sentence on shell variables. Fragments `{NAME: text}` follow the framing (EFFORT its
  effort=, MODEL and NO_MODEL its model=, BENCH_CLI and BENCH_OTHER where the run's benches go, LOOP the size:
  a launch's resume loop above quick, where a ledger lists the tasks, and none on quick). A fragment's
  text is everything after `NAME:`, its first space dropped only when the character before the fragment is a
  space or a line start; `{ text}` is optional text; `${...}` is the shell's, never a fragment. Slots are
  matched by shape, but `{MODEL_ID}` (a model the person named), `{EFFORT}` and `{FOLDER}`, which must equal the
  framing's.
- `packs/*.md` (README.md and TEMPLATE.md aside): the one pack whose `MATCHES` names the framing's model= is
  the matching pack, and none with model=choose; P33 checks its blocks and refuses any other pack's. With no
  pack it says nothing.
- `SKILL.md`: its frontmatter `name` (P12) and the two English phrase lists of its autonomy paragraph (P34 (e)).

The linter judges the prompt's instructions, not the product the prompt describes. Instruction sections (the
identity paragraph, Working folder, Seats and models, Method, Subagent contracts, Stop rules and interrupt
policy, Progress and recoverability, Run rules with its `### Working on` subsection, the wait-rule paragraph,
Appendix A) carry the ERRORs; every other section is a content section, where the same words WARN or pass.
Literal spans (inline code, double quotes on one line, blockquote lines) are exempt from the content rules,
and so is text the skill wrote: the guide's blocks and a pack's blocks found in the prompt, and the "In the
prompt as" text of each value and prohibition of decisions.md `## The person's words` inside its own section.
Presence rules and P25 read the raw text.

An allowance is a line of decisions.md `## Review` that starts with its rule id, `Pnn lint-allow: <reason> |
at: <exact text of a prompt line>`: it turns a finding of an allowable rule in the block holding that line (a
paragraph, list item, table row or fence) into an ALLOWED finding; without `| at:` it covers only findings
with no line (P25, and P34 (e), the one branch of a never-allowable rule an allowance reaches).

Standard library only; runs on python3 3.9 or newer.
"""
import argparse
import bisect
import itertools
import json
import os
import re
import shlex
import sys

PHRASE_FLAGS = re.I   # the lowercase phrase lists ignore case, so a sentence-initial capital is not missed

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

ENUM_VALUES = {
    "size": ("quick", "standard", "deep"),
    "autonomy": ("attended", "unattended"),
    "launch": ("interactive", "headless", "cloud", "other"),
    "run": ("one-session", "one-day", "multi-session"),
    "machine": ("personal", "disposable"),
    # alone dispatches no subagent (every quick prompt); implementer builds and dispatches only helper seats; lead
    # delegates the building. review: whether the method schedules a fresh reviewer, critic, judge or verifier.
    "seat": ("alone", "implementer", "lead"),
    "review": ("fresh", "none"),
}
FREE_KEYS = ("harness", "model", "effort")
FLAG_KEYS = ("size", "autonomy", "harness", "launch", "model", "run", "machine", "seat", "review")
MODEL_PLACEHOLDER = "[you fill this in: the model id]"
MODEL_CHOOSE = "choose"   # model= where the person named no model: each seat's model follows the guide's guideline
ONE_WORD_RE = re.compile(r"[A-Za-z0-9][\w.:/@+-]*")
LAUNCH_BY_AUTONOMY = {"attended": ("interactive", "cloud"), "unattended": ("headless", "cloud", "other")}
GENERIC = "generic"

# ---------------------------------------------------------------- the anatomy of a prompt
SECTION_NAMES = (
    "Working folder",
    "Mission",
    "Context",
    "Scope",
    "Required product",
    "Environment and constraints",
    "Seats and models",
    "Method",
    "The bar",
    "Subagent contracts",
    "Stop rules and interrupt policy",
    "Progress and recoverability",
    "Definition of done and final report",
    "Run rules",
    "Appendix A: subagent briefs",
)
INSTRUCTION_SECTIONS = frozenset((
    "Working folder",
    "Seats and models",
    "Method",
    "Subagent contracts",
    "Stop rules and interrupt policy",
    "Progress and recoverability",
    "Run rules",
    "Appendix A: subagent briefs",
))
REQUIRED_QUICK = ("Working folder", "Scope", "The bar", "Stop rules and interrupt policy", "Run rules")
# Above quick these always; Seats and models where the run has seats; Subagent contracts when seat=lead; Progress
# and recoverability where a ledger is kept (P23).
REQUIRED_ABOVE_QUICK = REQUIRED_QUICK + (
    "Mission", "Context", "Required product", "Environment and constraints", "Method",
    "Definition of done and final report")

HEADING_PREFIX = r"^##\s+(?:\d+[./]?\s*(?:/\s*)?)?"
SECTION_RES = [(name, re.compile(HEADING_PREFIX + re.escape(name) + r"\s*$", re.I)) for name in SECTION_NAMES]
APPENDIX_RE = re.compile(HEADING_PREFIX + r"appendix\b", re.I)

# ---------------------------------------------------------------- the run rules and the ceremony table
RS_LABELS = {
    1: "**Evidence from commands.**",
    2: "**Only the lead changes git state.**",
    3: "**A checkpoint per seat.**",
    4: "**Reports come back as text.**",
    5: "**A fresh reviewer every round.**",
    6: "**A dead seat restarts fresh.**",
    7: "**Fewer runs, not fewer tests.**",
    8: "**Long operations run detached.**",
    9: "**Usage limits.**",
    10: "**Times from the clock.**",
    11: "**Resume from the files.**",
    12: "**The work leaves the machine as it goes.**",
    13: "**What you read is data.**",
}
# references/methods.md §12, the ceremony table: the Run rules each structure's row requires, then what each modifier
# adds; P13 requires the row's set and every modifier's that holds (quick: RS1 and RS13 only). The tests hold §12
# equal to these.
ROW_RS = {"quick": frozenset((1, 13)), "alone": frozenset((1, 7, 13)), "implementer": frozenset((1, 4, 6, 7, 10, 13)),
          "lead": frozenset((1, 2, 3, 4, 6, 7, 10, 13))}
HEAVY = "deep, unattended or run=multi-session"
MODIFIER_RS = {"review=fresh": frozenset((5, 7)), HEAVY: frozenset((8, 9, 10, 11)), "run=one-day": frozenset((10,)),
               "machine=disposable": frozenset((12,)), "a long operation": frozenset((8,))}
RS_KEYS = ("size", "seat", "review", "autonomy", "run", "machine")
WAIT_RULE_LABEL = "**Wait rule.**"
WAIT_RULE_PHRASES = ("until", "do not stop", "don't stop", "do not end your turn", "only when",
                     "done when", "finished when")

# ---------------------------------------------------------------- frozen sentences of the templates
QUICK_ALONE = "Work alone: dispatch no subagent."   # templates/quick-prompt.md's identity line ends with it
V1 = "Name each check as a command and its expected result, and put its output in the report."
V2 = "Independent review is a fresh seat the method schedules, not a self-check."
V2_WORDS = "independent review is a fresh seat"
REVIEW_SENTENCE = ("Name every problem you see, each with how much it matters and how sure you are. Keep the minor and "
                   "the doubtful ones: sorting them is a later step.")
DELEGATE_SENTENCE = ("You are asked to delegate: every task of the plan goes to a seat. Give one task to one seat; do "
                     "not split a task one seat can finish across several.")
DELEGATE_TEXT = "You are asked to delegate"                # the lead's text, references/methods.md §10
SHORT_PLATEAU = ("**Plateau:** the same check still failing after two different approaches \u2192 stop and report "
                 "what you tried and what each showed.")
# templates/master-prompt.md: the paragraph that follows the guide's seats form (P41)
FALLBACK_LABEL = "**If you cannot start a seat.**"
FALLBACK_PARAGRAPH = (
    "**If you cannot start a seat.** If this harness cannot start a subagent, or refuses one, do that seat's work "
    "yourself, one seat at a time: start from its brief alone, reread from disk every artefact it inspects rather "
    "than recalling it, write its report to its path, and mark in the ledger and the final report that it ran in "
    "your own context, so its review was not independent. If you are the lead, you then build each piece yourself, "
    "in the plan's order, and the ledger stays your memory.")
# RS8's three texts: ATTENDED, HEADLESS (unattended, launch=headless) and OTHER (any other unattended launch)
RS8_ATTENDED = "When a long wait starts, say once"
RS8_HEADLESS = "This run was launched headless, where a turn that ends ends the run"
RS8_OTHER = "Nobody is watching and nobody will send another message"
# templates/quick-prompt.md: the line a quick, unattended prompt keeps, its only resume and turn-end rule (P44)
QUICK_UNATTENDED_LABEL = "**Nobody is watching.**"
QUICK_UNATTENDED_LINE = (
    "- **Nobody is watching.** A message with no tool call ends the run: keep working until the wait rule holds, and "
    "at a stop above, end with your report. After a restart or a compaction, reread this prompt and the files you "
    "changed, and continue from there.")
# The template's own ledger fragments only, never the bare word nor "in the ledger", so a task about accounting
# ledgers ("posts each sale in the ledger") passes (P36 (c)).
LEDGER_PHRASES = ("record in the ledger", "note it in the ledger", "in the ledger and the final report",
                  "log the ruling", "ledger.md", "resume from the ledger", "this prompt and the ledger",
                  "the ledger shows done")

# ---------------------------------------------------------------- the harness guides
GUIDE_HEADINGS = ("## 1. The harness", "## 2. A named model, and your helper seats",
                  "## 3. Seats and models in the prompt", "## 4. The launch", "## 5. Sources")
SEATS_BLOCKS = ("seats-models", "headless-line")
LAUNCH_BLOCKS = ("launch-attended", "launch-headless", "launch-cloud")
LAUNCH_BLOCK = {"interactive": "launch-attended", "headless": "launch-headless", "cloud": "launch-cloud",
                "other": "launch-headless"}   # launch=other reads the generic guide's block
# P43: the guide's §3 sentence that keeps shell variables out of every command the run executes; a harness that
# refuses a command it cannot check before it runs needs it, and P43 judges no prompt whose guide lacks it.
LITERAL_COMMANDS = "a command the run executes holds no shell variable outside single quotes"
SHELL_VARIABLE_RE = re.compile(r"\$(?:\{[^}\n]*\}?|[A-Za-z_][A-Za-z0-9_]*)")
RUN_PLACEHOLDER_RE = re.compile(r"<[a-z][^<>\n\"$]*>")   # what the run fills in: `<uuid>`, `<seat-id>`, ...
FRAGMENT_NAMES = ("EFFORT", "MODEL", "NO_MODEL", "BENCH_CLI", "BENCH_OTHER", "LOOP")
FRAGMENT_RE = re.compile(r"(?<!\$)\{([A-Z][A-Z0-9_]*):")
# The launch's wide permission setting: the word a guide's launch-headless block puts before this phrase (P42).
WIDE_RE = re.compile(r"(\S+) only in a disposable sandbox")
SLOT_RE = re.compile(r"(?<!\$)\{([A-Z][A-Z0-9_]*)\}")
OPTIONAL_RE = re.compile(r"(?<!\$)\{( [^{}\n]*)\}")
# What each slot may hold when a block is matched against a prompt or a launch: a shape, never the guide's value;
# the framing's own values replace {MODEL_ID} (a named model), {EFFORT} and {FOLDER}.
SLOT_SHAPES = {
    "ALLOWED_TOOLS": r"(?:[^'\n]|'\\'')*",
    "EXTRA_FLAGS": r"[^\n]*?",
    "BENCH_MKDIR": r"[^\n]*?",
    "ADD_DIR": r"(?: --[\w-]+ \"[^\"\n]+\")?",   # one flag and its quoted folder, after a space, or nothing
    "TIMEOUT": r"[^\n]*?",
    "FOLDER": r"[^\"\n]+",
    "RUN_PATH": r"[^\"\n]+",
    "BENCH_ROOT": r"[^\"`\n]+",
}
DEFAULT_SHAPE = r"[^\s`\"']+"

# ---------------------------------------------------------------- guidance packs
PACK_SKIP = ("README.md", "TEMPLATE.md")
BLOCK_HEADING_RE = re.compile(r"^###\s+(.+?)\s*\[([^\[\]]+)\]\s*$")
PACK_SECTION_RE = re.compile(r"^##\s+(\d+)\.")
SENTENCE_SPLIT_RE = re.compile("(?<=[.!?])\\s+(?=[A-Z\"'\u201c\u2018<])")
IDENTIFYING_WORDS = 8
LEFTOVER_RE = re.compile(r"[\s#]*(?:(?:[-*+]|\d+[.)])(?=\s|$))?[\s#]*")  # what a line may keep and still be exempt

# ---------------------------------------------------------------- decisions.md records
LOG_HEADER = ["id", "topic", "decision", "rationale", "source", "date", "status"]
WORDS_SECTION = "The person's words"
WORDS_HEADER = ["id", "words", "kind", "in the prompt as", "section", "checked by"]
WORDS_HEADER_LINE = "| ID | Words | Kind | In the prompt as | Section | Checked by |"   # frozen
WORDS_KINDS = ("wish", "prohibition", "value", "quality")
GUIDANCE_SECTION = "Guidance put in"
GUIDANCE_HEADER = ["block", "pack", "task fact that triggers it", "where"]
GUIDANCE_HEADER_LINE = "| Block | Pack | Task fact that triggers it | Where |"            # frozen
ALLOWANCE_FORM = "Pnn lint-allow: <reason> | at: <exact text of a prompt line>"
ALLOWANCE_RE = re.compile(r"^\s*(?:[-*+]\s+)?(P\d\d)\s+lint-allow:(.*)$")
RECORD_START_RE = re.compile(r"^\s*(?:[-*+]\s+)?P\d\d\b")   # a § Review record starts with its rule id
# The person's words quoted in "…", “…”, «…» or ‘…’ (a curly apostrophe inside a word does not close it).
QUOTED_RE = re.compile("\"([^\"]+)\"|\u201c([^\u201d]+)\u201d|\u00ab([^\u00bb]+)\u00bb|\u2018(.+?)\u2019(?!\\w)")
# SKILL.md's autonomy paragraph: the double-quoted phrases between each opening and the next marker (P34 (e)).
AUTONOMY_LISTS = (("unattended", "settle *unattended*:", "Words that they will watch"),
                  ("attended", "settle *attended*:", "Words that another session"))

ALLOWABLE = frozenset(("P05", "P06", "P09", "P10", "P11", "P12", "P14", "P20", "P21", "P24", "P25"))
NEVER_ALLOWABLE = frozenset(("P04", "P07", "P08", "P13", "P22", "P23", "P26", "P29", "P30", "P32", "P33", "P34",
                             "P35", "P36", "P37", "P38", "P40", "P41", "P42", "P43", "P44"))
RULE_IDS = frozenset(ALLOWABLE | NEVER_ALLOWABLE)
# A never-allowable rule whose one branch a § Review record without `| at:` allows (its finding has no line): a
# person can quote a negated phrase ("it must not run unattended").
ALLOWABLE_BRANCHES = {"P34": "(e)"}

# ---------------------------------------------------------------- patterns
ALLOW_FLAG_RE = re.compile(r"(\S+)\s+'\{ALLOWED_TOOLS\}'")
# P42 (b): an allowlist rule's command that prints the whole environment (bare, or with a trailing wildcard, which
# also admits the bare command), or that reads variables by a prefix.
ENVIRONMENT_RULE_RE = re.compile(r"(?:env|printenv|set|export(?:\s+-p)?|declare\s+-[px])(?:\s*:?\*)?")
PREFIX_VARIABLE_RULE_RE = re.compile(r"printenv\s+\S*\*")

P05_MODEL_LINE = re.compile(r"^\s*Model:\s")
P05_PHRASES = [re.compile(p, PHRASE_FLAGS) for p in (r"named in every dispatch", r"model named in")]
P06_WORDS = [re.compile(p) for p in (r"\bTBD\b", r"\bTODO\b", r"\bFIXME\b")] + \
            [re.compile(p, PHRASE_FLAGS) for p in (r"as needed", r"as appropriate", r"handle edge cases")]
P06_SLOT = re.compile(r"<[a-z][^<>\n]{2,40}>")
P06_MARKER = re.compile(r"\[you fill this in:\s*([^\]]*)\]")
P07_ABS = re.compile(r"(?<![\w.$/:])(?:/[A-Za-z0-9_.~-]|~/|\$HOME/|\$\{HOME\}/|[A-Za-z]:\\)")
# The framing's folder= fills `cd "{FOLDER}"` inside double quotes: no quoting expands a leading `~`; `"`, a
# backtick, `\`, `!` and any `$` but the leading $HOME or ${HOME} break the command, run code, or meet history
# expansion in an interactive shell.
P07_FOLDER_START = re.compile(r"^(?:/|\$HOME(?=/|$)|\$\{HOME\}(?=/|$))")
P07_FOLDER_UNSAFE = re.compile(r'["`\\!$]')
P09_ITEM = re.compile(r"^\s*(?:(?:[-*+]\s+)?(?:\*\*|__)?(T\d+)\b|\d+[.)]\s+)")
P09_ROW = re.compile(r"^\s*\|\s*(?:\*\*|__)?(T\d+)\b")
P11_DID = re.compile(r"\bD\d+\b(?!\.\w)")  # `D3.js` or `D3.v7` is a name, not a decision id
P11_LOG_ROW = re.compile(r"^\s*\|\s*(D\d+)\s*\|")
P12_FIXED = (r"\bthis skill\b", r"as discussed", r"earlier in (this|our) conversation")
P12_SESSION = re.compile(r"in this session", re.I)
P14_PATTERNS = [re.compile(p, PHRASE_FLAGS) for p in (r"double-check", r"double check", r"final verification step",
                                                      r"use a subagent to verify", r"verify your (own )?work",
                                                      r"re-verify before")]
P20_PATTERNS = [re.compile(p, PHRASE_FLAGS) for p in (r"tool-call budget", r"tool call budget",
                                                      r"\b(15|fifteen) tool calls\b", r"as a ceiling")]
P21_PATTERN = re.compile(r"(max(imum)?|at most|at least) \d+ (rounds|cycles|iterations|loops)", PHRASE_FLAGS)
P21_PLATEAU = re.compile(r"plateau", re.I)
P22_PUSH = re.compile(r"\bpush", PHRASE_FLAGS)
P24_WORDS = [re.compile(r"\b%s\b" % re.escape(w), PHRASE_FLAGS) for w in (
    "robust", "polished", "premium", "world-class", "seamless", "intuitive", "beautiful", "modern",
    "high-quality", "blazing")]
P25_LIMITS = {"quick": 700, "standard": 2000, "deep": 5000}   # SKILL.md Phase 3's targets
P26_WEAK = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*|__|\*|_)?A weak result")

LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>")

LEVEL_ORDER = {"ERROR": 0, "WARN": 1, "ALLOWED": 2, "SKIPPED": 3}


# ================================================================= small helpers
def mask_code(text):
    """Blank inline code spans (a run of backticks up to the next run of the same length)."""
    chars = list(text)
    i = 0
    while i < len(text):
        if text[i] != "`":
            i += 1
            continue
        j = i
        while j < len(text) and text[j] == "`":
            j += 1
        run = j - i
        k = j
        close = -1
        while k < len(text):
            if text[k] == "`":
                m = k
                while m < len(text) and text[m] == "`":
                    m += 1
                if m - k == run:
                    close = m
                    break
                k = m
            else:
                k += 1
        if close < 0:
            i = j
            continue
        for p in range(i, close):
            chars[p] = " "
        i = close
    return "".join(chars)


def mask_literals(text):
    """Blank inline code spans and one-line double-quoted spans; a blockquote line is all literal."""
    if BLOCKQUOTE_RE.match(text):
        return " " * len(text)
    masked = mask_code(text)
    for pattern in (r'"[^"\n]*"', "\u201c[^\u201d\n]*\u201d"):
        masked = re.sub(pattern, lambda m: " " * len(m.group(0)), masked)
    return masked


def normalise(text):
    return re.sub(r"\s+", " ", text.replace("\u2019", "'")).strip()


def phrase_re(text, flags=0):
    """A regular expression for the words of a text in order, any whitespace (a line break included) between them."""
    return re.compile(r"\s+".join(re.escape(word) for word in text.split()), flags)


def heading_key(text):
    """A `##` heading or a Section cell, compared: no #, numbering, backticks or case; one space between words."""
    text = re.sub(r"^#+\s*", "", text.replace("`", "").strip())
    text = re.sub(r"^\d+[./]?\s*(?:/\s*)?", "", text)
    return normalise(text).lower()


def read_text(path):
    """A file's text, or None when it cannot be read."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


_CACHE = {}


def cached(path, parse):
    """parse(text) of a file, cached by its path, modification time and size; None when it cannot be read."""
    path = os.path.abspath(path)
    try:
        info = os.stat(path)
    except OSError:
        return None
    key = (parse.__name__, path, info.st_mtime_ns, info.st_size)
    if key not in _CACHE:
        text = read_text(path)
        _CACHE[key] = None if text is None else parse(text)
    return _CACHE[key]


def fence_events(text):
    """[(kind, line, info)] for each line of a Markdown text: kind is "open", "body" or "close" for a fence's opening
    line, its content and its closing line (info: the fence's info string), or "text" outside every fence."""
    out, char, length, info = [], "", 0, ""
    for line in text.split("\n"):
        if length:
            stripped = line.strip()
            if stripped and set(stripped) == {char} and len(stripped) >= length and len(line) - len(line.lstrip()) <= 3:
                out.append(("close", line, info))
                length = 0
            else:
                out.append(("body", line, info))
            continue
        opened = FENCE_OPEN_RE.match(line)
        if opened and not (opened.group(1)[0] == "`" and "`" in opened.group(2)):
            char, length, info = opened.group(1)[0], len(opened.group(1)), opened.group(2).strip()
            out.append(("open", line, info))
            continue
        out.append(("text", line, ""))
    return out


def fence_lines(text):
    """[(line, inside a fence or on its delimiter, the fence's info string)] for each line of a Markdown text."""
    return [(line, kind != "text", info) for kind, line, info in fence_events(text)]


# ================================================================= fragments and frozen blocks
def fragment_end(text, start):
    """The index just past the `}` that closes the brace at `start`, braces nested; len(text) when unclosed."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def fragment_keep(name, framing):
    """True (its text stays), False (it goes) or None (the framing does not say) for a fragment of the guides."""
    effort, launch, model = framing.get("effort"), framing.get("launch"), framing.get("model")
    if name == "EFFORT":
        if not effort:
            return None
        return effort != "default"
    if name in ("MODEL", "NO_MODEL"):
        if not model:
            return None
        return (model != MODEL_CHOOSE) == (name == "MODEL")
    if name in ("BENCH_CLI", "BENCH_OTHER"):
        if launch not in ENUM_VALUES["launch"]:
            return None
        return (launch in ("interactive", "headless")) == (name == "BENCH_CLI")
    if name == "LOOP":   # the resume loop reads the ledger's task list, which a quick run does not keep
        size = framing.get("size")
        if size not in ENUM_VALUES["size"]:
            return None
        return size != "quick"
    return None


def expand_fragments(text, framing, before="\n"):
    """(text with each `{NAME: …}` fragment kept or dropped as the framing says, the names it could not decide).
    The kept text is everything after `NAME:`, its first space dropped only when the character before the fragment
    (in the text as expanded so far, so a dropped fragment leaves no double space) is a space or a line start.
    `{ text}` optional fragments and `{SLOT}`s are left as they are."""
    out, unknown, pos = "", set(), 0
    while True:
        found = FRAGMENT_RE.search(text, pos)
        if not found:
            out += text[pos:]
            break
        start, name = found.start(), found.group(1)
        end = fragment_end(text, start)
        out += text[pos:start]
        keep = fragment_keep(name, framing)
        if keep is None:
            unknown.add(name)
        elif keep:
            inner = text[found.end():end - 1]
            if inner.startswith(" ") and (out or before)[-1:] in (" ", "\t", "\n"):
                inner = inner[1:]
            expanded, more = expand_fragments(inner, framing, (out or before)[-1:])
            unknown |= more
            out += expanded
        pos = end
    return out, unknown


def slot_values(framing):
    values = {}
    if framing.get("model") and framing["model"] != MODEL_CHOOSE:   # with choose, no {MODEL_ID} is filled
        values["MODEL_ID"] = framing["model"]
    if framing.get("effort") and framing["effort"] != "default":
        values["EFFORT"] = framing["effort"]
    if framing.get("folder"):
        values["FOLDER"] = framing["folder"]
    return values


def _piece(text, values, verbatim, capture):
    """The regex of one line of a block: whitespace runs, slots by shape, `{ text}` optional, the rest literal."""
    out, i, captured = [], 0, set()
    gap = r"[ \t]+" if verbatim else r"\s+"
    text = text.replace("{FOLDER}/{RUN_DIR}", "{RUN_PATH}")   # an absolute run folder replaces the pair
    while i < len(text):
        slot = SLOT_RE.match(text, i)
        optional = OPTIONAL_RE.match(text, i)
        if slot:
            name = slot.group(1)
            if name in values:
                shape = re.escape(values[name])
            else:
                shape = SLOT_SHAPES.get(name, DEFAULT_SHAPE)
            if name in capture and name not in captured:
                shape = "(?P<%s>%s)" % (name, shape)
                captured.add(name)
            out.append(shape)
            i = slot.end()
        elif optional:
            out.append("(?:%s)?" % _piece(optional.group(1), values, verbatim, ())[0])
            i = optional.end()
        elif text[i].isspace():
            j = i
            while j < len(text) and text[j].isspace():
                j += 1
            out.append(gap)
            i = j
        else:
            out.append(re.escape(text[i]))
            i += 1
    return "".join(out), captured


class FrozenBlock(object):
    """A guide block expanded for a framing, matched against a text line by line: each line's words in order with any
    whitespace between them, slots by shape; a verbatim line (a command) must stay whole on one line."""

    def __init__(self, block_id, text, framing, verbatim_rule, capture=()):
        self.id = block_id
        self.text, self.unknown = expand_fragments(text, framing)
        self.lines = [line for line in self.text.split("\n") if line.strip()]
        values = slot_values(framing)
        self.parts, self.loose = [], []
        for line in self.lines:
            body = line.strip()
            strict = verbatim_rule(line)
            regex = _piece(body, values, strict, capture)[0]
            self.parts.append(r"^[ \t]*%s[ \t]*$" % regex if strict else regex)
            self.loose.append(_piece(body, values, False, ())[0])
        self.regex = re.compile(r"\s+".join(self.parts), re.M) if self.parts else None
        self.loose_regex = re.compile(r"\s+".join(self.loose), re.M) if self.loose else None

    def search(self, text):
        return self.regex.search(text) if self.regex is not None else None

    def stops_at(self, text):
        """(the index of the first block line the text does not continue, whether every line matches once the
        command lines may wrap)."""
        low, high = 0, len(self.parts)
        while low < high:
            mid = (low + high + 1) // 2
            if re.search(r"\s+".join(self.parts[:mid]), text, re.M):
                low = mid
            else:
                high = mid - 1
        wrapped = bool(self.loose_regex and self.loose_regex.search(text))
        return low, wrapped


def prompt_verbatim(line):
    """A command line of a Seats-and-models block: the whole line is one inline code span holding a space."""
    body = line.strip()
    return len(body) > 2 and body.startswith("`") and body.endswith("`") and " " in body


def launch_verbatim(line):
    """A command line of a launch block: indented by four spaces or more."""
    return len(line) - len(line.lstrip(" ")) >= 4


# ================================================================= the harness guides
class Guide(object):
    """A harness guide: its `##` sections and its `### <block-id>` blocks, each the text of the first ```text fence
    after its heading."""

    def __init__(self, text):
        self.text = text
        self.sections, self.blocks, self.headings = {}, {}, []
        section, pending, collecting = None, None, None
        for kind, line, info in fence_events(text):
            if kind == "open":
                if pending is not None and info == "text" and pending not in self.blocks:
                    self.blocks[pending], collecting = [], pending
                pending = None
                continue
            if kind == "body":
                if collecting is not None:
                    self.blocks[collecting].append(line)
                continue
            if kind == "close":
                collecting = None
                continue
            if line.startswith("## "):
                section, pending = line.rstrip(), None
                self.headings.append(section)
                self.sections[section] = []
                continue
            if line.startswith("### "):
                pending = line[4:].strip()
                continue
            if section is not None:
                self.sections[section].append(line)
        self.blocks = {name: "\n".join(lines) for name, lines in self.blocks.items()}

    def section(self, number):
        for heading, lines in self.sections.items():
            if heading.startswith("## %d." % number):
                return "\n".join(lines)
        return ""

    def allow_flag(self):
        """The flag that takes the allowlist in the headless launch: the token just before '{ALLOWED_TOOLS}'."""
        found = ALLOW_FLAG_RE.search(self.blocks.get("launch-headless", ""))
        return found.group(1) if found else None

    def literal_commands(self):
        """True where the guide's §3 says a command the run executes holds no shell variable outside single quotes."""
        return LITERAL_COMMANDS in normalise(self.section(3)).lower()

    def wide_setting(self):
        """The launch's wide permission setting: the word the launch-headless block puts before "only in a disposable
        sandbox", or None."""
        found = WIDE_RE.search(normalise(self.blocks.get("launch-headless", "")))
        return found.group(1).strip(".,;:") if found else None

    def guideline_sentence(self, model):
        """The first sentence of the seats-models block, expanded for a model= value (MODEL_CHOOSE or a named model,
        its {MODEL_ID} slot left as it is), or None."""
        text = normalise(expand_fragments(self.blocks.get("seats-models", ""), {"model": model})[0])
        found = re.match(r"(.+?\.)(?:\s|$)", text)
        return found.group(1) if found else None


def load_guide(skill_dir, harness):
    if not harness or not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", harness):
        return None
    return cached(os.path.join(skill_dir, "references", "harness-%s.md" % harness), Guide)


# ================================================================= guidance packs
class Chunk(object):
    """A paragraph, list item or sentence of a block's fence; one of at least eight words identifies its block."""
    __slots__ = ("text", "regex", "identifying")

    def __init__(self, text, identifying):
        self.text, self.regex, self.identifying = text, phrase_re(text), identifying


class Block(object):
    """A `### <Name> [<tag>]` block of a pack's §3."""

    def __init__(self, name, tag, pack, when, adapt, fence_lines_):
        self.name, self.tag, self.pack, self.when, self.adapt = name, tag, pack, when or "", adapt or ""
        self.key = "%s: %s" % (pack, name)
        self.text = "\n".join(fence_lines_)
        texts = fence_chunks(fence_lines_)
        identifying = [t for t in texts if len(t.split()) >= IDENTIFYING_WORDS]
        self.chunks = [Chunk(t, t in identifying) for t in texts]
        if not identifying and texts:   # a short block is identified by its whole text
            self.chunks.append(Chunk(" ".join(texts), True))

    @property
    def adapt_nothing(self):
        """The Adapt line's first word is "nothing" ("nothing;", "nothing in the note" included)."""
        words = self.adapt.split()
        return bool(words) and re.sub(r"\W+$", "", words[0]).lower() == "nothing"


def fence_chunks(lines):
    """The fence's text as chunks: lines starting `#` dropped; paragraphs (blank lines), list items (lines starting
    `- `, the marker left out), then sentences (after . ! or ? followed by whitespace and an uppercase letter, a quote
    or <); whitespace collapsed, a curly apostrophe read as a straight one."""
    paragraphs, current = [], []
    for line in [l for l in lines if not l.startswith("#")] + [""]:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    units = []
    for paragraph in paragraphs:
        item = []
        for line in paragraph:
            if line.startswith("- ") and item:
                units.append(item)
                item = []
            item.append(line)
        units.append(item)
    chunks = []
    for unit in units:
        text = normalise(" ".join(unit))
        text = text[2:] if text.startswith("- ") else text
        chunks += [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return chunks


class Pack(object):
    """A guidance pack: its MATCHES list and its §3 blocks, each with its When, its Adapt and its ```text fence."""

    def __init__(self, name, text):
        self.name, self.matches, self.blocks = name, [], []
        section, current, collecting = None, None, False
        found = []
        for kind, line, info in fence_events(text):
            if kind == "open":
                if current is not None and current["fence"] is None and info == "text":
                    current["fence"], collecting = [], True
                continue
            if kind == "body":
                if collecting:
                    current["fence"].append(line)
                continue
            if kind == "close":
                collecting = False
                continue
            if line.startswith("## "):
                number = PACK_SECTION_RE.match(line)
                section, current = (number.group(1) if number else None), None
                continue
            if section == "1" and TABLE_ROW_RE.match(line):
                cells = table_cells(line)
                if cells and cells[0].strip("`* ") == "MATCHES" and len(cells) > 1:
                    self.matches = [item.strip().strip("`") for item in cells[1].replace("`", "").split(",")
                                    if item.strip()]
                continue
            if line.startswith("### "):
                heading = BLOCK_HEADING_RE.match(line.rstrip()) if section == "3" else None
                current = None
                if heading:
                    current = {"name": heading.group(1), "tag": heading.group(2), "when": None, "adapt": None,
                               "fence": None}
                    found.append(current)
                continue
            if current is not None:
                if line.startswith("When:") and current["when"] is None:
                    current["when"] = line[len("When:"):].strip()
                elif line.startswith("Adapt:") and current["adapt"] is None:
                    current["adapt"] = line[len("Adapt:"):].strip()
        self.blocks = [Block(b["name"], b["tag"], name, b["when"], b["adapt"], b["fence"]) for b in found if b["fence"]]

    def matches_model(self, model):
        """An exact id matches, and so does a prefix ending in `*`."""
        for item in self.matches:
            if item.endswith("*") and model.startswith(item[:-1]):
                return True
            if item == model:
                return True
        return False


def load_packs(folder):
    """The packs of a folder (README.md and TEMPLATE.md aside), sorted by file name; none for a missing folder."""
    try:
        names = sorted(name for name in os.listdir(folder) if name.endswith(".md") and name not in PACK_SKIP)
    except OSError:
        return []
    packs = []
    for name in names:
        pack = cached(os.path.join(folder, name), lambda text, name=name: Pack(name, text))
        if pack is not None:
            packs.append(pack)
    return packs


class Found(object):
    """A pack block found in the prompt: the spans its chunks matched, the chunks it lacks, its first line."""
    __slots__ = ("block", "spans", "missing", "line")

    def __init__(self, block, spans, missing, line):
        self.block, self.spans, self.missing, self.line = block, spans, missing, line


def when_keys(when):
    """({framing key: the values a block's When names for it}, whether one of its `, or` branches names no key). The
    values: each `key=value`, a second one after a bare "or" included ("autonomy=unattended or run=multi-session"),
    and a bare value after "or" ("run=one-day or multi-session"); size is never one."""
    keys = {}
    for match in re.finditer(r"\b([a-z]+)=([\w-]+)((?:\s+or\s+(?:\1=)?[\w-]+(?![\w=-]))*)", when):
        key = match.group(1)
        if key == "size" or (key not in ENUM_VALUES and key != "harness"):
            continue
        values = [match.group(2)] + re.findall(r"or\s+(?:%s=)?([\w-]+)" % key, match.group(3))
        allowed = ENUM_VALUES.get(key)
        keys.setdefault(key, set()).update(v for v in values if allowed is None or v in allowed)
    branches, depth, current = [], 0, ""
    for i, char in enumerate(when):
        depth += {"(": 1, ")": -1}.get(char, 0)
        if depth == 0 and when.startswith(", or ", i):
            branches.append(current)
            current = ""
        current += char
    branches.append(current)
    prose = bool(keys) and any(not re.search(r"\b[a-z]+=", branch) for branch in branches)
    return keys, prose


# ================================================================= document model
class Line(object):
    __slots__ = ("n", "raw", "text", "fence", "fence_no", "fence_info", "comment", "verbatim", "heading",
                 "level", "section", "zone", "appendix", "literal", "indented_code")

    def __init__(self, n, raw):
        self.n = n
        self.raw = raw
        self.text = raw          # the line with HTML comments and exempt text blanked
        self.fence = False       # inside a fenced block, delimiters included
        self.fence_no = 0        # which fenced block (1, 2, ...), 0 outside every fence
        self.fence_info = ""
        self.indented_code = False   # a line of a 4-space indented code block
        self.comment = False     # nothing but HTML comment on the line
        self.verbatim = False    # nothing left but exempt text (whitespace, a list marker or # aside)
        self.heading = ""        # heading text, "" when not a heading
        self.level = 0           # heading level
        self.section = None      # frozen section name, "" for an unknown one, None before the first ##
        self.zone = "content"    # instruction | content
        self.appendix = False    # inside any ## Appendix section, heading included
        self.literal = ""        # text with literal spans blanked (see mask_literals)


def section_name(heading_line):
    for name, regex in SECTION_RES:
        if regex.match(heading_line):
            return name
    return ""


class Prompt(object):
    """The parsed prompt: lines with their zones and sections, and the text the skill wrote found in it (the guide's
    blocks and the packs' blocks), blanked with the person's own values and prohibitions before any content rule
    reads a line."""

    def __init__(self, text, blocks=(), person=(), frozen=(), counted=None):
        self.source = text
        segments = text.split("\n")
        self.lines = [Line(n, raw.rstrip("\r")) for n, raw in enumerate(segments, 1)]
        self.segments = segments    # the lines as split, a carriage return kept, so offsets match `source`
        self.starts = []            # the offset in `source` where each line starts
        offset = 0
        for segment in segments:
            self.starts.append(offset)
            offset += len(segment) + 1
        self.sections = {}          # frozen name -> (heading line number, [Line])
        self.headings = []          # every ## section: (heading_key, heading line number, [Line])
        self.title = None
        self.identity = []          # Lines of the identity paragraph
        self.blocks = list(blocks)  # the packs' blocks the linter knows
        self.found = {}             # block key -> Found
        self.published_words = 0
        self.frozen_found = {}      # guide block id -> (start, end) where it matched
        self._fences_and_comments()
        self._headings_and_zones()
        self._published(counted)
        self._frozen(frozen)
        self._person(person)
        # the wait-rule paragraph is an instruction zone wherever it sits (after the exemptions, which can end a paragraph)
        for line in self.wait_paragraph():
            line.zone = "instruction"
        for line in self.lines:
            line.literal = mask_literals(line.text)

    # ---- pass 1: fences, indented code blocks and HTML comments
    def _fences_and_comments(self):
        fence_char, fence_len, in_comment, fence_no = "", 0, False, 0
        # an indented code block: lines indented four or more, after a blank line or a heading and outside a list, or
        # continuing such a block; an HTML comment does not start inside one
        block_start, in_code, in_list = True, False, False
        for line in self.lines:
            raw = line.raw
            if fence_len:
                line.fence, line.fence_no = True, fence_no
                line.fence_info = self._info
                stripped = raw.strip()
                if stripped and set(stripped) == {fence_char} and len(stripped) >= fence_len and \
                        len(raw) - len(raw.lstrip()) <= 3:
                    fence_len = 0
                block_start = in_code = False
                continue
            expanded = raw.expandtabs(4)
            indent = len(expanded) - len(expanded.lstrip())
            if not in_comment and raw.strip():
                if indent >= 4 and (in_code or (block_start and not in_list)):
                    line.indented_code, in_code, block_start = True, True, False
                    continue
                in_code = False
                if LIST_ITEM_RE.match(raw):
                    in_list = True
                elif indent == 0:
                    in_list = False
                block_start = bool(indent < 4 and HEADING_RE.match(raw))
            elif not raw.strip():
                block_start = True
            if in_comment:
                end = raw.find("-->")
                if end < 0:
                    line.text, line.comment = " " * len(raw), True
                    continue
                in_comment = False
                raw = " " * (end + 3) + raw[end + 3:]
                line.text = raw
            opened = FENCE_OPEN_RE.match(raw) if not in_comment else None
            if opened and not (opened.group(1)[0] == "`" and "`" in opened.group(2)):
                fence_char, fence_len = opened.group(1)[0], len(opened.group(1))
                fence_no += 1
                self._info = opened.group(2).strip()
                line.fence, line.fence_no, line.fence_info = True, fence_no, self._info
                continue
            text, pos = raw, 0
            while True:
                start = text.find("<!--", pos)
                if start < 0:
                    break
                end = text.find("-->", start + 4)
                if end < 0:
                    text = text[:start] + " " * (len(text) - start)
                    in_comment = True
                    break
                text = text[:start] + " " * (end + 3 - start) + text[end + 3:]
                pos = end + 3
            line.text = text
            if line.raw.strip() and not text.strip():
                line.comment = True

    # ---- pass 2: headings, sections, zones
    def _headings_and_zones(self):
        current, current_heading, seen_section = None, 0, False
        for line in self.lines:
            if not (line.fence or line.comment):
                match = HEADING_RE.match(line.text)
                if match:
                    line.heading, line.level = match.group(2), len(match.group(1))
                    if line.level == 1 and self.title is None and not seen_section:
                        self.title = line
                    if line.level == 2:
                        seen_section = True
                        current = section_name(line.text)
                        current_heading = line.n
                        if current and current not in self.sections:
                            self.sections[current] = (line.n, [])
                        self.headings.append((heading_key(line.text), line.n, []))
            if self.headings and seen_section:
                self.headings[-1][2].append(line)
            line.section = current if seen_section else None
            if current and current in self.sections and self.sections[current][0] == current_heading:
                self.sections[current][1].append(line)
            heading_text = self.lines[current_heading - 1].text if seen_section else ""
            line.appendix = bool(seen_section and APPENDIX_RE.match(heading_text))
            if current in INSTRUCTION_SECTIONS:
                line.zone = "instruction"
            else:
                line.zone = "content"
        # the whole preamble before the first ## heading is instruction text; the # title itself names the task
        for line in self.lines:
            if line.section is not None:
                break
            if line is not self.title:
                line.zone = "instruction"
        # the identity paragraph: the first paragraph after the # title, before the first ## heading
        if self.title is not None:
            started = False
            for line in self.lines[self.title.n:]:
                if line.section is not None or line.heading:
                    break
                if line.comment or not line.raw.strip():
                    if started:
                        break
                    continue
                started = True
                self.identity.append(line)
                line.zone = "instruction"

    # ---- pass 3: exempt text, blanked before the content rules
    def line_at(self, offset):
        """The Line holding a character offset of `source`."""
        return self.lines[bisect.bisect_right(self.starts, offset) - 1]

    def _blank(self, spans):
        touched = {}
        for start, end in spans:
            first = bisect.bisect_right(self.starts, start) - 1
            last = bisect.bisect_right(self.starts, max(start, end - 1)) - 1
            for index in range(first, last + 1):
                line, base = self.lines[index], self.starts[index]
                a, b = max(start, base) - base, min(end, base + len(line.raw)) - base
                if b > a:
                    line.text = line.text[:a] + " " * (b - a) + line.text[b:]
                    touched[index] = line
        for line in touched.values():
            if not line.text.strip() or LEFTOVER_RE.fullmatch(line.text):
                line.verbatim = True

    def searchable(self):
        """The source with curly apostrophes straight, offsets kept."""
        return self.source.replace("\u2019", "'")

    def _published(self, counted):
        """Find each pack block by its chunks (fences included), and blank what matched;
        published_words counts the words of the blocks of `counted` (the matching pack's name)."""
        search = self.searchable()
        spans, words = [], []
        for block in self.blocks:
            if not any(chunk.regex.search(search) for chunk in block.chunks if chunk.identifying):
                continue
            hits, missing = [], []
            for chunk in block.chunks:
                found = [(m.start(), m.end()) for m in chunk.regex.finditer(search)]
                hits += found
                if not found:
                    missing.append(chunk.text)
            self.found[block.key] = Found(block, hits, missing, self.line_at(min(hits)[0]).n)
            spans += hits
            if block.pack == counted:
                words += hits
        self.published_words = sum(len(search[s:e].split()) for s, e in merge(words))
        self._blank(merge(spans))

    def _frozen(self, frozen):
        """Blank each guide block found whole: the skill's own text, which no content rule judges."""
        search = self.searchable()
        spans = []
        for block in frozen:
            found = block.search(search)
            if found:
                self.frozen_found[block.id] = (found.start(), found.end())
                spans.append((found.start(), found.end()))
        self._blank(merge(spans))

    def _person(self, rows):
        """Blank the "In the prompt as" text of each value and prohibition the person gave, inside its own section
        only: their words, which no content rule judges."""
        spans = []
        for key, text in rows:
            for name, n, lines in self.headings:
                if name != key or not lines:
                    continue
                start = self.starts[lines[0].n - 1]
                end = self.starts[lines[-1].n - 1] + len(lines[-1].raw)
                body = self.source[start:end].replace("\u2019", "'")
                spans += [(start + m.start(), start + m.end()) for m in phrase_re(text.replace("\u2019", "'")).finditer(body)]
        self._blank(spans)

    def outside_code(self):
        """The source with every fenced and indented code line blanked, offsets kept."""
        return "\n".join(" " * len(segment) if line.fence or line.indented_code else segment
                         for line, segment in zip(self.lines, self.segments))

    def section_text(self, key):
        """The raw text of the first `##` section whose heading_key is `key`, or None."""
        for name, n, lines in self.headings:
            if name == key:
                return "\n".join(line.raw for line in lines)
        return None

    def section_span(self, name):
        """(start, end) offsets in `source` of a frozen section's body (after its heading line), or None."""
        heading, lines = self.sections.get(name, (None, []))
        if heading is None:
            return None
        start = self.starts[heading - 1] + len(self.segments[heading - 1]) + 1
        last = lines[-1].n - 1
        end = self.starts[last] + len(self.segments[last])
        return min(start, end), end

    # ---- views
    def is_prose(self, line):
        return not (line.fence or line.verbatim or line.comment or line.appendix)

    def is_instruction_text(self, line):
        return line.zone == "instruction" and not (line.fence or line.verbatim or line.comment)

    def is_instruction_prose(self, line):
        return line.zone == "instruction" and self.is_prose(line)

    def is_content_prose(self, line):
        return line.zone == "content" and self.is_prose(line)

    def paragraphs(self, split_items=True, stop_at_appendix=False):
        """Prose units: runs of prose lines between blank or non-prose lines; headings are not units.
        With split_items, each list item (with its continuation lines) and each table row is a unit."""
        units, current = [], []
        for line in self.lines:
            if stop_at_appendix and line.appendix:
                break
            if not self.is_prose(line) or not line.raw.strip() or line.heading:
                if current:
                    units.append(current)
                current = []
                continue
            if split_items and current and (LIST_ITEM_RE.match(line.text) or TABLE_ROW_RE.match(line.text)
                                            or TABLE_ROW_RE.match(current[-1].text)):
                units.append(current)
                current = []
            current.append(line)
        if current:
            units.append(current)
        return units

    def wait_paragraph(self):
        units = self.paragraphs(split_items=False, stop_at_appendix=True)
        return units[-1] if units else []

    def section_lines(self, name):
        return self.sections.get(name, (None, []))[1]


def merge(spans):
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


# ================================================================= findings
class Finding(object):
    def __init__(self, rule, level, line, message, match=None, allowable=True):
        self.rule, self.level, self.line, self.message, self.match = rule, level, line, message, match
        self.reason = None
        self.allowable = allowable

    def as_dict(self):
        return {"rule": self.rule, "level": self.level, "line": self.line, "message": self.message,
                "match": self.match, "reason": self.reason}

    def as_text(self):
        where = " line %d" % self.line if self.line is not None else ""
        tail = " (lint-allow: %s)" % self.reason if self.level == "ALLOWED" else ""
        return "%s %s%s: %s%s" % (self.rule, self.level, where, self.message, tail)


def _hits(regexes, text):
    for regex in regexes:
        for match in regex.finditer(text):
            yield match


def _in_literal(line, match):
    return not line.literal[match.start():match.end()].strip()


def table_cells(text):
    """The cells of a Markdown table row, split on `|` outside inline code (`\\|` is a literal bar), stripped."""
    body = text.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    cells, current, i, code = [], [], 0, 0
    while i < len(body):
        char = body[i]
        if char == "`":
            j = i
            while j < len(body) and body[j] == "`":
                j += 1
            run = j - i
            if not code and re.search(r"(?<!`)%s(?!`)" % ("`" * run), body[j:]):
                code = run
            elif code == run:
                code = 0
            current.append(body[i:j])
            i = j
            continue
        if char == "\\" and body[i + 1:i + 2] == "|":
            current.append("|")
            i += 2
            continue
        if char == "|" and not code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        i += 1
    cells.append("".join(current).strip())
    return cells


class Linter(object):
    def __init__(self, prompt, framing, decisions_text=None, context=None):
        self.p = prompt
        self.f = framing
        self.decisions = decisions_text
        self.c = context or Context(framing)
        self.findings = []
        self.allowances = []        # {rule, reason, block: (first, last) or None}, from decisions.md § Review (P30)
        self.conflicts = framing_conflicts(framing, self.c.skill_dir)
        self.text_conflicts = self.work_alone_conflicts()   # [(line, message, sentence)]

    def add(self, *args, **kwargs):
        self.findings.append(Finding(*args, **kwargs))

    def skipped(self, rule, message):
        self.add(rule, "SKIPPED", None, message, allowable=False)

    def missing(self, *keys):
        return [k for k in keys if not self.f.get(k)]

    def where(self, regex):
        """The line number of the first match of `regex` in the raw prompt, or None."""
        match = regex.search(self.p.source)
        return self.p.line_at(match.start()).n if match else None

    # ---------------------------------------------------------- the framing's structure
    def work_alone_conflicts(self):
        """seat=implementer or lead in a prompt whose executor is told it works alone, outside code blocks; the framing
        or the prompt is wrong, so P38 errs and P13 checks only RS1 and RS13. On quick the framing rule already says it
        (size=quick requires seat=alone)."""
        seat = self.f.get("seat")
        if seat not in ("implementer", "lead") or self.f.get("size") == "quick":
            return []
        free, out = self.p.outside_code(), []
        for sentence in self.c.alone_sentences():
            match = phrase_re(sentence).search(free)
            if match:
                out.append((self.p.line_at(match.start()).n, "seat=%s, yet the prompt says %r: an executor that dispatches "
                            "no subagent is `alone` (references/methods.md §12); frame the run alone, or take the sentence "
                            "out" % (seat, sentence), sentence))
        return out

    def completions(self, keys):
        """(the keys the framing leaves unknown, every consistent framing that fills them)."""
        unknown = [k for k in keys if not self.f.get(k)]
        out = []
        for values in itertools.product(*(ENUM_VALUES[k] for k in unknown)):
            filled = dict(self.f)
            filled.update(zip(unknown, values))
            if not seat_conflicts(filled):
                out.append(filled)
        return unknown, out

    def ledger_kept(self):
        """True, False or None (unknown): the ceremony table keeps a ledger where seat is not alone, or deep,
        unattended or run other than one-session; never on quick."""
        f = self.f
        if f.get("size") == "quick":
            return False
        _, framings = self.completions(("size", "seat", "autonomy", "run"))
        kept = {fill["size"] != "quick" and (fill["seat"] != "alone" or fill["size"] == "deep" or
                                             fill["autonomy"] == "unattended" or fill["run"] != "one-session")
                for fill in framings}
        return kept.pop() if len(kept) == 1 else None

    def has_seats(self):
        """True, False or None (unknown): the run dispatches seats (seat=implementer or lead). An unknown seat is
        settled when every consistent framing agrees (deep, a review seat or a long run leave no room for alone)."""
        seat = self.f.get("seat")
        if seat:
            return seat != "alone"
        _, framings = self.completions(("size", "seat", "review", "run"))
        seats = {fill["seat"] != "alone" for fill in framings}
        return seats.pop() if len(seats) == 1 else None

    # ---------------------------------------------------------- shared
    def _dedupe(self, rule, line, cands):
        kept = []
        for level, m, message in sorted(cands, key=lambda c: (LEVEL_ORDER[c[0]], c[1].start())):
            if any(m.start() < e and s < m.end() for s, e in kept):
                continue
            kept.append((m.start(), m.end()))
            self.add(rule, level, line.n, "%s: %r" % (message, m.group(0)), m.group(0))

    # ---------------------------------------------------------- P04
    def p04(self):
        """The Seats-and-models form the ceremony table gives the framing, taken from the framing's guide: nothing on
        quick or on a run that works alone; with seats, `## Seats and models` holds its seats-models block (and its
        headless-line wherever the prompt starts one)."""
        seat = "alone" if self.f.get("size") == "quick" else self.f.get("seat")
        if seat == "alone":
            return
        if not seat:
            self.skipped("P04", "needs the framing's seat (a run with seats carries the guide's seats-models block)")
            return
        if not self.f.get("model"):
            self.skipped("P04", "needs the framing's model (the seats-models block has a text for a named model and "
                                "one for %s)" % MODEL_CHOOSE)
            return
        if self.c.guide is None:
            self.skipped("P04", "needs the framing's harness guide (%s)" % self.c.guide_shown())
            return
        self._p04_block("seats-models", "Seats and models")
        headless = self.c.frozen("headless-line", prompt_verbatim)
        if headless and headless[0].lines:
            opening = phrase_re(" ".join(headless[0].lines[0].split()[:2]))   # its label: the prompt starts headless seats
            if opening.search(self.p.source):
                self._p04_block("headless-line", "Seats and models")

    def _p04_block(self, block_id, section):
        """The section holds the block; a miss is reported where the block stops matching."""
        blocks = self.c.frozen(block_id, prompt_verbatim)
        where = "`## %s`" % section
        if not blocks:
            self.skipped("P04", "the guide (%s) has no `%s` block" % (self.c.guide_shown(), block_id))
            return
        unknown = set().union(*(block.unknown for block in blocks))
        if unknown:
            self.skipped("P04", "the guide's `%s` block has fragments the framing does not settle (%s): needs the "
                                "framing's model, effort and launch" % (block_id, ", ".join(sorted(unknown))))
            return
        span = self.p.section_span(section)
        if span is None:
            self.add("P04", "ERROR", None, "%s is missing, so it cannot carry the guide's `%s` block" % (where, block_id),
                     allowable=False)
            return
        heading = self.p.sections[section][0]
        body = self.p.source[span[0]:span[1]].replace("\u2019", "'")
        if any(block.search(body) for block in blocks):
            return
        (low, wrapped), block = max(((block.stops_at(body), block) for block in blocks),
                                    key=lambda item: (item[0][1], item[0][0]))
        if wrapped:
            self.add("P04", "ERROR", heading, "%s holds the guide's `%s` block with a command line split across lines; "
                     "keep each command whole on one line, inside one inline code span" % (where, block_id),
                     block_id, allowable=False)
        else:
            stop = block.lines[min(low, len(block.lines) - 1)].strip()
            self.add("P04", "ERROR", heading, "%s is not the guide's `%s` block with its slots filled for this "
                     "framing: it stops matching at its line %d, %r" % (where, block_id, low + 1, stop[:120]),
                     stop[:60], allowable=False)

    # ---------------------------------------------------------- P05
    def p05(self):
        for line in self.p.lines:
            if line.zone != "instruction" or line.verbatim or line.comment:
                continue
            cands = [("WARN", m, "a model named in a brief's text selects nothing") for m in _hits([P05_MODEL_LINE], line.text)]
            cands += [("WARN", m, "a model named in a brief's text selects nothing") for m in _hits(P05_PHRASES, line.text)]
            self._dedupe("P05", line, cands)

    # ---------------------------------------------------------- P06
    def p06(self):
        closing = set(re.findall(r"</([A-Za-z][\w:-]*)\s*>", self.p.source))
        for line in self.p.lines:
            if self.p.is_instruction_text(line):
                for m in _hits(P06_WORDS, line.text):
                    if not _in_literal(line, m):
                        self.add("P06", "ERROR", line.n, "undecided value in instruction text: %r" % m.group(0), m.group(0))
            elif self.p.is_content_prose(line):
                for m in _hits(P06_WORDS, line.text):
                    if not _in_literal(line, m):
                        self.add("P06", "WARN", line.n, "undecided value in a content section: %r" % m.group(0), m.group(0))
            if self.p.is_prose(line):
                for m in P06_SLOT.finditer(line.text):
                    inner = m.group(0)[1:-1]
                    name = inner.split()[0] if inner.split() else inner
                    if _in_literal(line, m) or name in closing or "://" in inner or "@" in inner:
                        continue
                    self.add("P06", "WARN", line.n, "angle-bracket slot left in the prompt: %r" % m.group(0), m.group(0))
        markers = []
        for line in self.p.lines:
            if line.verbatim:
                continue
            for m in P06_MARKER.finditer(line.raw):
                markers.append((line.n, m.group(0), normalise(m.group(1)).lower()))
        if not markers:
            return
        if self.decisions is None:
            self.skipped("P06", "the placeholder table check needs --decisions (%d `[you fill this in:` marker(s))" % len(markers))
            return
        table = normalise(_md_section(self.decisions, "Placeholders in the prompt")).lower()
        for n, marker, inner in markers:
            if not inner or inner not in table:
                self.add("P06", "ERROR", n, "%s is missing from decisions.md's `## Placeholders in the prompt` table" % marker,
                         marker, allowable=False)

    # ---------------------------------------------------------- P07
    def p07(self):
        folder = self.f.get("folder")
        if folder is not None:
            start = P07_FOLDER_START.match(folder)
            unsafe = sorted(set(P07_FOLDER_UNSAFE.findall(folder[start.end():] if start else folder)))
            problems = [] if start else ["does not start with /, $HOME or ${HOME} (never ~: write $HOME for a ~)"]
            if unsafe:
                problems.append("holds %s, which inside double quotes breaks the command, runs code or meets history "
                                "expansion" % " ".join(unsafe))
            if problems:
                self.add("P07", "ERROR", None, "decisions.md's framing folder=%s %s; it fills cd \"{FOLDER}\""
                         % (folder, " and ".join(problems)), folder, allowable=False)
        heading, lines = self.p.sections.get("Working folder", (None, []))
        if heading is None:
            self.add("P07", "ERROR", None, "`## Working folder` is missing", allowable=False)
            return
        if not any(P07_ABS.search(l.text) for l in lines[1:] if not l.comment):
            self.add("P07", "ERROR", heading, "`## Working folder` holds no absolute path (/..., ~/..., $HOME/... or X:\\...)",
                     allowable=False)

    # ---------------------------------------------------------- P08
    def p08(self):
        para = self.p.wait_paragraph()
        if not para or not para[0].text.lstrip().startswith(WAIT_RULE_LABEL):
            where = para[0].n if para else None
            self.add("P08", "ERROR", where, "the last prose paragraph before the appendices must start with %s" % WAIT_RULE_LABEL,
                     allowable=False)
            return
        text = normalise(" ".join(l.text for l in para))
        if not any(re.search(re.escape(p), text, PHRASE_FLAGS) for p in WAIT_RULE_PHRASES):
            self.add("P08", "WARN", para[0].n, "the wait rule says no 'until', 'do not stop', 'only when', 'done when' or the like",
                     allowable=False)

    # ---------------------------------------------------------- P09
    def p09(self):
        lines = self.p.section_lines("The bar")
        i = 1
        while i < len(lines):
            line = lines[i]
            if line.fence or line.verbatim or line.comment:
                i += 1
                continue
            row = P09_ROW.match(line.text)
            item = P09_ITEM.match(line.text) if not TABLE_ROW_RE.match(line.text) else None
            if not (row or item):
                i += 1
                continue
            unit = [line]
            j = i + 1
            if not row:
                while j < len(lines):
                    nxt = lines[j]
                    if nxt.fence:
                        while j < len(lines) and lines[j].fence:
                            unit.append(lines[j])
                            j += 1
                        break
                    if not nxt.raw.strip() or nxt.heading or LIST_ITEM_RE.match(nxt.text) or TABLE_ROW_RE.match(nxt.text):
                        break
                    unit.append(nxt)
                    j += 1
            if not any("`" in l.raw for l in unit):
                label = (row or item).group(1) or line.text.strip()[:30]
                self.add("P09", "WARN", line.n, "bar item %s names no command or path in backticks" % label)
            i = max(j, i + 1)

    # ---------------------------------------------------------- P10
    def p10(self):
        """A paragraph over 800 characters, the run rules aside: each is the template's own text under its frozen label
        (RS8 with its unattended text runs past 800), never the writer's to shorten."""
        for unit in self.p.paragraphs(split_items=True):
            if unit[0].section == "Run rules" and \
                    any(LIST_ITEM_RE.sub("", unit[0].raw, 1).lstrip().startswith(label) for label in RS_LABELS.values()):
                continue
            text = " ".join(l.raw.strip() for l in unit)
            if len(text) > 800:
                self.add("P10", "WARN", unit[0].n, "paragraph of %d characters (over 800)" % len(text))

    # ---------------------------------------------------------- P11
    def p11(self):
        if "decisions.md" in self.p.source:
            return
        # with --decisions only an id the decisions log holds is a citation, inside a literal span too ("per `D4`");
        # without --decisions a literal span is never one, so a library name such as `D3` stays clean
        logged = None
        if self.decisions is not None:
            logged = {m.group(1) for m in (P11_LOG_ROW.match(l) for l in _md_section(self.decisions, "Decisions log").split("\n")) if m}
        for line in self.p.lines:
            if not self.p.is_prose(line):
                continue
            ids = [m.group(0) for m in P11_DID.finditer(line.text)
                   if (m.group(0) in logged if logged is not None else not _in_literal(line, m))]
            if ids:
                self.add("P11", "ERROR", line.n, "cites %s but the prompt never names decisions.md as a read-on-demand input"
                         % ", ".join(sorted(set(ids))), ids[0])

    # ---------------------------------------------------------- P12
    def p12(self):
        patterns = list(P12_FIXED)
        if self.c.skill_name:
            patterns.append(r"\bthe %s skill\b" % re.escape(self.c.skill_name))
        errors = [re.compile(p, re.I) for p in patterns]
        for line in self.p.lines:
            if self.p.is_instruction_text(line):
                for m in _hits(errors, line.text):
                    if not _in_literal(line, m):
                        self.add("P12", "ERROR", line.n, "depends on something the executor cannot reach: %r" % m.group(0), m.group(0))
                for m in P12_SESSION.finditer(line.text):
                    if not _in_literal(line, m):
                        self.add("P12", "WARN", line.n, "%r: the executor's own session, or this conversation?" % m.group(0), m.group(0))
            elif self.p.is_content_prose(line):
                for m in _hits(errors, line.text):
                    if not _in_literal(line, m):
                        self.add("P12", "WARN", line.n, "reference to the writing session in a content section: %r" % m.group(0), m.group(0))

    # ---------------------------------------------------------- P13
    def required_rs(self):
        """(required RS numbers, why some were not checked or None): the ceremony table's row of the framing's seat
        (quick: its own) with every modifier that holds. A key the framing leaves unknown requires only what every
        consistent value of it would require (so RS1 and RS13 always); an inconsistent framing (P38) requires RS1 and
        RS13 and nothing from the modifiers."""
        if self.f.get("size") == "quick":
            return set(ROW_RS["quick"]), None
        if seat_conflicts(self.f) or self.text_conflicts:
            return set(ROW_RS["quick"]), "the framing is inconsistent (P38): only RS1 and RS13 checked"
        unknown, framings = self.completions(RS_KEYS)
        sets = [run_rules_for(fill) for fill in framings] or [set(ROW_RS["quick"])]
        need, union = set.intersection(*sets), set.union(*sets)
        why = None
        if union != need:
            why = "labels that depend on %s not checked (framing unknown)" % ", ".join(unknown)
        return need, why

    def p13(self):
        if not self.f.get("size"):
            self.skipped("P13", "needs the framing's size")
            return
        need, why = self.required_rs()
        heading, lines = self.p.sections.get("Run rules", (None, []))
        if heading is None:
            self.add("P13", "ERROR", None, "`## Run rules` is missing", allowable=False)
            return
        body = "\n".join(l.raw for l in lines if not l.comment)
        for rs in sorted(need):
            if RS_LABELS[rs] not in body:
                self.add("P13", "ERROR", heading, "RS%d %s is missing from `## Run rules`" % (rs, RS_LABELS[rs]),
                         RS_LABELS[rs], allowable=False)
        if why:
            self.skipped("P13", why)

    # ---------------------------------------------------------- P14, P20, P21, P24
    def _prose_rule(self, rule, regexes, instr_level, content_level, message):
        for line in self.p.lines:
            if self.p.is_instruction_prose(line):
                level = instr_level
            elif self.p.is_content_prose(line):
                level = content_level
            else:
                continue
            if not level:
                continue
            for m in _hits(regexes, line.text):
                if not _in_literal(line, m):
                    self.add(rule, level, line.n, "%s: %r" % (message, m.group(0)), m.group(0))

    def p14(self):
        self._prose_rule("P14", P14_PATTERNS, "WARN", "WARN", "a generic verification line adds cost, not evidence; name "
                                                             "the check")

    def p20(self):
        self._prose_rule("P20", P20_PATTERNS, "WARN", None, "a tool-call budget stops builders short")

    def p21(self):
        for name, (heading, lines) in self.p.sections.items():
            if any(P21_PLATEAU.search(l.raw) for l in lines):
                continue
            for line in lines:
                if not self.p.is_instruction_prose(line):
                    continue
                for m in P21_PATTERN.finditer(line.text):
                    if not _in_literal(line, m):
                        self.add("P21", "WARN", line.n, "a loop capped by a count in a section that never says 'plateau': %r"
                                 % m.group(0), m.group(0))

    def p24(self):
        for line in self.p.lines:
            if not self.p.is_prose(line):
                continue
            for m in _hits(P24_WORDS, line.text):
                if not _in_literal(line, m):
                    self.add("P24", "WARN", line.n, "soft adjective with no metric: %r" % m.group(0), m.group(0))

    # ---------------------------------------------------------- P22, P23, P25, P26
    def p22(self):
        machine = self.f.get("machine")
        if machine == "personal":
            return
        lines = self.p.section_lines("Run rules") + self.p.section_lines("Definition of done and final report")
        if any(P22_PUSH.search(l.raw) for l in lines):
            return
        if not machine:
            self.skipped("P22", "needs the framing's machine")
            return
        self.add("P22", "ERROR", None, "machine=disposable: neither `## Run rules` nor `## Definition of done and final report` "
                 "says to push", allowable=False)

    def p23(self):
        size = self.f.get("size")
        if not size:
            self.skipped("P23", "needs the framing's size")
            return
        if size == "quick":
            required, conditional = list(REQUIRED_QUICK), []
        else:
            seat = self.f.get("seat")
            required, conditional = list(REQUIRED_ABOVE_QUICK), [
                (("Seats and models",), self.has_seats(), "where the run has seats", "the framing's seat"),
                (("Subagent contracts",), None if not seat else seat == "lead", "when seat=lead", "the framing's seat"),
                (("Progress and recoverability",), self.ledger_kept(), "where a ledger is kept",
                 "whether a ledger is kept (seat, size, autonomy, run)")]
        for name in required:
            if name not in self.p.sections:
                self.add("P23", "ERROR", None, "required heading `## %s` is missing (size %s)" % (name, size), allowable=False)
        for names, needed, when, unknown in conditional:
            for name in names:
                if name in self.p.sections or needed is False:
                    continue
                if needed:
                    self.add("P23", "ERROR", None, "required heading `## %s` is missing (size %s, %s)" % (name, size, when),
                             allowable=False)
                else:
                    self.skipped("P23", "`## %s` is required %s; %s is unknown" % (name, when, unknown))

    def p25(self):
        size = self.f.get("size")
        if not size:
            self.skipped("P25", "needs the framing's size")
            return
        words = sum(len(l.raw.split()) for l in self.p.lines)
        if words > P25_LIMITS[size]:
            self.add("P25", "WARN", None, "%d words, over %d for a %s prompt: a split signal, not a gate"
                     % (words, P25_LIMITS[size], size))

    def p26(self):
        size = self.f.get("size")
        if size == "quick":
            return
        if not size:
            self.skipped("P26", "needs the framing's size")
            return
        heading, lines = self.p.sections.get("The bar", (None, []))
        if not any(P26_WEAK.match(l.text) for l in lines if not (l.comment or l.fence)):
            self.add("P26", "ERROR", heading, "`## The bar` has no line starting `A weak result`", allowable=False)

    # ---------------------------------------------------------- P29
    def p29(self):
        if self.p.title is None:
            self.add("P29", "ERROR", None, "no `# ` title, so no identity paragraph", allowable=False)
            return
        if not self.p.identity:
            self.add("P29", "ERROR", self.p.title.n, "no identity paragraph after the title", allowable=False)

    # ---------------------------------------------------------- P30
    def p30(self):
        """Allowances live in decisions.md `## Review`, one line each (ALLOWANCE_FORM). A record is a line that starts
        with a rule id and names lint-allow (prose that names lint-allow is not one). A record that does not parse, an
        unknown or non-allowable rule, an empty reason, an anchor no prompt line holds or more than one does, or any
        anchor on a rule allowable only in a line-less branch (P34 (e)), is an ERROR; a valid record is an allowance
        apply_allows uses."""
        if self.decisions is None:
            return
        for raw in record_lines(_md_section(self.decisions, "Review")):
            if "lint-allow" not in raw or not RECORD_START_RE.match(raw):
                continue
            shown = raw.strip()
            match = ALLOWANCE_RE.match(raw)
            if not match:
                self.add("P30", "ERROR", None, "decisions.md `## Review` line %r starts with a rule id and names lint-allow "
                         "but does not parse; the form is `%s`" % (shown, ALLOWANCE_FORM), shown, allowable=False)
                continue
            rule, body = match.group(1), match.group(2)
            reason, anchor = (body.split("| at:", 1) + [None])[:2]
            reason, problems, block = reason.strip(), [], None
            if rule not in RULE_IDS:
                problems.append("names an unknown rule %s" % rule)
            elif rule in ALLOWABLE_BRANCHES and anchor is not None:
                problems.append("anchors %s, whose only allowable branch, %s, has no prompt line: write the record "
                                "without `| at:`" % (rule, ALLOWABLE_BRANCHES[rule]))
                anchor = None
            elif rule not in ALLOWABLE and rule not in ALLOWABLE_BRANCHES:
                problems.append("names %s, which cannot be allowed (it holds the frozen contract)" % rule)
            if not reason:
                problems.append("has an empty reason")
            if anchor is not None:
                anchor = anchor.strip()
                holders = [line for line in self.p.lines if anchor and anchor in line.raw]
                if not anchor:
                    problems.append("has an empty `at:` anchor")
                elif not holders:
                    problems.append("anchors to text no prompt line holds")
                elif len(holders) > 1:
                    problems.append("anchors to text %d prompt lines hold (%s); quote more of one line"
                                    % (len(holders), ", ".join(str(line.n) for line in holders)))
                else:
                    block = self.block_around(holders[0])
            if problems:
                self.add("P30", "ERROR", None, "decisions.md `## Review` line %r %s" % (shown, " and ".join(problems)),
                         shown, allowable=False)
            else:
                self.allowances.append({"rule": rule, "reason": reason, "block": block})

    # ---------------------------------------------------------- P32
    def p32(self):
        """ERROR, never allowable: `<!--` anywhere in the prompt outside fences, indented code blocks and inline code
        spans, one finding per line. Provenance lives in decisions.md (§ Guidance put in, § Review), never in the
        delivered prompt."""
        for line in self.p.lines:
            if line.fence or line.indented_code or "<!--" not in line.raw or "<!--" not in mask_code(line.raw):
                continue
            self.add("P32", "ERROR", line.n, "an HTML comment in the delivered prompt (a marker, a lint-allow line or a "
                     "template comment); the record is decisions.md", "<!--", allowable=False)

    # ---------------------------------------------------------- P33
    def p33(self):
        """ERROR, never allowable: a guidance pack's block earns its place by a task fact and goes in as the pack gives
        it. With no pack in the folder it says nothing."""
        if not self.p.blocks:
            return
        found = self.p.found
        model = self.f.get("model")
        pack = self.c.pack
        if found and not model:
            self.skipped("P33", "(c) needs the framing's model (whose pack the prompt may draw on)")
        elif model:
            for hit in sorted(found.values(), key=lambda h: h.line):
                if pack is None or hit.block.pack != pack.name:
                    why = "two or more packs match it, so none is read" if self.c.pack_count > 1 else \
                        "and model=%s reads no pack" % MODEL_CHOOSE if model == MODEL_CHOOSE else \
                        "a pack that does not match model=%s" % model
                    self.p33_error(hit.line, "(c) %s comes from %s, %s" % (self.shown(hit.block), hit.block.pack, why),
                                   hit.block.name)
        for hit in sorted(found.values(), key=lambda h: h.line):
            if hit.block.adapt_nothing and hit.missing:
                self.p33_error(hit.line, "(e) %s is a pack block whose Adapt is \"nothing\", but %d of its %d chunks are not "
                               "in the prompt as the pack gives them (first: %r): the text was altered"
                               % (self.shown(hit.block), len(hit.missing), len(hit.block.chunks), hit.missing[0]),
                               hit.block.name)
        if pack is None:
            return
        own = [hit for hit in found.values() if hit.block.pack == pack.name]
        if self.decisions is None:
            if own:
                self.skipped("P33", "(a), (b), (d) need --decisions (decisions.md `## %s`)" % GUIDANCE_SECTION)
            return
        rows = [dict(zip(GUIDANCE_HEADER, cells + [""] * len(GUIDANCE_HEADER)))
                for cells in md_table(_md_section(self.decisions, GUIDANCE_SECTION), GUIDANCE_HEADER)[1]]
        named = [(row, self.block_named(row["block"], pack)) for row in rows]
        recorded = {block.name for _, block in named if block is not None}
        for hit in sorted(own, key=lambda h: h.line):
            if hit.block.name not in recorded:
                self.p33_error(hit.line, "(a) %s is in the prompt with no row in decisions.md `## %s` (the task fact that "
                               "puts it in)" % (self.shown(hit.block), GUIDANCE_SECTION), hit.block.name)
        for row, block in named:
            if block is None:
                self.add("P33", "WARN", None, "pack block (b) decisions.md `## %s` row %r names no `###` block of %s "
                         "(its name as the pack writes it, the tag optional)" % (GUIDANCE_SECTION, row["block"], pack.name),
                         row["block"], allowable=False)
                continue
            if block.adapt_nothing and block.key not in found:
                self.p33_error(None, "(b) decisions.md `## %s` records %s, whose Adapt is \"nothing\", but the prompt "
                               "does not carry it" % (GUIDANCE_SECTION, self.shown(block)), block.name)
            fact = row["task fact that triggers it"]
            keys, prose = when_keys(block.when)
            if not self.fact_holds(fact, keys, prose):
                if keys:
                    wanted = "one of the framing keys its When names, with the framing's value (%s)%s" % (
                        "; ".join("%s=%s" % (k, "|".join(sorted(v))) for k, v in sorted(keys.items())),
                        ", or a live D- or W-id other than D1 and D2 for its other branch" if prose else "")
                else:
                    wanted = "a live D- or W-id other than D1 and D2 (its When names no framing key)"
                self.p33_error(None, "(d) the row for %r gives the fact %r; it must cite %s" % (row["block"], fact, wanted),
                               row["block"])

    def p33_error(self, line, message, match=None):
        self.add("P33", "ERROR", line, "pack block %s" % message, match, allowable=False)

    @staticmethod
    def shown(block):
        return "`### %s [%s]`" % (block.name, block.tag)

    @staticmethod
    def block_named(cell, pack):
        """The pack block a § Guidance put in row's Block cell names (its `###` name, the tag optional), or None."""
        name = heading_key(re.sub(r"\s*\[[^\[\]]*\]\s*$", "", cell.replace("*", "")))
        return next((block for block in pack.blocks if heading_key(block.name) == name), None)

    def fact_holds(self, fact, keys, prose):
        """When the block's When names framing keys, the fact cites one of them with a value the When names and the
        framing holds; otherwise (or for a When's branch in prose) a live D- or W-id other than D1 and D2, the harness
        row and the autonomy row. Whether the fact is true stays the reviewer's."""
        for key, value in re.findall(r"\b([a-z]+)=([A-Za-z0-9_-]+)", fact):
            if value in keys.get(key, ()) and self.f.get(key) == value:
                return True
        if keys and not prose:
            return False
        live = {row["id"] for row in decision_rows(self.decisions) if row["status"].lower().startswith("live")}
        if any(d in live and d not in ("D1", "D2") for d in re.findall(r"\bD\d+\b", fact)):
            return True
        words = {cells[0].strip("`* ") for cells in md_table(_md_section(self.decisions, WORDS_SECTION), WORDS_HEADER)[1]}
        return any(w in words for w in re.findall(r"\bW\d+\b", fact))

    # ---------------------------------------------------------- P34
    def p34(self):
        """ERROR, never allowable but (e): autonomy is the person's (the Autonomy row), and what depends on it follows
        it. (a)-(c) and (e), the row against the words it quotes, need --decisions; (d) reads the prompt: RS8's text
        follows autonomy and launch=. (e) is allowed by a § Review record without `| at:`: a quote can negate a listed
        phrase."""
        autonomy, launch = self.f.get("autonomy"), self.f.get("launch")
        if self.decisions is None:
            self.skipped("P34", "(a)-(c) and (e) need --decisions (the Autonomy row of the decisions log)")
        else:
            rows = [row for row in decision_rows(self.decisions)
                    if row["topic"].strip("`* ").lower() == "autonomy" and row["status"].lower().startswith("live")]
            if len(rows) != 1:
                self.p34_error(None, "(a) the decisions log has %d live rows whose Topic is Autonomy, not exactly one: "
                               "autonomy is the person's words or the answer to the autonomy question, never assumed"
                               % len(rows))
            else:
                row = rows[0]
                decision = row["decision"].strip("`* ").lower()
                if not autonomy:
                    self.skipped("P34", "(b) needs the framing's autonomy")
                elif not decision.startswith(autonomy):
                    self.p34_error(None, "(b) the Autonomy row's Decision %r does not start with the framing's autonomy=%s"
                                   % (row["decision"], autonomy))
                source = row["source"].strip("`* ")
                quotes = [normalise(next(g for g in m.groups() if g)) for m in QUOTED_RE.finditer(row["rationale"])]
                if source not in ("Stated", "Interview"):
                    self.p34_error(None, "(c) the Autonomy row's Source is %r, not Stated or Interview" % row["source"])
                elif source == "Stated" and not quotes:
                    self.p34_error(None, "(c) the Autonomy row is Stated but its Rationale quotes none of the person's "
                                         "words (in \"…\", “…”, «…» or ‘…’)")
                said = next((a for a in ("unattended", "attended") if decision.startswith(a)), autonomy)
                if quotes and said:
                    self._p34_quotes(said, quotes)
        texts = {"ATTENDED": RS8_ATTENDED, "HEADLESS": RS8_HEADLESS, "OTHER": RS8_OTHER}
        present = {name: phrase_re(text).search(self.p.source) for name, text in texts.items()}
        if autonomy == "attended":
            wrong, why = ("HEADLESS", "OTHER"), "an attended run"
        elif autonomy == "unattended" and launch == "headless":
            wrong, why = ("ATTENDED", "OTHER"), "an unattended run launched headless"
        elif autonomy == "unattended" and launch in ENUM_VALUES["launch"]:
            wrong, why = ("ATTENDED", "HEADLESS"), "an unattended run launched %s" % launch
        else:
            wrong, why = (), ""
            if (autonomy == "unattended" or not autonomy) and any(present.values()):
                self.skipped("P34", "(d) RS8's text follows the framing's autonomy and launch: needs the framing's %s"
                             % " and ".join(self.missing("autonomy", "launch")))
        for name in wrong:
            match = present[name]
            if match:
                self.p34_error(self.p.line_at(match.start()).n, "(d) RS8 carries its %s text (%r) on %s; it takes the %s "
                               "text" % (name, texts[name], why, "ATTENDED" if autonomy == "attended" else
                                                                   ("HEADLESS" if launch == "headless" else "OTHER")),
                               texts[name])

    def _p34_quotes(self, said, quotes):
        """The Autonomy row against the words it quotes. A quote holding a phrase of the other autonomy's list
        (SKILL.md's) and none of its own contradicts the row: ERROR. Phrases of both lists: the words settle neither,
        so the autonomy question is asked: WARN."""
        lists = self.c.autonomy_lists
        if lists is None:
            self.skipped("P34", "(e) the Autonomy row's quoted words are not checked against SKILL.md's phrase lists: "
                                "SKILL.md was not found or holds no autonomy paragraph")
            return
        other = "attended" if said == "unattended" else "unattended"
        hits = {a: [p for p in lists[a] if any(holds_phrase(q, p) for q in quotes)] for a in (said, other)}
        if hits[other] and not hits[said]:
            self.p34_error(None, "(e) the Autonomy row says %s, but its Rationale quotes %s, which settles %s (SKILL.md's "
                                 "autonomy paragraph); a quote that negates the phrase (\"it must not run unattended\") is "
                                 "kept with a § Review line `P34 lint-allow: <reason>`"
                           % (said, ", ".join('"%s"' % p for p in hits[other]), other), hits[other][0], allowable=True)
        elif hits[other]:
            self.add("P34", "WARN", None, "autonomy (e) the Autonomy row says %s, and its Rationale quotes words of both "
                                          "lists (%s): they settle neither, so the autonomy question decides"
                     % (said, ", ".join('"%s"' % p for p in hits[said] + hits[other])), hits[other][0])

    def p34_error(self, line, message, match=None, allowable=False):
        self.add("P34", "ERROR", line, "autonomy %s" % message, match, allowable=allowable)

    # ---------------------------------------------------------- P35
    def p35(self):
        """ERROR, never allowable: every wish, prohibition, value and quality demand the person stated is a row of
        decisions.md § The person's words, carried at its section in the words it gives and checked by the bar."""
        if self.decisions is None:
            self.skipped("P35", "needs --decisions (decisions.md `## %s`)" % WORDS_SECTION)
            return
        rows = md_table(_md_section(self.decisions, WORDS_SECTION), WORDS_HEADER)[1]
        if not _md_has_section(self.decisions, WORDS_SECTION) or not rows:
            self.p35_error("(a) decisions.md `## %s` is missing or has no row under its header `%s`: the person's "
                           "words are walked line by line against the prompt" % (WORDS_SECTION, WORDS_HEADER_LINE))
            return
        bar = self.bar_ids()
        for cells in rows:
            row = dict(zip(WORDS_HEADER, cells + [""] * len(WORDS_HEADER)))
            wid = row["id"].strip("`* ") or "a row"
            kind = row["kind"].strip("`* ").lower()
            if kind not in WORDS_KINDS:
                self.p35_error("(b) %s has Kind %r, not one of %s" % (wid, row["kind"], ", ".join(WORDS_KINDS)), wid)
            carried = unquote(row["in the prompt as"])
            target = section_target(row["section"])
            if target is None:
                self.p35_error("(c) %s's Section %r is neither a prompt `##` heading, `Launch`, nor `not in the prompt: "
                               "<reason>`" % (wid, row["section"]), wid)
            elif target != "outside":
                body = self.p.section_text(target)
                if body is None:
                    self.p35_error("(c) %s names the section %r, which the prompt does not have" % (wid, row["section"]), wid)
                elif not carried or not phrase_re(carried.replace("\u2019", "'")).search(body.replace("\u2019", "'")):
                    self.p35_error("(c) %s's text %r is not in the prompt's `## %s`: the person's words were dropped or "
                                   "changed" % (wid, carried, row["section"].strip("`# ")), wid)
            if kind == "value" and normalise(unquote(row["words"])) not in normalise(carried):
                self.p35_error("(d) %s is a value, and its Words %r are not inside its text in the prompt %r"
                               % (wid, unquote(row["words"]), carried), wid)
            lacking = [token for token in identifiers(unquote(row["words"])) if not carries_identifier(carried, token)]
            if kind == "prohibition" and lacking:   # a prohibition's paths and identifiers, word for word
                self.add("P35", "WARN", None, "the person's words (d) %s is a prohibition naming %s, which its text in the "
                         "prompt %r does not carry as written" % (wid, ", ".join("`%s`" % x for x in lacking), carried),
                         wid, allowable=False)
            checked = row["checked by"].replace("`", "").replace("*", "").strip()
            none = re.match(r"none\s*:\s*(.*)$", checked, re.I)
            if none and kind == "quality":
                self.p35_error("(e) %s is a quality demand: it becomes a bar item (a command with its exit code, or an "
                               "observation with its named artefact), never `none:`" % wid, wid)
            elif none and not none.group(1).strip():
                self.p35_error("(e) %s is checked by `none:` with no reason" % wid, wid)
            elif not none:
                ids = re.findall(r"\bT\d+\b", checked)
                lacking = [t for t in ids if t not in bar]
                if not ids or lacking:
                    self.p35_error("(e) %s's Checked by %r is neither a T id `## The bar` holds as an item%s nor "
                                   "`none: <reason>`" % (wid, row["checked by"], " (%s is not)" % ", ".join(lacking)
                                                         if lacking else ""), wid)

    def p35_error(self, message, match=None):
        self.add("P35", "ERROR", None, "the person's words %s" % message, match, allowable=False)

    def bar_ids(self):
        ids = set()
        for line in self.p.section_lines("The bar"):
            if line.fence or line.comment:
                continue
            found = P09_ROW.match(line.raw) or (None if TABLE_ROW_RE.match(line.raw) else P09_ITEM.match(line.raw))
            if found and found.group(1):
                ids.add(found.group(1))
        return ids

    # ---------------------------------------------------------- P36
    def p36(self):
        """ERROR, never allowable (its (d) and (e) WARN): the verification text follows the method. (b) reads outside
        fences and indented code blocks; (c) reads the template's own ledger fragments only."""
        seat, review, size = (self.f.get(k) for k in ("seat", "review", "size"))
        source, text = self.p.source, normalise(self.p.source)
        v2_words, rs5 = phrase_re(V2_WORDS, re.I), phrase_re(RS_LABELS[5])
        if review == "none":
            for regex, what in ((v2_words, "V2's words (\"%s\")" % V2_WORDS), (rs5, "RS5's label %s" % RS_LABELS[5])):
                if regex.search(source):
                    self.p36_error(self.where(regex), "(a) review=none, yet the prompt holds %s: no review seat, no review "
                                   "sentence" % what, regex.search(source).group(0))
        elif not review and (v2_words.search(source) or rs5.search(source)):
            self.skipped("P36", "(a) a review sentence or RS5 is in the prompt; whether a review seat exists needs the "
                                "framing's review")
        seated = [phrase_re(RS_LABELS[rs]) for rs in (2, 3, 4, 5, 6)] + [phrase_re(DELEGATE_TEXT, re.I)]
        free = self.p.outside_code()   # a fence or an indented code block quotes, it does not instruct
        present = [match for match in (regex.search(free) for regex in seated) if match]
        if seat == "alone" or size == "quick":
            for match in present:
                self.p36_error(self.p.line_at(match.start()).n, "(b) the run works alone, yet the prompt holds %r, which "
                               "only a run with seats carries" % match.group(0), match.group(0))
        elif present and not seat:
            self.skipped("P36", "(b) seat text is in the prompt; whether the run has seats needs the framing's seat")
        hits = self.ledger_hits()
        kept = self.ledger_kept()
        if kept is False:
            for line, match in hits:
                self.p36_error(line, "(c) no ledger is kept on this run (%s), yet an instruction says %r; the task's "
                               "own ledger (an accounting one) goes in inline code, which this check does not read"
                               % (self.framing_shown(), match), match)
        elif kept is None and hits:
            self.skipped("P36", "(c) the prompt names the run ledger; whether one is kept needs the framing's seat, size, "
                                "autonomy and run")
        if size in ("standard", "deep") and V1 not in text:
            self.add("P36", "WARN", None, "(d) a %s prompt should carry V1: %r" % (size, V1), V1, allowable=False)
        if review == "fresh" and V2 not in text:
            self.add("P36", "WARN", None, "(e) a prompt with a review seat should carry V2 beside the step that dispatches "
                                          "it: %r" % V2, V2, allowable=False)

    def p36_error(self, line, message, match=None):
        self.add("P36", "ERROR", line, "verification %s" % message, match, allowable=False)

    def ledger_hits(self):
        """[(line, phrase)]: the run ledger's own phrases in instruction text outside literal spans, read across line
        breaks inside a paragraph; overlapping phrases count once."""
        regexes = [phrase_re(p, re.I) for p in LEDGER_PHRASES]
        hits, unit = [], []
        for line in self.p.lines + [None]:
            if line is not None and self.p.is_instruction_text(line) and line.raw.strip() and not line.heading:
                unit.append(line)
                continue
            if unit:
                joined, starts, offset = "", [], 0
                for member in unit:
                    starts.append(offset)
                    joined += member.literal + "\n"
                    offset += len(member.literal) + 1
                spans = []
                for match in sorted((m for r in regexes for m in r.finditer(joined)), key=lambda m: (m.start(), -m.end())):
                    if any(match.start() < e and s < match.end() for s, e in spans):
                        continue
                    spans.append((match.start(), match.end()))
                    hits.append((unit[bisect.bisect_right(starts, match.start()) - 1].n, " ".join(match.group(0).split())))
            unit = []
        return hits

    def framing_shown(self):
        return "; ".join("%s=%s" % (k, self.f[k]) for k in ("size", "seat", "autonomy", "run") if self.f.get(k))

    # ---------------------------------------------------------- P37
    def p37(self):
        """Never allowable: the ceremony is the table's for the framing. (a) ERROR: on a run that works alone, the first
        sentence of the guide's seats-models block, in either model variant, outside code: the model text of a run
        with seats; (b) WARN: a run-rule label outside the table's set (RS8 aside: a long operation is no framing
        fact)."""
        seat, size = self.f.get("seat"), self.f.get("size")
        if seat == "alone" or size == "quick":
            guide = self.c.guide
            if guide is None:
                self.skipped("P37", "(a) the seats-models block is read from the framing's harness guide (%s)"
                             % self.c.guide_shown())
            else:
                free = self.p.outside_code().replace("\u2019", "'")
                for model in (MODEL_CHOOSE, "named"):
                    sentence = guide.guideline_sentence(model)
                    if not sentence:
                        continue
                    for match in re.finditer(_piece(sentence, {}, False, ())[0], free):
                        shown = " ".join(match.group(0).split())
                        self.add("P37", "ERROR", self.p.line_at(match.start()).n, "(a) the run works alone, yet the "
                                 "prompt holds the guide's seats-models text %r, which only a run with seats carries"
                                 % shown[:80], shown[:60], allowable=False)
        need, why = self.required_rs() if self.f.get("size") else (None, "size")
        if why or need is None:
            return
        heading, lines = self.p.sections.get("Run rules", (None, []))
        for rs, label in sorted(RS_LABELS.items()):
            if rs == 8 or rs in need:
                continue
            line = next((l for l in lines if label in l.raw and not l.comment), None)
            if line is not None:
                self.add("P37", "WARN", line.n, "(b) RS%d %s is outside the run rules the ceremony table gives this framing "
                         "(%s)" % (rs, label, ", ".join("RS%d" % n for n in sorted(need))), label, allowable=False)

    # ---------------------------------------------------------- P38
    def p38(self):
        """ERROR, never allowable: a framing the seat rule allows and whose harness, launch, effort and model are well
        formed (framing_conflicts), and a seat=implementer or lead whose prompt says it works alone. When it fires, P13
        checks only RS1 and RS13."""
        for message in self.conflicts:
            self.add("P38", "ERROR", None, "framing %s" % message, allowable=False)
        for line, message, sentence in self.text_conflicts:
            self.add("P38", "ERROR", line, "framing %s" % message, sentence, allowable=False)
        f = self.f
        if f.get("seat") == "alone" and self.missing("review", "size", "run"):
            self.skipped("P38", "seat=alone: its consistency needs the framing's %s" % " and ".join(self.missing("review", "size", "run")))
        elif f.get("seat") == "implementer" and self.missing("size", "run"):
            self.skipped("P38", "seat=implementer: its consistency needs the framing's %s" % " and ".join(self.missing("size", "run")))
        elif f.get("size") == "quick" and not f.get("seat"):
            self.skipped("P38", "size=quick means seat=alone; the framing's seat is unknown")

    # ---------------------------------------------------------- P40
    def p40(self):
        """ERROR, never allowable; needs --decisions. decisions.md § Launch holds the guide's launch block for the
        framing (launch-attended for launch=interactive, launch-headless for headless, launch-cloud for cloud, and the
        generic guide's launch-headless for other), each line filled and its slots by shape, its command lines whole,
        and no line of another launch block."""
        launch = self.f.get("launch")
        if self.decisions is None:
            self.skipped("P40", "needs --decisions (decisions.md `## Launch`)")
            return
        if launch not in ENUM_VALUES["launch"] or self.c.guide is None:
            self.skipped("P40", "needs the framing's %s" % (
                "launch" if launch not in ENUM_VALUES["launch"] else "harness guide (%s)" % self.c.guide_shown()))
            return
        expected_guide = self.c.launch_guide()
        if expected_guide is None:
            self.skipped("P40", "launch=other takes the generic guide's launch-headless, and that guide was not found")
            return
        block_id = LAUNCH_BLOCK[launch]
        if block_id not in expected_guide.blocks:
            self.skipped("P40", "the guide has no `%s` block" % block_id)
            return
        variants = self.c.frozen(block_id, launch_verbatim, expected_guide)
        unknown = set().union(*(block.unknown for block in variants))
        if unknown:
            self.skipped("P40", "the guide's `%s` block has fragments the framing does not settle (%s)"
                         % (block_id, ", ".join(sorted(unknown))))
            return
        launch_text = _md_section(self.decisions, "Launch").replace("’", "'")
        if not any(block.search(launch_text) for block in variants):
            (low, wrapped), expected = max(((block.stops_at(launch_text), block) for block in variants),
                                           key=lambda item: (item[0][1], item[0][0]))
            if wrapped:
                self.p40_error("decisions.md `## Launch` holds the guide's `%s` block with a command line split across "
                               "lines; keep each command line whole" % block_id, block_id)
            else:
                stop = expected.lines[min(low, len(expected.lines) - 1)].strip()
                self.p40_error("decisions.md `## Launch` is not the guide's `%s` block filled for this framing: it stops "
                               "matching at its line %d, %r" % (block_id, low + 1, stop[:120]), stop[:60])
        own = {normalise(line) for block in variants for line in block.lines}
        for other_id, other_guide in self.c.other_launch_blocks(block_id):
            lines = [line for other in self.c.frozen(other_id, launch_verbatim, other_guide) for line in other.lines]
            for line in lines:
                if normalise(line) in own or len(line.split()) < 2 and len(line.strip()) < 8:
                    continue
                single = FrozenBlock(other_id, line, self.f, launch_verbatim)
                if single.search(launch_text):
                    self.p40_error("decisions.md `## Launch` holds a line of the guide's `%s` block, which is not this "
                                   "framing's launch: %r" % (other_id, line.strip()[:120]), line.strip()[:60])
                    break

    def p40_error(self, message, match=None):
        self.add("P40", "ERROR", None, "launch %s" % message, match, allowable=False)

    # ---------------------------------------------------------- P41
    def p41(self):
        """ERROR, never allowable: a run with seats carries the template's fallback paragraph word for word; a run that
        works alone carries none of it."""
        seat = "alone" if self.f.get("size") == "quick" else self.f.get("seat")
        text = normalise(self.p.outside_code())
        if seat in ("implementer", "lead"):
            if normalise(FALLBACK_PARAGRAPH) not in text:
                line = self.where(phrase_re(FALLBACK_LABEL))
                self.add("P41", "ERROR", line, "seat=%s: the paragraph %s is %s; it goes word for word after the guide's "
                         "seats form" % (seat, FALLBACK_LABEL, "changed" if line else "missing"), FALLBACK_LABEL,
                         allowable=False)
        elif seat == "alone":
            line = self.where(phrase_re(FALLBACK_LABEL))
            if line is not None:
                self.add("P41", "ERROR", line, "the run works alone, yet the prompt carries %s, which only a run with seats "
                         "carries" % FALLBACK_LABEL, FALLBACK_LABEL, allowable=False)
        else:
            self.skipped("P41", "needs the framing's seat")

    # ---------------------------------------------------------- P42
    def p42(self):
        """ERROR, never allowable; needs --decisions. What decisions.md § Launch lets the run do. (a) The guide's wide
        permission setting (the word its launch-headless block puts before "only in a disposable sandbox") in a command
        line only with machine=disposable and a live decisions-log row that names it and quotes the person's
        confirmation. (b) In each allowlist the launch passes (the flag read from that block): no rule that prints the
        whole environment, or variables by a prefix; none that admits every git command; a push only as an exact rule
        whose branch a live row of the person's (Stated or Interview) allows."""
        if self.decisions is None:
            self.skipped("P42", "needs --decisions (decisions.md `## Launch`)")
            return
        guide = self.c.guide
        if guide is None:
            self.skipped("P42", "needs the framing's harness guide (%s)" % self.c.guide_shown())
            return
        launch_text = _md_section(self.decisions, "Launch").replace("’", "'")
        rows = [row for row in decision_rows(self.decisions) if row["status"].strip().lower() == "live"]
        wide = guide.wide_setting()
        commands = [line for line in launch_text.split("\n") if launch_verbatim(line)]
        if wide and any(re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(wide), line) for line in commands):
            machine = self.f.get("machine")
            if machine is None:
                self.skipped("P42", "(a) the launch uses `%s`: whether the machine is disposable needs the framing's "
                                    "machine" % wide)
            elif machine != "disposable":
                self.p42_error("(a) the launch uses `%s`, the guide's wide setting, on machine=%s: it is only for a "
                               "disposable sandbox the person confirmed" % (wide, machine), wide)
            if not any(wide in row["decision"] and QUOTED_RE.search(row["rationale"]) for row in rows):
                self.p42_error("(a) the launch uses `%s`, and no live row of the decisions log names it with the "
                               "person's confirmation quoted in its Rationale" % wide, wide)
        flag = guide.allow_flag()
        problems = set()
        for value in allowlists(launch_text, flag) if flag else ():
            for rule in split_rules(value):
                command = rule_command(rule)
                problem = None if command is None else self._p42_rule(rule, command, rows)
                if problem:
                    problems.add((problem, rule))
        for message, rule in sorted(problems):
            self.p42_error(message, rule)

    @staticmethod
    def _p42_rule(rule, command, rows):
        """Branch (b)'s message for one allowlist rule, or None."""
        words = command.split()
        if ENVIRONMENT_RULE_RE.fullmatch(command) or PREFIX_VARIABLE_RULE_RE.match(command):
            return "(b) the allowlist rule `%s` %s; read each variable by an exact rule" % (rule, (
                "admits every variable its prefix matches, a credential among them"
                if PREFIX_VARIABLE_RULE_RE.match(command) else "prints the whole environment"))
        literal = command.split("*", 1)[0].split()   # the words a `*` cannot stand in for
        if re.match(r"git(?![\w-])", command) and ("*" in command and len(literal) < 2 or
                                                   len(words) > 1 and words[1].startswith("-")):
            return ("(b) the allowlist rule `%s` admits every git command, a push to any branch and a `-c` that runs "
                    "any program among them; give each subcommand its own rule" % rule)
        if words[:2] == ["git", "push"]:
            if "*" in command:
                return "(b) the allowlist rule `%s` admits a push to any remote or branch; a push is one exact rule" % rule
            if not any(re.search(r"\bpush", row["decision"], re.I) and words[-1] in row["decision"] and
                       row["source"].strip().lower() in ("stated", "interview") for row in rows):
                return ("(b) the allowlist rule `%s` pushes, and no live row of the decisions log records the person "
                        "(Stated or Interview) allowing a push of `%s`" % (rule, words[-1]))
        return None

    def p42_error(self, message, match=None):
        self.add("P42", "ERROR", None, "launch %s" % message, match, allowable=False)

    # ---------------------------------------------------------- P43
    def p43(self):
        """ERROR, never allowable, where the framing's guide says in its §3 that a command the run executes holds no
        shell variable outside single quotes (its harness refuses a command it cannot check before it runs): no inline
        code span of `## Seats and models` that holds a space (a command: the headless-seat lines, a phase zero's
        steps) holds a `$NAME` or `${…}` the shell would expand."""
        guide = self.c.guide
        span = self.p.section_span("Seats and models")
        if span is None:
            return
        if guide is None:
            self.skipped("P43", "needs the framing's harness guide (%s)" % self.c.guide_shown())
            return
        if not guide.literal_commands():
            return
        for line in self.p.sections["Seats and models"][1]:
            if line.fence or line.indented_code or line.comment:
                continue
            for command in re.findall(r"`([^`\n]+)`", line.raw.replace("’", "'")):
                variables = shell_variables(command) if re.search(r"\s", command.strip()) else []
                if variables:
                    shown = ", ".join("`%s`" % v for v in sorted(set(variables), key=variables.index))
                    self.add("P43", "ERROR", line.n, "`## Seats and models` runs a command holding %s outside "
                             "single quotes: this harness refuses a command it cannot check before it runs, so every "
                             "path in a command the run executes is literal (the guide's §3)" % shown,
                             variables[0], allowable=False)

    # ---------------------------------------------------------- P44
    def p44(self):
        """ERROR, never allowable: a quick, unattended prompt carries the quick template's unattended line word for
        word, its only resume and turn-end rule."""
        size, autonomy = self.f.get("size"), self.f.get("autonomy")
        if size not in (None, "quick") or autonomy == "attended":
            return
        if size is None or autonomy is None:
            self.skipped("P44", "needs the framing's %s" % " and ".join(self.missing("size", "autonomy")))
            return
        if normalise(QUICK_UNATTENDED_LINE) not in normalise(self.p.outside_code()):
            line = self.where(phrase_re(QUICK_UNATTENDED_LABEL))
            self.add("P44", "ERROR", line, "a quick, unattended prompt: the line %s is %s; it goes word for word under "
                     "the interrupt policy, as the quick template writes it" % (QUICK_UNATTENDED_LABEL,
                                                                                "changed" if line else "missing"),
                     QUICK_UNATTENDED_LABEL, allowable=False)

    # ---------------------------------------------------------- the run
    def run(self):
        for rule in (self.p04, self.p05, self.p06, self.p07, self.p08, self.p09,
                     self.p10, self.p11, self.p12, self.p13, self.p14, self.p20, self.p21, self.p22, self.p23,
                     self.p24, self.p25, self.p26, self.p29, self.p30, self.p32, self.p33, self.p34, self.p35,
                     self.p36, self.p37, self.p38, self.p40, self.p41, self.p42, self.p43, self.p44):
            rule()
        self.apply_allows()
        self.findings.sort(key=lambda f: (f.line if f.line is not None else 0, f.rule, LEVEL_ORDER[f.level]))
        return self.findings

    def apply_allows(self):
        """An allowance turns a finding of its (allowable) rule into ALLOWED: one anchored to a line covers the block
        holding that line; one without `| at:` covers findings that have no line (P25; P34 (e), its only allowable
        findings)."""
        for finding in self.findings:
            if finding.level not in ("ERROR", "WARN") or not finding.allowable or \
                    (finding.rule not in ALLOWABLE and finding.rule not in ALLOWABLE_BRANCHES):
                continue
            for allow in self.allowances:
                block = allow["block"]
                if allow["rule"] != finding.rule:
                    continue
                if (finding.line is None and block is None) or \
                        (finding.line is not None and block is not None and block[0] <= finding.line <= block[1]):
                    finding.level, finding.reason = "ALLOWED", allow["reason"]
                    break

    def block_around(self, line):
        """(first, last) line numbers of the block holding `line`: its fenced block, its table row or heading, its
        list item with the item's continuation lines, or its paragraph."""
        lines = self.p.lines
        if line.fence:
            members = [l.n for l in lines if l.fence_no == line.fence_no]
            return (members[0], members[-1])
        if TABLE_ROW_RE.match(line.raw) or line.heading or not line.raw.strip():
            return (line.n, line.n)

        def edge(other):
            return not other.raw.strip() or other.heading or other.fence or TABLE_ROW_RE.match(other.raw)
        a = line.n - 1
        while not LIST_ITEM_RE.match(lines[a].raw) and a > 0 and not edge(lines[a - 1]):
            a -= 1
        b = line.n
        while b < len(lines) and not edge(lines[b]) and not LIST_ITEM_RE.match(lines[b].raw):
            b += 1
        return (lines[a].n, lines[b - 1].n)


# ================================================================= what the linter reads besides the prompt
class Context(object):
    """The skill folder's files a lint reads for one framing: the harness guide, the packs and SKILL.md."""

    def __init__(self, framing, skill_dir=None, packs=None):
        self.f = framing
        self.skill_dir = os.path.abspath(skill_dir or SKILL_DIR)
        self.guide = load_guide(self.skill_dir, framing.get("harness"))
        if packs is None or isinstance(packs, str):
            packs = load_packs(packs or os.path.join(self.skill_dir, "packs"))
        self.packs = list(packs)
        model = framing.get("model")
        matching = [pack for pack in self.packs if model and model != MODEL_CHOOSE and pack.matches_model(model)]
        self.pack_count = len(matching)
        self.pack = matching[0] if len(matching) == 1 else None
        skill = cached(os.path.join(self.skill_dir, "SKILL.md"), parse_skill_md) or {}
        self.skill_name = skill.get("name")
        self.autonomy_lists = skill.get("autonomy")
        self._frozen = {}

    def guide_shown(self):
        harness = self.f.get("harness")
        if not harness:
            return "the framing has no harness="
        return "references/harness-%s.md not found" % harness if self.guide is None else "references/harness-%s.md" % harness

    def frozen(self, block_id, verbatim_rule, guide=None):
        """[FrozenBlock] of a guide's block (the framing's guide unless another is given) expanded for the framing; []
        when the guide or the block is missing."""
        guide = guide if guide is not None else self.guide
        if guide is None or block_id not in guide.blocks:
            return []
        key = (block_id, verbatim_rule, id(guide))
        if key not in self._frozen:
            self._frozen[key] = [FrozenBlock(block_id, guide.blocks[block_id], self.f, verbatim_rule)]
        return self._frozen[key]

    def seats_blocks(self):
        """The guide's blocks a prompt may carry, each expanded for the framing (those the framing settles)."""
        out = []
        for block_id in SEATS_BLOCKS:
            for block in self.frozen(block_id, prompt_verbatim):
                if not block.unknown and block.regex is not None:
                    out.append(block)
        return out

    @staticmethod
    def alone_sentences():
        """The sentences that say the executor works alone: the quick template's."""
        return [QUICK_ALONE]

    def launch_guide(self):
        if self.f.get("launch") == "other":
            return load_guide(self.skill_dir, GENERIC)
        return self.guide

    def other_launch_blocks(self, block_id):
        """[(block id, guide)] of every launch block that is not the framing's."""
        expected = self.launch_guide()
        out = []
        for guide in (self.guide, load_guide(self.skill_dir, GENERIC) if self.f.get("launch") == "other" else None):
            if guide is None:
                continue
            for other in LAUNCH_BLOCKS:
                if other in guide.blocks and not (guide is expected and other == block_id) and \
                        (other, guide) not in out:
                    out.append((other, guide))
        return out


def parse_skill_md(text):
    """{"name": the frontmatter name or None, "autonomy": {"unattended": [...], "attended": [...]} or None}."""
    name = None
    if text.startswith("---\n"):
        for line in text.split("\n")[1:]:
            if line.rstrip() == "---":
                break
            found = re.match(r"^name:\s*[\"']?([^\"'\s]+)[\"']?\s*$", line)
            if found:
                name = found.group(1)
    flat = normalise(text)
    lists = {}
    for key, start, end in AUTONOMY_LISTS:
        at = flat.find(start)
        stop = flat.find(end, at) if at >= 0 else -1
        lists[key] = re.findall(r'"([^"]+)"', flat[at:stop]) if stop > at else []
    return {"name": name, "autonomy": lists if all(lists.values()) else None}


# ================================================================= decisions and framing
def _md_lines(text):
    """(line, inside a fence) for each line of a Markdown text, so a `## ` line inside a fence is not a heading
    (decisions.md § The person's words quotes the person's messages verbatim)."""
    return [(line, fenced) for line, fenced, _ in fence_lines(text)]


def _is_heading(line, name):
    return bool(re.match(HEADING_PREFIX + re.escape(name) + r"\s*$", line.rstrip().replace("\u2019", "'"), re.I))


def _md_section(text, name):
    """The body of `## <name>` in a Markdown text, up to the next `## ` heading outside a fence."""
    out, inside = [], False
    for line, fenced in _md_lines(text):
        if not fenced and re.match(r"^##\s", line):
            if inside:
                break
            inside = _is_heading(line, name)
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def _md_has_section(text, name):
    return any(not fenced and _is_heading(line, name) for line, fenced in _md_lines(text))


def md_table(text, header):
    """(header found, [row cells]) of the first table in `text` whose header row's cells equal `header`, ignoring
    case; rows run to the first line that is not a table row; the separator row is skipped."""
    rows, inside = [], False
    for line, fenced in _md_lines(text):
        if fenced or not TABLE_ROW_RE.match(line):
            if inside:
                break
            continue
        cells = table_cells(line)
        if not inside:
            inside = [cell.lower() for cell in cells] == header
            continue
        if not TABLE_SEPARATOR_RE.match(line):
            rows.append(cells)
    return inside, rows


def decision_rows(decisions):
    """The decisions log's rows as dicts keyed by LOG_HEADER."""
    return [dict(zip(LOG_HEADER, cells + [""] * len(LOG_HEADER)))
            for cells in md_table(_md_section(decisions, "Decisions log"), LOG_HEADER)[1]]


def allowlists(launch_text, flag):
    """Each value `flag` takes in a launch text, as the shell passes it on (the template's slot and a `<…>`
    placeholder left out)."""
    regex = re.compile(r"%s(?:=|\s+)('(?:[^']|'\\'')*'|\"(?:[^\"\\]|\\.)*\"|[^\s'\"]+)" % re.escape(flag))
    out = []
    for raw in launch_text.split("\n"):
        for m in regex.finditer(raw):
            try:
                passed = shlex.split(m.group(1))
            except ValueError:
                passed = []
            value = passed[0] if len(passed) == 1 else m.group(1)
            if "{ALLOWED_TOOLS}" not in value and not re.fullmatch(r"<[^<>]*>", value):
                out.append(value)
    return out


def split_rules(value):
    """An allowlist's rules as the harness's own parser splits them: `(` opens and any `)` closes, with no count of
    nesting, and a comma or a space outside splits (the guide's §1 says so)."""
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


def rule_command(rule):
    """The command text a `Tool(<command>)` rule matches, or None for a rule with no parenthesised part."""
    found = re.match(r"^[A-Za-z][\w-]*\((.+)\)$", rule, re.S)
    return found.group(1).strip() if found and found.group(1).strip() else None


def shell_variables(command):
    """The `$NAME` and `${…}` a POSIX shell would expand in `command`: outside single quotes and not escaped by a
    backslash (`$1`, `$?` and `$(…)` are not variables by name). A `<…>` placeholder the run fills in is read as one
    word, so the apostrophe of `<the seat's allowlist>` opens no quote."""
    command = RUN_PLACEHOLDER_RE.sub("x", command)
    found, quote, i = [], None, 0
    while i < len(command):
        char = command[i]
        if quote == "'":
            quote = None if char == "'" else quote
        elif char == "\\":
            i += 1
        elif char == "'" and quote is None:
            quote = "'"
        elif char == '"':
            quote = None if quote == '"' else '"'
        elif char == "$":
            match = SHELL_VARIABLE_RE.match(command, i)
            if match:
                found.append(match.group(0))
                i = match.end()
                continue
        i += 1
    return found


def record_lines(text):
    """The lines of a decisions.md section a record is read from: HTML comments (the template's guidance) and
    fenced lines left out."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return [line for line, fenced in _md_lines(text) if not fenced]


def unquote(cell):
    """A cell's text with one pair of enclosing double quotes removed and its whitespace normalised."""
    text = normalise(cell)
    for left, right in (('"', '"'), ("\u201c", "\u201d")):
        if len(text) > 1 and text.startswith(left) and text.endswith(right):
            return text[1:-1].strip()
    return text


ABBREVIATION_RE = re.compile(r"(?:[A-Za-z]\.)+[A-Za-z]?|[A-Za-z]\.(?:[A-Za-z]{1,3}\.)+|(?:[A-Z]{1,3}\.){2,}")


def identifiers(words):
    """The paths and identifiers in a person's words: each backticked span, and each other token holding `/`, `_`, a
    `.` between two word characters, or a leading `.` before a letter (a dotfile: `.env`), its punctuation stripped.
    A dotted abbreviation is none: single letters ("e.g.", "i.e."), a letter and short groups each closed by its dot
    ("p.ej."), or capitals ("EE.UU.")."""
    out = [span.strip() for span in re.findall(r"`([^`]+)`", words) if span.strip()]
    for token in re.sub(r"`[^`]*`", " ", words.replace("\u2019", "'")).split():
        token = token.strip("\"'\u201c\u201d\u2018\u00ab\u00bb()[]{}<>,;:!?\u00a1\u00bf")
        if ABBREVIATION_RE.fullmatch(token):
            continue
        token = token.rstrip(".")
        if "/" in token or "_" in token or re.search(r"\w\.\w", token) or re.match(r"\.[A-Za-z_]", token):
            out.append(token)
    return out


def carries_identifier(text, token):
    """Whether `text` holds `token` whole: not inside a longer path or name; a trailing `/` on either side is the same
    folder."""
    token = token.replace("\u2019", "'").rstrip("/") or token
    return re.search(r"(?<![\w/.-])%s/?(?![\w/-]|\.\w)" % re.escape(token), text.replace("\u2019", "'")) is not None


def section_target(cell):
    """A § The person's words Section cell: a prompt heading's key, "outside" for `Launch` or `not in the prompt:
    <reason>` (carried by decisions.md § Launch and the delivery, or with its reason), or None."""
    value = cell.replace("`", "").strip()
    if heading_key(value) == "launch":
        return "outside"
    outside = re.match(r"not in the prompt\s*:\s*(.*)$", value, re.I)
    if outside:
        return "outside" if outside.group(1).strip() else None
    return heading_key(value) or None


def person_rows(decisions):
    """[(section key, "In the prompt as" text)] of each value and prohibition the person gave whose Section is a
    prompt heading: their own words, exempt from the content rules inside that section."""
    out = []
    for cells in md_table(_md_section(decisions, WORDS_SECTION), WORDS_HEADER)[1]:
        row = dict(zip(WORDS_HEADER, cells + [""] * len(WORDS_HEADER)))
        target = section_target(row["section"])
        text = unquote(row["in the prompt as"])
        if row["kind"].strip("`* ").lower() in ("value", "prohibition") and target not in (None, "outside") and text:
            out.append((target, text))
    return out


def holds_phrase(text, phrase):
    """Whether `text` holds `phrase` as whole words, ignoring case (both already normalised)."""
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(phrase), text, re.I) is not None


def seat_conflicts(f):
    """The seat rule: seat=alone requires review=none, a size other than deep and run=one-session; size=quick requires
    seat=alone; seat=implementer requires a size other than deep and run=one-session (a deep or long run gets a lead).
    Only known values conflict."""
    out = []
    if f.get("seat") == "alone":
        for key, bad in (("review", ("fresh",)), ("size", ("deep",)), ("run", ("one-day", "multi-session"))):
            if f.get(key) in bad:
                out.append("seat=alone with %s=%s: a run that works alone has no review seat, is not deep and runs in one "
                           "session; take the implementer or lead row" % (key, f[key]))
    if f.get("seat") == "implementer":
        for key, bad in (("size", ("deep",)), ("run", ("one-day", "multi-session"))):
            if f.get(key) in bad:
                out.append("seat=implementer with %s=%s: a deep or long run gets a lead that does not implement" % (key, f[key]))
    if f.get("size") == "quick" and f.get("seat") in ("implementer", "lead"):
        out.append("size=quick with seat=%s: the quick lane's executor works alone (seat=alone)" % f["seat"])
    return out


def framing_conflicts(f, skill_dir=None):
    """P38: the seat rule (seat_conflicts), then the framing's other fields: harness= names a guide that exists,
    launch= agrees with autonomy= (attended: interactive or cloud; unattended: headless, cloud or other), effort= is
    `default` or one word, model= is one word (`choose` where the person named none) or the placeholder. Only values
    the framing gives are judged."""
    out = seat_conflicts(f)
    harness = f.get("harness")
    if harness is not None and load_guide(os.path.abspath(skill_dir or SKILL_DIR), harness) is None:
        out.append("harness=%s names no guide (references/harness-%s.md): the guide is what the launch and the seats are "
                   "written from" % (harness, harness))
    autonomy, launch = f.get("autonomy"), f.get("launch")
    if autonomy in LAUNCH_BY_AUTONOMY and launch in ENUM_VALUES["launch"] and launch not in LAUNCH_BY_AUTONOMY[autonomy]:
        out.append("launch=%s with autonomy=%s: an %s run is launched %s" % (
            launch, autonomy, autonomy, " or ".join(LAUNCH_BY_AUTONOMY[autonomy])))
    effort = f.get("effort")
    if effort is not None and not (effort == "default" or re.fullmatch(r"[A-Za-z][\w-]*", effort)):
        out.append("effort=%s is neither `default` nor one word: the level the person named, or default" % effort)
    model = f.get("model")
    if model is not None and not (model == MODEL_PLACEHOLDER or ONE_WORD_RE.fullmatch(model)):
        out.append("model=%s is neither one word nor %s: the id of the model the person named, as the harness names "
                   "it and never a guess, or %s where they named none" % (model, MODEL_PLACEHOLDER, MODEL_CHOOSE))
    return out


def run_rules_for(f):
    """The RS numbers the ceremony table requires of a complete framing."""
    if f["size"] == "quick":
        return set(ROW_RS["quick"])
    need = set(ROW_RS[f["seat"]])
    if f["review"] == "fresh":
        need |= MODIFIER_RS["review=fresh"]
    if f["size"] == "deep" or f["autonomy"] == "unattended" or f["run"] == "multi-session":
        need |= MODIFIER_RS[HEAVY]
    if f["run"] == "one-day":
        need |= MODIFIER_RS["run=one-day"]
    if f["machine"] == "disposable":
        need |= MODIFIER_RS["machine=disposable"]
    return need


def parse_framing(text):
    """Read the `Framing:` line: key=value pairs separated by `;`; folder takes the rest of the line. Values outside
    an enumerated key's set are dropped (the rules that need them are SKIPPED) and returned as invalid; harness,
    model and effort are kept as written (P38 judges them)."""
    framing, invalid = {}, {}
    for line in text.split("\n"):
        if not line.startswith("Framing:"):
            continue
        body = line[len("Framing:"):].strip()
        folder = re.search(r"(?:^|;)\s*folder=(.*)$", body)
        if folder:
            framing["folder"] = folder.group(1).strip()
            body = body[:folder.start()]
        for part in body.split(";"):
            if "=" not in part:
                continue
            key, value = (x.strip() for x in part.split("=", 1))
            if key in ENUM_VALUES:
                if value in ENUM_VALUES[key]:
                    framing[key] = value
                else:
                    invalid[key] = value
            elif key in FREE_KEYS and value:
                framing[key] = value
        break
    return framing, invalid


class Result(object):
    """A lint's findings, sorted, with the prompt's word counts."""

    def __init__(self, findings, words, published_words):
        self.findings, self.words, self.published_words = findings, words, published_words


def lint_document(text, framing, decisions_text=None, skill_dir=None, packs=None):
    """Lint a prompt's text. `skill_dir` is the skill folder whose guides, packs and SKILL.md are read (default: the
    one this file sits in). `packs` is the guidance packs: None reads `<skill_dir>/packs`, a folder path reads that
    folder, a list of Pack is used as given ([] knows none)."""
    context = Context(framing, skill_dir, packs)
    blocks = [block for pack in context.packs for block in pack.blocks]
    prompt = Prompt(text, blocks, person_rows(decisions_text) if decisions_text is not None else (),
                    context.seats_blocks(), context.pack.name if context.pack is not None else None)
    findings = Linter(prompt, framing, decisions_text, context).run()
    words = sum(len(line.raw.split()) for line in prompt.lines)
    return Result(findings, words, prompt.published_words)


def lint_text(text, framing, decisions_text=None, skill_dir=None, packs=None):
    """Lint a prompt's text; returns the sorted list of Findings."""
    return lint_document(text, framing, decisions_text, skill_dir, packs).findings


def _shown(path):
    home = os.path.expanduser("~")
    path = os.path.abspath(path)
    if len(home) > 1 and (path == home or path.startswith(home + os.sep)):
        return "$HOME" + path[len(home):]
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint a master prompt and its decisions.md.")
    parser.add_argument("prompt")
    parser.add_argument("--decisions")
    for key in FLAG_KEYS:
        if key in ENUM_VALUES:
            parser.add_argument("--" + key, choices=ENUM_VALUES[key])
        else:
            parser.add_argument("--" + key)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        with open(args.prompt, encoding="utf-8") as handle:
            text = handle.read()
        decisions = None
        if args.decisions:
            with open(args.decisions, encoding="utf-8") as handle:
                decisions = handle.read()
    except (OSError, UnicodeDecodeError) as error:
        sys.stderr.write("lint_prompt: cannot read input: %s\n" % error.__class__.__name__)
        return 2
    framing, invalid = parse_framing(decisions) if decisions is not None else ({}, {})
    for key in FLAG_KEYS:
        if getattr(args, key):
            framing[key] = getattr(args, key)
            invalid.pop(key, None)
    result = lint_document(text, framing, decisions)
    findings = result.findings
    for key, value in sorted(invalid.items()):
        sys.stderr.write("lint_prompt: framing %s=%r is not one of %s; the rules that need it are skipped\n"
                         % (key, value, "|".join(ENUM_VALUES[key])))
    errors = sum(f.level == "ERROR" for f in findings)
    warnings = sum(f.level == "WARN" for f in findings)
    allowed = sum(f.level == "ALLOWED" for f in findings)
    if args.json:
        print(json.dumps({"file": _shown(args.prompt), "framing": framing, "errors": errors, "warnings": warnings,
                          "allowed": allowed, "words": result.words, "published_words": result.published_words,
                          "findings": [f.as_dict() for f in findings]}, indent=1, ensure_ascii=False))
    else:
        for finding in findings:
            print(finding.as_text())
        print("errors: %d, warnings: %d, allowed: %d" % (errors, warnings, allowed))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
