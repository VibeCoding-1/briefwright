"""The README claims only what the repository shows.

The title, the promise, the line on who it is for, one short line that leads to the install lines, and the install lines
come before any other section, with a release badge on the repository beside the others; above "How it works" the prose
is plain (no word of the trade left unexplained, each technical word explained where it first appears, short sentences
on average); every relative link and anchor in the README and docs/install.md resolves; the README makes none of the
claims the evidence does not carry, and
keeps each clause that holds a claim to what the skill does; the FAQ's second entry places it among its peers without
ranking them, and its third says what the skill does with a plan request, its qualifiers kept and nothing ranked; the
person's reply and the quoted passages fold into one <details> that GitHub renders; no file reads as if the landing page
were built; docs/install.md marks exactly the five routes run against the repository "tested on" a version and a date,
Gemini CLI its own install-and-remove status, and every other route "documented", and the README calls no other route
tested; and the demo
is a self-contained SVG of three beats in large type that land in turn and are still by VISIBLE_BY seconds, each word
carried by the example the caption links: the request a quote whose every fragment stands in its README's translation,
in order, with an ellipsis wherever words are dropped; then a thumbnail of its prompt, the rows `##` headings of that
file in order, each skipped stretch a gap counting the headings it skips, every row picked out in the accent in turn.
Arrows carry the eye along the story: a dim connector from each beat to the next and a mint one from the last beat
that stops short of the thumbnail, each a thin line ending in an open chevron that draws itself on as its beat or the
thumbnail lands, and is whole in the last frame. It repeats without end, one cycle that every animated element runs
on the same length: once still, the complete frame holds for HOLD seconds or more, then everything fades out together
over RESET seconds or more, never cut, and the build starts again from the empty frame. At most about 40 words, in
the social image's palette with no gradient, shadow or emoji, no brand, result or harness named; captioned, and
described in its alt text, as a real prompt the skill wrote with a model answering its questions, its alt text listing
every line it shows. Each check is a function that returns what it found, and each has a test that plants the mutation
it exists to catch.
"""
import functools
import os
import re
import unittest
import xml.etree.ElementTree as ET

import support
from support import ROOT, read

README = os.path.join(ROOT, "README.md")
DOCS = os.path.join(ROOT, "docs")
INSTALL = os.path.join(DOCS, "install.md")
DEMO = os.path.join(DOCS, "media", "demo.svg")
LINKED = (README, INSTALL)
# The skill-name placeholder, built at run time: the export refuses any placeholder left in a file it does not fill.
NAME_TOKEN = "{{" + "SKILL_NAME" + "}}"
# The staged layout (the source of the public tree) keeps the skill outside the tree, and its root LICENSE and NOTICE are
# the skill's own, copied at export; the published layout holds all three where the links point.
STAGED = os.path.isdir(os.path.join(ROOT, "packaging"))

FIRST_SCREEN = 30                     # the install lines sit within the README's first 30 lines
# The top: the name and its category in plain words; the promise, the one line every public text starts from, word for
# word with the name in its place; then who it is for, by the agents a reader knows, and what the plan is.
TITLE = "a plan writer for AI coding agents"
PROMISE = "Describe the job in one sentence. {name} asks what's missing, then writes the full plan your AI agent can " \
          "follow on its own."
AUDIENCE = ("AI coding agent", "Claude Code", "Codex", "master prompt")
# Then a next step before the badges and the demo: one short line, no longer than the top half's average sentence may
# be, that sends the reader to the install lines.
NEXT_STEP = "](#install)"
NEXT_STEP_WORDS = 16
# The release badge sits in the badge row, its image and its link on the repository the CI badge names.
REPO_TOKEN = "{{" + "REPO" + "}}"
RELEASE_BADGE = "[![Release](https://img.shields.io/github/v/release/{repo})](https://github.com/{repo}/releases)"
INSTALL_COMMANDS = ("claude plugin marketplace add ", "codex plugin marketplace add ", "npx skills add ")
HARNESSES = ("Claude Code", "Codex", "Gemini CLI", "Copilot CLI", "GitHub CLI", "Cursor", "OpenCode", "claude.ai",
             "Antigravity")
# The routes run against the repository on 2026-10-13, each "tested on <version>, <date>" (claude.ai shows no
# version, so a date only); Gemini CLI, installed and removed from a clone, has a status of its own; every other route
# is "documented".
TESTED = ("Claude Code", "Codex", "OpenCode", "claude.ai", "Antigravity")
UNVERSIONED = ("claude.ai",)
GEMINI_STATUS = "installs and removes cleanly from a clone (0.63.0, 2026-10-13)"
DOCUMENTED = "documented"
# A route not in TESTED called tested: from "tested on", "in" or "with" to the end of its sentence or clause, a dot
# inside a word such as claude.ai not ending it, and "also installs" starting a new claim.
UNTESTED_CLAIM = (r"\btested (?:on|in|with)\b(?:(?!\balso installs\b)(?:[^.;\n]|\.(?=\S)))*?"
                  r"\b(?:gemini|copilot|cursor|github cli)\b")
# Claims the evidence does not carry. Nobody counted the run's reads, so no number of files read is claimed.
CLAIMS = (r"better than", r"no task lost", r"wins every", r"\bwins\b", UNTESTED_CLAIM, r"\bfour files\b")
# Each clause a page keeps under its heading: without one, a sentence claims more than the skill does (a spike gets a
# stop condition and no bar; a harness that cannot start subagents gets a review that was not cold), or the page drops
# a fact it owes the reader.
KEPT = (
    ("README.md", "## Why ", "into checks your agent runs, wherever checks fit"),
    ("README.md", "## Why ", "where your agent can start them, fresh subagents"),
    ("README.md", "## How it works", "what could not be established is marked open, never guessed"),
    ("README.md", "## How it works", "Where the harness cannot start a subagent, the skill does their work itself"),
    ("README.md", "## FAQ", "names no model itself"),
    ("README.md", "## FAQ", "If you name a model, the run uses that one"),
    ("install.md", "## With the `skills` CLI", "[the `skills` CLI](https://github.com/vercel-labs/skills)"),
)
# Plain words above "How it works", where a newcomer decides: the page's own prose, without its code, tables, quotes,
# images or link targets. Words of this project's trade stop a newcomer, so each may stand only in a sentence that
# explains it on the spot: the word, then " — ", " (" or ": " and what it is. A comma is no such mark: "the harness,
# the model and …" is a list.
PLAIN_END = "## How it works"
JARGON = ("harness", "executor", "bar", "linter", "lint", "seat", "headless", "plateau", "placeholder", "frontmatter",
          "rubric", "greenfield")
EXPLAINS = r"\b%s(?:s|es)?\b(?: — | \(|: )(?:a|an|the|one|that|which|what|where|how)\b"
# Claude Code and Codex count as explained only where the sentence says what they are, not wherever "AI agent" stands
# in it: listed as AI coding agents ("an AI coding agent such as Claude Code or Codex") or called them ("Claude Code
# and Codex are AI coding agents", "Codex — an AI coding agent"). Any other names beside them start with a capital and
# are joined by commas, "or" or "and".
AN_AGENT = r"AI (?:coding )?agents?"
NAMES = r"(?-i:[A-Z][\w.-]*(?: [A-Z][\w.-]*)*)"
JOIN = r"(?:,? or |,? and |, )"
IS_AN_AGENT = (r"\b%(agent)s,? (?:such as|like|including) (?:%(names)s%(join)s)*%(name)s\b"
               r"|\b%(name)s(?:%(join)s%(names)s)*(?: — | \(|: | (?:is|are) )(?:an? )?%(agent)s\b")
# The technical words this audience needs, kept and made plain: the first sentence that uses each says what it is.
TECHNICAL = (
    ("Claude Code", IS_AN_AGENT % dict(agent=AN_AGENT, names=NAMES, join=JOIN, name="Claude Code")),
    ("Codex", IS_AN_AGENT % dict(agent=AN_AGENT, names=NAMES, join=JOIN, name="Codex")),
    ("master prompt", r"\bmaster prompts?\W{1,3}(?:one|a|the) (?:single )?(?:file|plan)\b"),
    # Agent Skills: the sentence says what it is, a standard that agents read ("the open Agent Skills format, a shared
    # standard many AI agents read"); the bare name of the format explains nothing.
    ("Agent Skills", r"\bAgent Skills(?: format| standard)?\W{1,3}(?:a|an|the) (?:\w+ ){0,2}standard\b"
                     r"[^.;]*\bagents\b"),
    ("checks", r"\bchecks (?:that )?(?:your|the) agent (?:runs|passes)\b"),
    ("stop rules", r"\bstop rules?\b[^.;]{0,12}\b(?:end|ends|say when|says when)\b"),
    ("subagents", r"\bsubagents?\W{1,3}(?:helper agents?|helpers?)\b"),
)
# Plain-English guides put a readable average at 15 to 20 words a sentence (Martin Cutts, Oxford Guide to Plain
# English, guideline 1). The top half keeps to 16: inside that band, and low enough that a rewrite stringing its
# short sentences back into long ones fails.
MOST_AVERAGE = 16.0
# The FAQ's second entry places the skill among the tools a visitor already knows, neutrally: no ranking, and only
# what is true of trying them together.
PEERS = ("spec-kit", "BMAD", "OpenSpec", "Task Master", "superpowers")
RANKING = re.compile(r"\b(?:better|unlike|lacks?|lacking|worse|superior|than)\b", re.I)
UNTRIED = "It has not been tried alongside any of them."
# The third entry answers the question first-time readers asked, by what the skill does with a plan request, never by
# what an agent fails at: each step, with the qualifiers that keep it true where checks or subagents are not available.
PLAN_FIRST = "Why not just ask my agent to make a plan first?"
PLAN_FIRST_SAYS = ("reads your files and asks until nothing that changes the work is assumed",
                   "picks a method that fits the task", "what \"done\" means as checks your agent runs",
                   "wherever checks fit", "when to stop", "a script checks it", "where your agent can start them",
                   "fresh subagents read it cold")
# A wording that reads as if a run's work were judged, when the example is a prompt and no page was built. Split so
# that this file does not hold it.
RETIRED = ("built " + "overnight",)
# The demo: three beats in large type, then a thumbnail of the example's prompt.
SVG_MAX_BYTES = 100 * 1024
SVG_WIDTH = (900, 1000)               # about 960 wide, in the SVG's own pixels
SVG_HEIGHT = (480, 600)               # as tall as the layout needs
MIN_FONT_PX = 20                      # no text smaller, at the SVG's own size
BEAT_PX = 44                          # the beats, so they read on a phone 400 px wide
MOST_WORDS = 40                       # "about 40" words on screen in all, the thumbnail's rows and file name counted
BEAT_WORDS = 25                       # "about 25" of them in the three beats and the quote
VISIBLE_BY = 7.0                      # seconds into each cycle: everything shown and still
LONGEST = 9.0                         # seconds into each cycle: no part of the build runs later
HOLD = 4.0                            # seconds, the least the complete frame holds still before the reset
RESET = 0.3                           # seconds, the least the reset's fade-out takes: anything shorter reads as a cut
DURATION = (0.6, 0.8)                 # seconds, of the one fade-and-rise, with one easing
RISE = 10                             # px, the most any element rises
BEATS = ("One message in.", "It asks what’s missing.", "A plan your agent can run alone.")
# The example README's words each beat stands on: its whole first message; the questions asked; a session alone.
BEAT_FACTS = ("the person's whole first message", "asked three rounds of numbered questions",
              "a cloud session working alone")
FILE = "master-prompt.md"
# What the alt text and the caption each say: the prompt is a real one, and its answers came from a model, not a person.
CAPTION = ("a real prompt the skill wrote", "a model answering its questions")
PICKED = ("Mission", "Method", "The bar", "Stop rules and interrupt policy")   # in the accent, in this order
PALETTE = {"#0b1018", "#eef2f8", "#8d99ab", "#5d6a7d", "#6ee7b7", "#93c5fd", "#111925", "#1f2a3a"}
ACCENT, MUTED, INK = "#6ee7b7", "#8d99ab", "#eef2f8"
RESULT_WORDS = re.compile(r"\b(built|shipped|launched|finished|done)\b", re.I)
DEMO_HARNESSES = HARNESSES + ("Claude",)
# Its arrows: a dim connector from each beat to the next, then a mint arrow from the last beat into the thumbnail.
ARROWS = 3
DIM = "#5d6a7d"
STROKE = (1.5, 2.0)                   # px, every arrow's stroke
HEAD = 10                             # px, the most a chevron's arm reaches back or out from its tip
DRAW = (0.4, 0.6)                     # seconds, an arrow drawing itself on, with the one easing
WIDEST = 0.58                         # ems per character: no font tried ends a line of a beat further right
ROW_INK = (0.75, 0.25)                # ems a row's ink reaches above its baseline (cap height) and below (descent)
TIP_GAP = 32                          # px the last arrow's tip stops short of the card: air at any width, aimed at it
# Its frame: every line left of the thumbnail on the margin, gap marks that read on a phone, the card's measures.
MARGIN = 56                           # px, where every line left of the thumbnail starts
DOT = (2.5, 7)                        # px, a gap mark's three dots: their least radius, their least spacing
CARD_WIDTH, FILE_PX = 280, 22         # px, the card's width with its border; the file name's size
LINK = re.compile(r"\]\(([^)\s]+)\)|\b(?:src|href)=\"([^\"]+)\"")
FENCE = re.compile(r"^```.*?^```[ \t]*$", re.S | re.M)


def heading_lines(lines):
    """(index, line) of each Markdown heading, fenced code skipped."""
    fenced = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,6} ", line):
            yield i, line


def section(text, heading):
    """The text under a whole-line heading, up to the next heading of its level or higher (fenced code is no
    heading); None when absent."""
    lines = text.split("\n")
    marks = list(heading_lines(lines))
    start = next((i for i, line in marks if line == heading), None)
    if start is None:
        return None
    level = len(heading.split(" ", 1)[0])
    end = next((i for i, line in marks if i > start and len(line.split(" ", 1)[0]) <= level), len(lines))
    return "\n".join(lines[start + 1:end])


def table(text):
    """The rows of the one Markdown table in `text`, header and rule left out, each a list of stripped cells."""
    rows = [line for line in text.split("\n") if line.startswith("|")]
    return [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows[2:]]


def under(text, prefix):
    """The text under the first heading that starts with `prefix` (as `section`); None when absent."""
    heading = next((line for _, line in heading_lines(text.split("\n")) if line.startswith(prefix)), None)
    return None if heading is None else section(text, heading)


# The first screen

def first_screen_problems(text):
    """What keeps the promise and the install lines from coming first."""
    lines, problems = text.split("\n"), []
    if not re.fullmatch(r"# \S+ — %s" % re.escape(TITLE), lines[0]):
        problems.append("line 1 is not the title")
    paragraphs = [p.strip() for p in "\n".join(lines[1:]).split("\n\n") if p.strip()]
    promise = r"\*\*%s\*\*" % r"\S+".join(re.escape(part) for part in PROMISE.split("{name}"))
    if not paragraphs or not re.fullmatch(promise, paragraphs[0]):
        problems.append("the promise is not the first paragraph")
    elif len(paragraphs) < 2 or paragraphs[1].startswith(("[", "!", "#", "<")) \
            or not all(word in paragraphs[1] for word in AUDIENCE):
        problems.append("the line under the promise does not say who it is for and what the plan is")
    elif len(paragraphs) < 3 or paragraphs[2].startswith(("[", "!", "#", "<")) or "\n" in paragraphs[2] \
            or NEXT_STEP not in paragraphs[2] or len(paragraphs[2].split()) > NEXT_STEP_WORDS:
        problems.append("the line under who it is for is not one short line that leads to the install lines")
    headings = [i for i, _ in heading_lines(lines)]
    if len(headings) < 2 or lines[headings[1]] != "## Install":
        problems.append("the first section is not Install")
        return problems
    install = section(text, "## Install") or ""
    for command in INSTALL_COMMANDS:
        at = next((i for i, line in enumerate(lines) if line.startswith(command)), None)
        if at is None or command not in install:
            problems.append("no install line %r under Install" % command.strip())
        elif at + 1 > FIRST_SCREEN:
            problems.append("the install line %r is after line %d" % (command.strip(), FIRST_SCREEN))
    return problems


# Links and anchors

def slug(heading):
    """GitHub's anchor for a heading's text: link text kept, lowercased, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(text):
    """The anchors of a Markdown text's headings; a repeated one gets -1, -2 and so on, as on GitHub."""
    found, seen = set(), {}
    for _, line in heading_lines(text.split("\n")):
        base = slug(line.split(" ", 1)[1])
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else "%s-%d" % (base, count))
    return found


def resolve(source, target):
    """The path a relative link in `source` names, in either layout."""
    path = os.path.normpath(os.path.join(os.path.dirname(source), target))
    if os.path.exists(path) or not STAGED:
        return path
    relative = os.path.relpath(path, ROOT).replace(os.sep, "/")
    prefix = "skills/%s/" % NAME_TOKEN
    if relative.startswith(prefix):
        return os.path.join(support.SKILL, relative[len(prefix):])
    if relative in ("LICENSE", "NOTICE"):
        return os.path.join(support.SKILL, relative)
    return path


def link_problems(source, text):
    """Each relative link of `text` (as if at `source`) whose file or anchor does not exist; fenced code skipped."""
    problems = []
    for match in LINK.finditer(FENCE.sub("", text)):
        target = match.group(1) or match.group(2)
        if re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue
        name, _, anchor = target.partition("#")
        path = resolve(source, name) if name else source
        if not os.path.exists(path):
            problems.append("%s: %s (no such file)" % (os.path.basename(source), target))
        elif anchor and path.endswith(".md"):
            if anchor not in anchors(text if path == source else read(path)):
                problems.append("%s: %s (no such heading)" % (os.path.basename(source), target))
    return problems


# Claims and the clauses that hold them

def claim_problems(text):
    return [claim for claim in CLAIMS if re.search(claim, text, re.I)]


def kept_problems(texts):
    """Each clause of KEPT missing under its heading; `texts` maps a page's file name to its text."""
    return ["%s, %s: %r" % (name, heading.strip(), clause) for name, heading, clause in KEPT
            if clause not in (under(texts[name], heading) or "")]


# Install statuses

def status_problems(text):
    """Each route of docs/install.md not marked as it should be: exactly the routes of TESTED read "tested on <version>,
    <date>", claude.ai a date only, with at most a note in brackets after it; Gemini CLI reads GEMINI_STATUS; every
    other route reads DOCUMENTED."""
    rows = table(section(text, "## Every route, with its status") or "")
    problems = []
    if tuple(row[0] for row in rows) != HARNESSES:
        problems.append("the routes are %r, expected one row per harness %r" % ([row[0] for row in rows], HARNESSES))
    for harness, _, status in (row[:3] for row in rows):
        if harness in TESTED:
            version = "" if harness in UNVERSIONED else r"\d[\w.-]*, "
            ok = re.match(r"tested on %s\d{4}-\d{2}-\d{2}( \([^()]+\))?$" % version, status)
        elif harness == "Gemini CLI":
            ok = status == GEMINI_STATUS
        else:
            ok = status == DOCUMENTED
        if not ok:
            problems.append("%s: %s" % (harness, status))
    return problems


def readme_commands_problems(readme, install):
    """Each command of the README's install block that docs/install.md does not hold."""
    block = re.search(r"```sh\n(.*?)```", section(readme, "## Install") or "", re.S)
    commands = [line for line in (block.group(1) if block else "").split("\n") if line and not line.startswith("#")]
    return [command for command in commands if command not in install] or ([] if commands else ["no install block"])


def release_badge_problems(text):
    """What keeps the release badge from standing in the badge row on the repository the CI badge names (the
    placeholder, before the export fills it)."""
    row = next((line for line in text.split("\n") if "/actions/workflows/ci.yml/badge.svg" in line), "")
    ci = re.search(r"\(https://github\.com/([^\s()]+?)/actions/workflows/ci\.yml/badge\.svg\)", row)
    repo = REPO_TOKEN if STAGED else (ci.group(1) if ci else "<no CI badge>")
    if ci is None or ci.group(1) != repo:
        return ["the CI badge does not name %s" % repo]
    if RELEASE_BADGE.format(repo=repo) not in row:
        return ["no release badge on %s beside the CI badge" % repo]
    return []


# Plain words above "How it works"

def plain_text(fragment):
    """A line's words as a reader sees them: images and their links dropped, a link's text kept, code and HTML
    marks removed, emphasis unmarked."""
    fragment = re.sub(r"\[?!\[[^\]]*\]\([^)]*\)(?:\]\([^)]*\))?", "", fragment)
    fragment = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", fragment)
    fragment = re.sub(r"`([^`]*)`", r"\1", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment).replace("**", "")
    return " ".join(fragment.split())


def plain_units(text):
    """[(is_heading, text)] of the README's own prose above "How it works", in order: each heading, then each
    sentence of each paragraph and list item. Fenced code, tables, quotes, HTML comments and image lines are left
    out; a <summary> counts as prose."""
    top = text.split("\n%s\n" % PLAIN_END, 1)[0]
    top = re.sub(r"<!--.*?-->", "", FENCE.sub("", top), flags=re.S)
    units, current = [], []
    def close():
        if current:
            prose = plain_text(" ".join(current))
            units.extend((False, part) for part in re.split(r"(?<=[.!?])[\"”’)]*\s+", prose) if sentence_words(part))
            del current[:]
    for line in top.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith((">", "|")) or stripped in ("<details>", "</details>"):
            close()
        elif re.match(r"#{1,6} ", stripped):
            close()
            units.append((True, plain_text(stripped.split(" ", 1)[1])))
        else:
            if re.match(r"(?:[-*]|\d+\.) ", stripped):
                close()
                stripped = stripped.split(" ", 1)[1]
            current.append(stripped)
    close()
    return units


def sentence_words(sentence):
    return [word for word in sentence.split() if re.search(r"[^\W_]", word)]


def plain_measure(text):
    """(words, sentences) of the prose above "How it works", headings left out."""
    sentences = [sentence for heading, sentence in plain_units(text) if not heading]
    return sum(len(sentence_words(sentence)) for sentence in sentences), len(sentences)


def plain_problems(text):
    """Each word of the trade used above "How it works" in a sentence that does not explain it; each technical word
    missing, or not explained where it first appears; and an average sentence over MOST_AVERAGE words."""
    units, problems = plain_units(text), []
    for _, sentence in units:
        for word in JARGON:
            if re.search(r"\b%s(?:s|es)?\b" % word, sentence, re.I) and not re.search(EXPLAINS % word, sentence, re.I):
                problems.append("%r is not explained in: %s" % (word, sentence))
    for term, explained in TECHNICAL:
        first = next((sentence for _, sentence in units if re.search(r"\b%s\b" % re.escape(term), sentence, re.I)),
                     None)
        if first is None:
            problems.append("%s is not used" % term)
        elif not re.search(explained, first, re.I):
            problems.append("%s is not explained where it first appears: %s" % (term, first))
    words, sentences = plain_measure(text)
    if not sentences or words / sentences > MOST_AVERAGE:
        problems.append("the sentences average %.1f words, over %g" % (words / max(sentences, 1), MOST_AVERAGE))
    return problems


# The FAQ's positioning, the folded quotes, and a retired wording

def faq_entries(text):
    return [line for line in (section(text, "## FAQ") or "").split("\n") if line.startswith("- **")]


def positioning_problems(text):
    """What keeps the FAQ's second entry from being the neutral answer to how the skill differs from its peers."""
    entries = faq_entries(text)
    naming = [i for i, entry in enumerate(entries) if all(peer in entry.split("**")[1] for peer in PEERS)]
    if naming != [1]:
        return ["the FAQ's second entry is not the one question that names %s" % ", ".join(PEERS)]
    problems = ["ranks: %s" % word for word in RANKING.findall(entries[1])]
    if UNTRIED not in entries[1]:
        problems.append("does not say %r" % UNTRIED)
    return problems


def plan_first_problems(text):
    """What keeps the FAQ's third entry, right after the positioning one, from answering why not just ask the agent
    for a plan by what the skill does: each step said, its qualifiers kept, nothing ranked."""
    entries = faq_entries(text)
    asking = [i for i, entry in enumerate(entries) if entry.split("**")[1] == PLAN_FIRST]
    if asking != [2]:
        return ["the FAQ's third entry is not the one question %r" % PLAN_FIRST]
    problems = ["ranks: %s" % word for word in RANKING.findall(entries[2])]
    return problems + ["does not say %r" % clause for clause in PLAN_FIRST_SAYS if clause not in entries[2]]


def folded_problems(text):
    """What keeps the person's reply and the two passages inside one <details> that GitHub renders as Markdown (a
    one-line <summary>, a blank line after it and before </details>), with the request, the line on what the skill
    found and the closing paragraph left in view."""
    lines = (section(text, "## Before and after") or "").split("\n")
    opens = [i for i, line in enumerate(lines) if line.strip() == "<details>"]
    closes = [i for i, line in enumerate(lines) if line.strip() == "</details>"]
    if len(opens) != 1 or len(closes) != 1 or opens[0] > closes[0]:
        return ["the moved lines are not inside one <details>"]
    start, end, problems = opens[0], closes[0], []
    if not re.fullmatch(r"<summary>[^<>]+</summary>", lines[start + 1].strip()):
        problems.append("no one-line <summary> right after <details>")
    elif lines[start + 2].strip():
        problems.append("no blank line after <summary>")
    if lines[end - 1].strip():
        problems.append("no blank line before </details>")
    quotes = [i for i, line in enumerate(lines)
              if line.startswith(">") and (i == 0 or not lines[i - 1].startswith(">"))]
    if [start < i < end for i in quotes] != [False, True, True, True]:
        return problems + ["the request is not in view, or the reply and the two passages are not folded"]
    if not any(line.strip() and not line.startswith(">") for line in lines[quotes[0] + 1:start]):
        problems.append("the line on what the skill found is not in view")
    if not any("](examples/" in line for line in lines[end + 1:]):
        problems.append("the closing paragraph is not in view")
    return problems


def tree_texts(root):
    """{path relative to root: text} of every file under root, .git and __pycache__ skipped."""
    texts = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in (".git", "__pycache__")]
        for name in files:
            path = os.path.join(folder, name)
            with open(path, "rb") as handle:
                texts[os.path.relpath(path, root)] = handle.read().decode("utf-8", "replace")
    return texts


def retired_problems(texts):
    return ["%s:%d: %s" % (path, number, phrase) for path, text in sorted(texts.items())
            for number, line in enumerate(text.split("\n"), 1) for phrase in RETIRED if phrase in line.lower()]


# The demo

def local(tag):
    return tag.rsplit("}", 1)[-1]


def demo_safety_problems(svg):
    """What makes the SVG unsafe, external or too heavy, or leaves it no reduced-motion rule."""
    problems = []
    if len(svg.encode("utf-8")) >= SVG_MAX_BYTES:
        problems.append("%d bytes" % len(svg.encode("utf-8")))
    for marker in ("<!DOCTYPE", "<!ENTITY", "@import", "@font-face", "javascript:"):
        if marker.lower() in svg.lower():
            problems.append("holds %s" % marker)
    for target in re.findall(r"url\(\s*['\"]?([^)'\"]*)", svg):
        if not target.startswith("#"):
            problems.append("url(%s)" % target)
    if "prefers-reduced-motion" not in svg:
        problems.append("no prefers-reduced-motion rule")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as error:
        return problems + ["not XML: %s" % error]
    if local(root.tag) != "svg":
        problems.append("the root is %s" % local(root.tag))
    for element in root.iter():
        if local(element.tag) in ("script", "foreignObject", "image", "use", "a", "iframe"):
            problems.append("a <%s> element" % local(element.tag))
        for name in element.attrib:
            if local(name) == "href" or local(name).lower().startswith("on"):
                problems.append("a %s attribute" % local(name))
    return problems


def demo_size_problems(svg):
    """Where the demo's own size is not about 960 wide and 480 to 600 tall."""
    root, problems = ET.fromstring(svg), []
    for name, (low, high) in (("width", SVG_WIDTH), ("height", SVG_HEIGHT)):
        value = re.fullmatch(r"\d+(?:\.\d+)?", root.get(name, ""))
        if not value or not low <= float(value.group(0)) <= high:
            problems.append("%s %r: not between %d and %d" % (name, root.get(name), low, high))
    if root.get("viewBox", "").split() != ["0", "0", root.get("width"), root.get("height")]:
        problems.append("the viewBox is not the SVG's own size")
    return problems


def demo_style(svg):
    """The SVG's style sheet."""
    return "".join(re.findall(r"<style>(.*?)</style>", svg, re.S))


def percent(selector):
    """A keyframe selector's offset in percent ("from" is 0, "to" 100); None for anything else."""
    selector = selector.strip()
    match = re.fullmatch(r"(\d*\.?\d+)%", selector)
    return {"from": 0.0, "to": 100.0}.get(selector, float(match.group(1)) if match else None)


@functools.lru_cache(maxsize=256)
def demo_keyframes(svg):
    """{name: [(offsets in percent, {property: value})]} of each @keyframes rule, its blocks in order."""
    found = {}
    for name, body in re.findall(r"@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*)\s*\}", svg):
        found[name] = [([percent(selector) for selector in selectors.split(",")],
                        {key.strip(): value.strip() for key, _, value in
                         (part.partition(":") for part in declarations.split(";")) if key.strip()})
                       for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", body)]
    return found


@functools.lru_cache(maxsize=256)
def demo_cycle(svg):
    """(seconds, easing, count) of the `.a` rule's animation, the one every animated element runs: its length, its
    timing function ("ease" when it gives none) and its iteration count ("1" when it gives none); None without one."""
    rule = [declared["animation"] for selector, declared in style_rules(svg)
            if selector == ".a" and "animation" in declared]
    if not rule:
        return None
    easing = re.search(r"(?:cubic-bezier|steps)\([^)]*\)|\b(?:linear|ease(?:-in-out|-in|-out)?|step-start|step-end)\b",
                       rule[0])
    rest = rule[0].replace(easing.group(0), " ") if easing else rule[0]
    seconds = re.findall(r"(?<![\w.])(\d*\.?\d+)s\b", rest)
    counts = re.findall(r"(?<![\w.])(infinite|\d*\.?\d+)(?![\w.%])", rest)
    return (float(seconds[0]) if seconds else None, easing.group(0) if easing else "ease",
            counts[0] if counts else "1")


def own_motion(element, svg):
    """(the keyframes' name, the start, the seconds, the starting state, the end state) of the change an element of
    class `a` runs in each cycle: the keyframes its style names hold their first block's state from 0% to that
    block's last offset (the start), then reach the next block's state at its offset; None for an element of no class
    `a`, or one whose keyframes are not so made."""
    if "a" not in element.get("class", "").split():
        return None
    name = re.search(r"animation-name\s*:\s*([\w-]+)", element.get("style", ""))
    blocks = demo_keyframes(svg).get(name.group(1)) if name else None
    period = (demo_cycle(svg) or (None,))[0]
    if not period or not blocks or len(blocks) < 2 or None in blocks[0][0] + blocks[1][0] or 0.0 not in blocks[0][0]:
        return None
    start, end = max(blocks[0][0]), min(blocks[1][0])
    return (name.group(1), round(start * period / 100, 3), round((end - start) * period / 100, 3), blocks[0][1],
            blocks[1][1])


def own_start(element, svg):
    """When in each cycle an element of class `a` starts its change; None for any other, or one with no change."""
    motion = own_motion(element, svg)
    return motion[1] if motion else None


def demo_texts(svg):
    """[(text, data, start)] of each <text> of the SVG, in order: its text; the data-* attributes of it and of the
    elements around it (its own first); and when it starts to show, the latest start among it and those elements."""
    root = ET.fromstring(svg)
    parents = {child: parent for parent in root.iter() for child in parent}
    texts = []
    for element in root.iter():
        if local(element.tag) != "text":
            continue
        data, start, around = {}, 0.0, element
        while around is not None:
            for name, value in around.attrib.items():
                if name.startswith("data-"):
                    data.setdefault(name[5:], value)
            start = max(start, own_start(around, svg) or 0.0)
            around = parents.get(around)
        texts.append(("".join(element.itertext()), data, start))
    return texts


def on_screen_words(svg):
    """The words the SVG shows: each whitespace-separated piece of its text that holds a letter or a digit."""
    return [word for text, _, _ in demo_texts(svg) for word in text.split() if re.search(r"[^\W_]", word)]


def demo_times(svg):
    """[(start, end)] in seconds into the cycle of each change of the build: every element of class `a` but the group
    that resets the frame."""
    motions = [own_motion(element, svg) for element in ET.fromstring(svg).iter() if element.get("data-loop") is None]
    return [(motion[1], round(motion[1] + motion[2], 3)) for motion in motions if motion]


def demo_last_frame_problems(svg):
    """What could keep the last frame from showing at once where motion is reduced or nothing is animated: something
    hidden outside the keyframes, or a reduced-motion rule that leaves `.a` animated."""
    style = "".join(re.findall(r"<style>(.*?)</style>", svg, re.S))
    outside = re.sub(r"@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*\s*\}", "", style) + svg.replace(style, "")
    hiding = r"(?<![\w-])(opacity\s*[:=]\s*\"?0*\.?0*(?![.\d])|display\s*[:=]\s*\"?none|visibility\s*[:=]\s*\"?hidden)"
    problems = ["hidden outside the keyframes: %s" % match.group(0) for match in re.finditer(hiding, outside)]
    reduced = re.search(r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{((?:[^{}]*\{[^{}]*\})*)\s*\}",
                        style)
    stops = [body for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", reduced.group(1) if reduced else "")
             if ".a" in [selector.strip() for selector in selectors.split(",")]]
    if not any(re.search(r"animation(-name)?\s*:\s*none", body) for body in stops):
        problems.append("the reduced-motion rule does not stop .a")
    return problems


# What an element shows when no keyframes act on it, for the properties the keyframes animate.
INITIAL = {"opacity": "1", "transform": "none", "stroke-dashoffset": "0"}


def demo_cycle_problems(svg):
    """What keeps the demo from repeating without end as one cycle (built, held, reset): the `.a` rule not the one
    animation, of one length and with no end (any other length, delay, count or easing, anywhere, would let an element
    drift from the others); an element of class `a` whose keyframes are not of the cycle's making (a starting state
    held from 0% to its moment, then its end state), or that end on a state other than its own style, so the frame
    moves while it should hold; an animated element outside the group that resets the frame; that group fading
    during the build; the complete frame holding still for less than HOLD seconds; or a reset that is not one fade
    of RESET seconds or more to an empty frame that stays empty until the cycle ends, so a cycle starts with a cut."""
    cycle, problems = demo_cycle(svg), []
    if not cycle or not cycle[0]:
        return ["no `.a` rule gives the cycle's length"]
    period, _, count = cycle
    if count != "infinite":
        problems.append("the cycle plays %s times, not without end" % count)
    rest = re.sub(r"\.a\{[^}]*\}", "", demo_style(svg), count=1).replace("animation:none!important", "")
    rest += re.sub(r"<style>.*?</style>", "", svg, flags=re.S)
    problems += ["an animation timing of its own: %s" % found
                 for found in re.findall(r"(?<![\w-])animation(?:-(?!name\b)[\w-]+)?\s*:[^;}\"]*", rest)]
    root, rules = ET.fromstring(svg), style_rules(svg)
    loops = [element for element in root.iter() if element.get("data-loop") is not None]
    if len(loops) != 1 or "a" not in loops[0].get("class", "").split():
        return problems + ["no one group of class `a` marked data-loop resets the frame"]
    inside = set(loops[0].iter())
    for element in root.iter():
        if element is loops[0] or not ("a" in element.get("class", "").split() or local(element.tag) == "text"):
            continue
        if element not in inside:
            problems.append("a <%s> does not fade out with the rest" % local(element.tag))
        motion = own_motion(element, svg)
        if motion is None:
            if "a" in element.get("class", "").split():
                problems.append("a <%s> runs no keyframes of the cycle: %r" % (local(element.tag),
                                                                              element.get("style")))
            continue
        name, _, _, _, end = motion
        if len(demo_keyframes(svg)[name]) != 2:
            problems.append("the keyframes %s change more than once in a cycle" % name)
        own = dict(INITIAL)
        own.update(styled(element, rules))
        problems += ["the keyframes %s end on %s:%s, not the element's own %s, so the frame moves while it holds"
                     % (name, key, value, own.get(key)) for key, value in sorted(end.items()) if own.get(key) != value]
    name = re.search(r"animation-name\s*:\s*([\w-]+)", loops[0].get("style", ""))
    points = {}
    for offsets, declared in demo_keyframes(svg).get(name.group(1) if name else "", []):
        for offset in offsets:
            if offset is not None and "opacity" in declared:
                points[round(offset * period / 100, 3)] = float(declared["opacity"])
    if not points:
        return problems + ["the group that resets the frame runs no keyframes of its opacity"]
    base = float(styled(loops[0], rules).get("opacity", INITIAL["opacity"]))
    points = sorted(dict([(0.0, base), (period, base)] + list(points.items())).items())
    builds = demo_times(svg)
    if not builds:
        return problems + ["nothing is built"]
    first, still = min(start for start, _ in builds), max(end for _, end in builds)
    whole = max([at for at, opacity in points if opacity == 1], default=0.0)
    problems += ["the frame fades during the build, at %g s" % at for at, opacity in points
                 if first <= at <= whole and opacity != 1]
    if whole - still < HOLD:
        problems.append("the complete frame holds %.1f s, under %s s" % (whole - still, HOLD))
    gone = [at for at, opacity in points if at > whole and opacity == 0]
    if not gone:
        problems.append("the frame is whole as the cycle ends, so the next one starts with a cut")
    elif gone[0] - whole < RESET:
        problems.append("the reset fades the frame out in %.2f s, under %s s: a cut" % (gone[0] - whole, RESET))
    elif any(opacity for at, opacity in points if at > gone[0]):
        problems.append("the frame comes back before the cycle ends, so the next one starts with a cut")
    return problems


def example_files(folder):
    return {name: read(os.path.join(folder, name)) for name in ("README.md", "decisions.md", FILE)}


def brand_names(decisions):
    """The brand the page is for (the decisions' title) and every site the log names as "Name (domain)"."""
    names = re.findall(r"^# Decisions — (\S+)", decisions, re.M)
    for name, domain in re.findall(r"([A-Z][A-Za-z]*(?: [A-Z][A-Za-z]*)*) \(([a-z0-9-]+(?:\.[a-z0-9-]+)+)\)",
                                   decisions):
        names += [name, domain]
    return names


def demo_words_problems(svg, decisions):
    """A brand name, a word that claims a result ("built", "shipped", "launched", "finished", "done"), a harness named,
    or a claim the evidence does not carry, anywhere in the SVG's text or title. A name is matched as written (so the
    word "seed" is no brand), a domain in any case."""
    root = ET.fromstring(svg)
    text = "\n".join("".join(e.itertext()) for e in root.iter() if local(e.tag) in ("text", "title", "desc"))
    problems = ["names %s" % name for name in brand_names(decisions)
                if re.search(r"(?<![\w.-])%s(?![\w-])" % re.escape(name), text, re.I if "." in name else 0)]
    problems += ["claims a result: %s" % word for word in RESULT_WORDS.findall(text)]
    problems += ["names %s" % name for name in DEMO_HARNESSES
                 if re.search(r"(?<![\w.-])%s(?![\w-])" % re.escape(name), text)]
    return problems + ["claims %s" % claim for claim in claim_problems(text)]


def demo_caption(readme):
    """(the alt text, the caption) of the README's demo: the image's text, then the next line that is not blank."""
    lines = readme.split("\n")
    at = next(i for i, line in enumerate(lines) if "](docs/media/demo.svg)" in line)
    alt = re.search(r"!\[([^\]]*)\]\(docs/media/demo\.svg\)", lines[at])
    caption = next((line for line in lines[at + 1:] if line.strip()), "")
    return (alt.group(1) if alt else ""), caption


def caption_problems(readme):
    """What the alt text or the caption leaves unsaid: the prompt is a real one the skill wrote, and a model answered
    its questions."""
    alt, caption = demo_caption(readme)
    return ["the %s does not say %r" % (name, phrase) for name, text in (("alt text", alt), ("caption", caption))
            for phrase in CAPTION if phrase not in text]


def alt_problems(readme, svg):
    """Each line the demo shows that the alt text does not list: the beats, the quote, the file's name and the
    thumbnail's rows (a line set on two being one), compared without regard to case."""
    alt = demo_caption(readme)[0].lower()
    shown = list(demo_beats(svg).values()) + [demo_quote(svg), FILE]
    shown += [value for kind, value in thumbnail(svg) if kind == "row"]
    return ["the alt text does not list %r" % text for text in shown if text.lower() not in alt]


def demo_example(readme):
    """The example folder the caption under the demo links."""
    lines = readme.split("\n")
    at = next(i for i, line in enumerate(lines) if "docs/media/demo.svg" in line)
    for line in lines[at + 1:]:
        if line.startswith("#"):
            break
        match = re.search(r"\]\((examples/[^)/]+)/\)", line)
        if match:
            return os.path.join(ROOT, match.group(1))
    return None


def style_rules(svg):
    """[(selector, {property: value})] of the style sheet's plain rules, in order; @keyframes and @media left out."""
    style = "".join(re.findall(r"<style>(.*?)</style>", svg, re.S))
    plain = re.sub(r"@[\w-]+[^{]*\{(?:[^{}]*\{[^{}]*\})*\s*\}", "", style)
    rules = []
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", plain):
        declared = {name.strip(): value.strip() for name, _, value in
                    (declaration.partition(":") for declaration in body.split(";")) if name.strip()}
        rules += [(selector.strip(), declared) for selector in selectors.split(",")]
    return rules


def styled(element, rules):
    """The properties the style sheet's class rules give `element`: a rule applies when the element has every class
    its selector names; a selector naming more classes wins, then a later rule."""
    classes = set(element.get("class", "").split())
    matching = [(len(selector.split(".")) - 1, n, declared) for n, (selector, declared) in enumerate(rules)
                if re.fullmatch(r"(\.[\w-]+)+", selector) and set(selector.split(".")[1:]) <= classes]
    found = {}
    for _, _, declared in sorted(matching, key=lambda rule: rule[:2]):
        found.update(declared)
    return found


def text_elements(svg):
    """[(element, text, data, start)] of each <text> of the SVG, as demo_texts gives them, with the element."""
    elements = [element for element in ET.fromstring(svg).iter() if local(element.tag) == "text"]
    return [(element,) + found for element, found in zip(elements, demo_texts(svg))]


def demo_beats(svg):
    """{beat number: its lines joined} of the texts in the groups marked data-beat."""
    beats = {}
    for text, data, _ in demo_texts(svg):
        if "beat" in data:
            beats[data["beat"]] = (beats.get(data["beat"], "") + " " + text).strip()
    return beats


def beat_problems(svg, readme):
    """Unless the beats say BEATS, the example's README carries each one's fact, and the last frame shows the earlier
    beats settled to muted and the last one in ink."""
    beats, problems = demo_beats(svg), []
    shown = [beats.get(str(n + 1)) for n in range(len(BEATS))]
    if shown != list(BEATS) or len(beats) != len(BEATS):
        problems.append("the beats say %r" % shown)
    problems += ["the README does not say %r" % fact for fact in BEAT_FACTS if fact not in readme]
    rules = style_rules(svg)
    for element, text, data, _ in text_elements(svg):
        if "beat" in data:
            fill = styled(element, rules).get("fill")
            wanted = INK if data["beat"] == str(len(BEATS)) else MUTED
            if fill != wanted:
                problems.append("%r ends in %s, not %s" % (text, fill, wanted))
    return problems


def demo_quote(svg):
    """The quote under the first beat, its lines joined."""
    return " ".join(text for text, data, _ in demo_texts(svg) if "quote" in data)


def demo_type_problems(svg):
    """Type that is not as the demo sets it: the beats BEAT_PX or larger and semibold, every other text MIN_FONT_PX or
    larger; every size from the style sheet; the sans stack for every text but the file name, which is mono."""
    problems = []
    if re.search(r"(?<![\w-])font\s*:", svg):
        problems.append("a font shorthand, whose size is not checked")
    if re.search(r"font-size=|style=\"[^\"]*font", svg):
        problems.append("a font set outside the style sheet")
    rules = style_rules(svg)
    for element, text, data, _ in text_elements(svg):
        style = styled(element, rules)
        size = re.fullmatch(r"(\d*\.?\d+)px", style.get("font-size", ""))
        least = BEAT_PX if "beat" in data else MIN_FONT_PX
        if not size or float(size.group(1)) < least:
            problems.append("%r is set at %s, under %d px" % (text, style.get("font-size"), least))
        weight = {"normal": "400", "bold": "700"}.get(style.get("font-weight", "400"), style.get("font-weight"))
        if "beat" in data and not (weight.isdigit() and 500 <= int(weight) <= 700):
            problems.append("%r is not semibold: font-weight %s" % (text, weight))
        family = style.get("font-family", "")
        if not family.endswith("monospace" if "file" in data else "sans-serif"):
            problems.append("%r is set in %r" % (text, family[-30:]))
    return problems


def demo_word_problems(svg):
    """More than MOST_WORDS words on screen, or more than BEAT_WORDS in the beats and the quote."""
    problems, count = [], len(on_screen_words(svg))
    if count > MOST_WORDS:
        problems.append("%d words on screen, more than %d" % (count, MOST_WORDS))
    beats = " ".join(list(demo_beats(svg).values()) + [demo_quote(svg)])
    if len(beats.split()) > BEAT_WORDS:
        problems.append("%d words in the beats and the quote, more than %d" % (len(beats.split()), BEAT_WORDS))
    return problems


def word_edge(text, at):
    """Whether position `at` of `text` falls between two words, not inside one."""
    return at <= 0 or at >= len(text) or not (text[at - 1].isalnum() and text[at].isalnum())


def quote_problems(svg, readme):
    """Unless the quote is fragments of the README's English translation, each at word edges and after the one
    before it, in quotation marks, with an ellipsis wherever words of the translation are dropped and nowhere else."""
    english = re.search(r'^\s*In English: "(.+)"\s*$', readme, re.M)
    whole, shown = (english.group(1) if english else ""), demo_quote(svg)
    if not (len(shown) > 2 and shown[0] == "“" and shown[-1] == "”"):
        return ["the quote %r is not in quotation marks" % shown]
    pieces, at, problems = shown[1:-1].split("…"), 0, []
    for n, piece in enumerate(pieces):
        piece = piece.strip()
        if not piece:
            continue
        found = whole.find(piece, at)
        if found < 0:
            problems.append("%r is not in the translation after the fragment before it" % piece)
            continue
        if not (word_edge(whole, found) and word_edge(whole, found + len(piece))):
            problems.append("%r cuts a word of the translation" % piece)
        if bool(re.search(r"\w", whole[at:found])) != (n > 0):
            problems.append("before %r: %s" % (piece, "an ellipsis drops nothing" if n else "words dropped unmarked"))
        at = found + len(piece)
    if bool(re.search(r"\w", whole[at:])) != shown[1:-1].endswith("…"):
        problems.append("at the end: %s" % ("an ellipsis drops nothing" if shown[1:-1].endswith("…")
                                            else "words dropped unmarked"))
    return problems


def prompt_headings(prompt):
    """The `##` headings of a prompt, in order; fenced code holds none."""
    return [line[3:].strip() for _, line in heading_lines(prompt.split("\n")) if line.startswith("## ")]


def thumbnail(svg):
    """The thumbnail's items in order: ("row", heading), a heading set on two lines being one row, or ("gap", how many
    headings it stands for, as its data-gap counts them)."""
    card = next((element for element in ET.fromstring(svg).iter() if element.get("data-card")), None)
    items = []
    for element in [] if card is None else card.iter():
        if element.get("data-gap") is not None:
            items.append(["gap", element.get("data-gap")])
        elif local(element.tag) == "text" and element.get("data-row"):
            line = "".join(element.itertext())
            if items and items[-1][0] == "row" and items[-1][2] == element.get("data-row"):
                items[-1][1] += " " + line
            else:
                items.append(["row", line, element.get("data-row")])
    return [tuple(item[:2]) for item in items]


def thumbnail_problems(svg, prompt):
    """Unless the thumbnail is the file's name, then rows that are `##` headings of the prompt in its order, with a gap
    exactly where headings are skipped (at the start, between two rows, at the end), each counting what it skips (a
    count, not the headings' names, which the file already holds)."""
    texts, problems = demo_texts(svg), []
    if [text for text, data, _ in texts if "file" in data] != [FILE]:
        problems.append("the thumbnail does not name %s" % FILE)
    headings, items = prompt_headings(prompt), thumbnail(svg)
    rows = [value for kind, value in items if kind == "row"]
    expected, at = [], -1
    for row in rows:
        if row not in headings[at + 1:]:
            problems.append("%r is not a `##` heading of %s after the row before it" % (row, FILE))
            continue
        found = headings.index(row, at + 1)
        if found > at + 1:
            expected.append(("gap", str(found - at - 1)))
        expected.append(("row", row))
        at = found
    if at < len(headings) - 1:
        expected.append(("gap", str(len(headings) - at - 1)))
    if not rows or items != expected:
        problems.append("the rows and gaps are %r; %s gives %r" % (items, FILE, expected))
    return problems


def picked_problems(svg):
    """Unless exactly PICKED are picked out (class `pick`), each turning after the one above it, and the accent is
    theirs alone in the last frame."""
    rules, picked, begins, problems = style_rules(svg), [], [], []
    for element, text, data, _ in text_elements(svg):
        if "row" not in data:
            continue
        pick = "pick" in element.get("class", "").split()
        if pick and data["row"] not in picked:
            picked.append(data["row"])
            begins.append(own_start(element, svg))
        if (styled(element, rules).get("fill") == ACCENT) != pick:
            problems.append("%r is %s in the accent" % (text, "picked out but not" if pick else "not picked out but"))
    if picked != list(PICKED):
        problems.append("the picked-out rows are %r" % picked)
    elif None in begins or begins != sorted(set(begins)):
        problems.append("the rows are not picked out one after another: %r" % begins)
    return problems


def demo_timing_problems(svg):
    """What keeps the demo from moving as it should in each cycle: every change a fade-and-rise of DURATION, or a
    draw of DRAW for an arrow's line and head, all with the cycle's one easing, which does not overshoot; rising at
    most RISE px, every other keyframe at most sliding; the beats in order, the quote with the first, the thumbnail
    with the third and its rows picked out after it lands; an earlier beat settling only as the next lands, the last
    never; each beat and the quote shown whole at once; still by VISIBLE_BY, nothing later than LONGEST."""
    times = demo_times(svg)
    if not times:
        return ["nothing is animated"]
    problems, root = [], ET.fromstring(svg)
    easing = (demo_cycle(svg) or (None, "", None))[1]
    curve = re.fullmatch(r"cubic-bezier\(([^)]*)\)", easing)
    if curve and not all(0 <= float(value) <= 1 for value in curve.group(1).split(",")[1::2]):
        problems.append("the easing %s overshoots" % easing)
    problems += ["an easing of its own: %s" % found for found in re.findall(r"animation-timing-function\s*:[^;}\"]*",
                                                                            svg)]
    arrows = {part for group in root.iter() if group.get("data-arrow") is not None for part in group.iter()}
    for element in root.iter():
        motion = own_motion(element, svg) if element.get("data-loop") is None else None
        if not motion:
            continue
        name, _, seconds, begin, _ = motion
        (low, high), kind = (DRAW, "draw") if element in arrows else (DURATION, "fade-and-rise")
        if not low <= seconds <= high:
            problems.append("a %s of %g s" % (kind, seconds))
        for move, amount in re.findall(r"(translate[XY])\(\s*(-?\d*\.?\d+)", begin.get("transform", "")):
            if element not in arrows and (move != "translateY" or abs(float(amount)) > RISE):
                problems.append("the keyframes %s %s(%s)" % (name, move, amount))
    for name, blocks in demo_keyframes(svg).items():
        for _, declared in blocks:
            problems += ["the keyframes %s %s(%s)" % (name, move, amount) for move, amount in
                         re.findall(r"(\w+)\(\s*(-?\d*\.?\d+)", declared.get("transform", ""))
                         if move not in ("translateX", "translateY")]
    marked = {}
    for element in root.iter():
        for key in ("beat", "quote", "card"):
            if element.get("data-" + key) is not None:
                marked.setdefault(key, {})[element.get("data-" + key)] = own_start(element, svg)
    beats = [marked.get("beat", {}).get(str(n)) for n in (1, 2, 3)]
    quote, card = list(marked.get("quote", {}).values()), list(marked.get("card", {}).values())
    if None in beats or any(a >= b for a, b in zip(beats, beats[1:])):
        return problems + ["the beats do not land one after another: %r" % beats]
    if len(quote) != 1 or quote[0] is None or not beats[0] <= quote[0] < beats[1]:
        problems.append("the quote does not land with the first beat: %r" % quote)
    if len(card) != 1 or card[0] is None or card[0] < beats[2]:
        problems.append("the thumbnail does not land with the third beat: %r" % card)
    landed = max([beats[2]] + [begin for begin in card if begin is not None])
    for element, text, data, _ in text_elements(svg):
        classes, begins = element.get("class", "").split(), own_start(element, svg)
        if "pick" in classes and (begins is None or begins < landed):
            problems.append("%r is picked out before the thumbnail lands" % text)
        if "settle" in classes:
            beat = int(data.get("beat", len(BEATS)))
            if beat >= len(BEATS):
                problems.append("%r settles, though no beat comes after it" % text)
            elif begins is None or begins < beats[beat]:
                problems.append("%r settles before the next beat lands" % text)
    for key in ("beat", "quote"):
        begins = {}
        for _, data, begin in demo_texts(svg):
            if key in data:
                begins.setdefault(data[key], set()).add(begin)
        problems += ["%s %s does not show whole at once" % (key, name) for name, found in sorted(begins.items())
                     if len(found) > 1]
    still = max(end for _, end in times)
    if still > VISIBLE_BY:
        problems.append("still moving at %.1f s, after %s s" % (still, VISIBLE_BY))
    if still > LONGEST:
        problems.append("an animation runs to %.1f s, later than %s s" % (still, LONGEST))
    return problems


def demo_look_problems(svg):
    """What the demo never has: a gradient, a filter, a pattern or a mask; a shadow or a blur; a colour outside the social
    image's palette; an emoji."""
    root, problems = ET.fromstring(svg), []
    problems += ["a <%s> element" % local(element.tag) for element in root.iter() if local(element.tag) in
                 ("linearGradient", "radialGradient", "filter", "pattern", "mask", "clipPath")]
    markup = re.sub(r"(<(text|title)\b[^>]*>)[^<]*", r"\1", re.sub(r"\sdata-[\w-]+=\"[^\"]*\"", "", svg))
    problems += ["holds %s" % word for word in ("filter", "shadow", "blur", "gradient", "blend") if word in markup]
    problems += ["the colour %s" % colour for colour in sorted(set(re.findall(r"#[0-9a-fA-F]{3,8}\b", markup)))
                 if colour.lower() not in PALETTE]
    problems += ["the colour %s" % found for found in re.findall(r"\b(?:rgba?|hsla?)\(", markup)]
    problems += ["an emoji in %r" % text for text, _, _ in demo_texts(svg)
                 if any(0x1F000 <= ord(char) <= 0x1FAFF or 0x2600 <= ord(char) <= 0x27BF for char in text)]
    return problems


def path_points(d):
    """The points a path of absolute M, L, H and V commands passes through; None for any other command (a curve, a
    close, a relative step)."""
    points, command, pending = [], None, []
    for token in re.findall(r"[A-Za-z]|-?\d*\.?\d+", d):
        if token.isalpha():
            if token not in "MLHV" or token != "M" and not points or pending:
                return None
            command = token
        elif command is None:
            return None
        elif command in "ML":
            pending.append(float(token))
            if len(pending) == 2:
                points.append(tuple(pending))
                pending = []
        elif command in "HV":
            x, y = points[-1]
            points.append((float(token), y) if command == "H" else (x, float(token)))
        else:
            return None
    return None if pending else points


def cascade(element, rules, svg):
    """(the properties of `element` from its class rules, the name of the keyframes it runs in each cycle, the
    seconds its change takes); None for either where it runs none."""
    motion = own_motion(element, svg)
    return styled(element, rules), motion[0] if motion else None, motion[2] if motion else None


def demo_arrows(svg):
    """[(number, its group, its line, its head)] of the groups marked data-arrow, in order: the line the group's path of
    class `line`, the head its path of class `head` (None unless there is exactly one)."""
    found = []
    for group in ET.fromstring(svg).iter():
        if group.get("data-arrow") is None:
            continue
        parts = [[path for path in group if local(path.tag) == "path" and kind in path.get("class", "").split()]
                 for kind in ("line", "head")]
        found.append((group.get("data-arrow"), group) + tuple(part[0] if len(part) == 1 else None for part in parts))
    return found


def arrow_look(group, part, rules):
    """The properties an arrow's line or head shows with: its group's class rules, then its own, then its own
    presentation attributes."""
    look = styled(group, rules)
    look.update(styled(part, rules))
    look.update({name: part.get(name) for name in ("fill", "stroke", "stroke-width", "stroke-linecap")
                 if part.get(name)})
    return look


def keyframes_from(svg):
    """{name: {property: value}} of the state each @keyframes rule starts from: its block at 0%."""
    return {name: blocks[0][1] for name, blocks in demo_keyframes(svg).items() if blocks and 0.0 in blocks[0][0]}


def demo_frame(svg):
    """({beat number: [(baseline, px)] of its block, its lines and, under the first, the quote's}, the card's rect)."""
    rules, blocks = style_rules(svg), {}
    for element, _, data, _ in text_elements(svg):
        key = data.get("beat") or ("1" if "quote" in data else None)
        if key:
            size = re.fullmatch(r"(\d*\.?\d+)px", styled(element, rules).get("font-size", ""))
            blocks.setdefault(key, []).append((float(element.get("y")), float(size.group(1)) if size else 0.0))
    card = next((element for element in ET.fromstring(svg).iter()
                 if local(element.tag) == "rect" and "card" in element.get("class", "").split()), None)
    return {key: sorted(lines) for key, lines in blocks.items()}, card


def chevron_problems(number, line, head):
    """Unless the head is an open chevron at the line's end: two strokes meeting there, reaching back on either side
    of the line by as much, neither further than HEAD px."""
    (x0, y0), (x1, y1) = line
    if not head or len(head) != 3 or head[1] != (x1, y1):
        return ["arrow %s's head is not two strokes meeting at its line's end: %r" % (number, head)]
    run = max(abs(x1 - x0), abs(y1 - y0)) or 1
    ahead = ((x1 - x0) / run, (y1 - y0) / run)
    back = [(x - x1) * ahead[0] + (y - y1) * ahead[1] for x, y in (head[0], head[2])]
    side = [(x - x1) * ahead[1] - (y - y1) * ahead[0] for x, y in (head[0], head[2])]
    if not (back[0] == back[1] < 0 and side[0] == -side[1] != 0 and max(map(abs, back + side)) <= HEAD):
        return ["arrow %s's chevron does not reach back evenly on both sides: %r" % (number, head)]
    return []


def arrow_problems(svg):
    """What keeps the arrows from drawing the story's flow: ARROWS of them, numbered in order; each a straight line
    ending in an open chevron, unfilled, with round caps, stroked STROKE px wide, the connectors dim and the last one
    the accent; each connector down the left column, below the last line of the beat above (its quote counted) and
    above the next beat's cap line; the last one along the last beat's last line, from past its last word in any font
    to exactly TIP_GAP px short of the card's edge, level with its straight edge, clear of the corners."""
    arrows, (blocks, card), rules, problems = demo_arrows(svg), demo_frame(svg), style_rules(svg), []
    numbers = [number for number, _, _, _ in arrows]
    if numbers != [str(n) for n in range(1, ARROWS + 1)]:
        return ["the arrows are numbered %r, not 1 to %d" % (numbers, ARROWS)]
    if card is None or sorted(blocks) != numbers:
        return ["not one block of text per beat beside a card"]
    edge, top = float(card.get("x")) - .5, float(card.get("y"))
    bottom, corner = top + float(card.get("height")), float(card.get("rx", 0))
    for number, group, line, head in arrows:
        if line is None or head is None:
            problems.append("arrow %s is not one line and one head" % number)
            continue
        for part in (line, head):
            look = arrow_look(group, part, rules)
            width = re.fullmatch(r"(\d*\.?\d+)(px)?", look.get("stroke-width", ""))
            if not width or not STROKE[0] <= float(width.group(1)) <= STROKE[1]:
                problems.append("arrow %s is stroked %s wide" % (number, look.get("stroke-width")))
            colour = ACCENT if number == str(ARROWS) else DIM
            if look.get("stroke") != colour:
                problems.append("arrow %s is stroked %s, not %s" % (number, look.get("stroke"), colour))
            if look.get("fill") != "none" or look.get("stroke-linecap") != "round":
                problems.append("arrow %s is filled %s, with %s caps" % (number, look.get("fill"),
                                                                        look.get("stroke-linecap")))
        ends = path_points(line.get("d", ""))
        if not ends or len(ends) != 2 or (ends[0][0] == ends[1][0]) == (ends[0][1] == ends[1][1]):
            problems.append("arrow %s's line is not one straight stroke across or down: %r" % (number, line.get("d")))
            continue
        problems += chevron_problems(number, ends, path_points(head.get("d", "")))
        (x0, y0), (x1, y1) = ends
        if number != str(ARROWS):
            above, below = blocks[number][-1], blocks[str(int(number) + 1)][0]
            if not (x0 == x1 and MARGIN <= x0 < edge and y0 < y1):
                problems.append("arrow %s does not run down the left column" % number)
            elif not above[0] + .25 * above[1] <= y0 < y1 <= below[0] - .75 * below[1]:
                problems.append("arrow %s does not run between beat %s and beat %d" % (number, number, int(number) + 1))
            continue
        last = blocks[number][-1]
        words = [text for _, text, data, _ in text_elements(svg) if data.get("beat") == number][-1]
        if not (y0 == y1 and x0 < x1):
            problems.append("arrow %s does not run across to the right" % number)
        elif x1 != edge - TIP_GAP:
            problems.append("arrow %s ends at %g, not %d px short of the card's edge %g" % (number, x1, TIP_GAP, edge))
        elif not top + corner + HEAD <= y1 <= bottom - corner - HEAD:
            problems.append("arrow %s meets the card at %g, off its straight edge" % (number, y1))
        elif not last[0] - .55 * last[1] <= y0 <= last[0]:
            problems.append("arrow %s does not run along beat %s's last line" % (number, number))
        elif x0 < MARGIN + len(words) * last[1] * WIDEST:
            problems.append("arrow %s starts at %g, where beat %s's last word may still be" % (number, x0, number))
    return problems


def landing_problems(svg):
    """What keeps the last arrow from landing on the card itself rather than on one of its sections: its line or its
    chevron level with a row's text (from the baseline up by the cap height and down by the descent, ROW_INK ems of
    the row's size) or with a gap mark; the card's border not the accent in the last frame; or the border not turning
    to it as the arrow's tip arrives (an animation of its own from another colour, starting as the line has drawn)."""
    arrows, (_, card), rules = demo_arrows(svg), demo_frame(svg), style_rules(svg)
    last = [(line, head) for number, _, line, head in arrows if number == str(ARROWS)]
    ends = path_points(last[0][0].get("d", "")) if last and last[0][0] is not None else None
    if not ends or len(ends) != 2 or ends[0][1] != ends[1][1] or card is None:
        return ["no arrow %d across into a card" % ARROWS]
    line, head = last[0]
    tip = [y for _, y in (path_points(head.get("d", "")) if head is not None else None) or []] + [ends[1][1]]
    low, high, problems = min(tip), max(tip), []
    for element, text, data, _ in text_elements(svg):
        size = re.fullmatch(r"(\d*\.?\d+)px", styled(element, rules).get("font-size", ""))
        if "row" in data and size:
            base, px = float(element.get("y")), float(size.group(1))
            if base - ROW_INK[0] * px < high and low < base + ROW_INK[1] * px:
                problems.append("arrow %d is level with the row %r" % (ARROWS, text))
    for gap in ET.fromstring(svg).iter():
        dots = [(float(dot.get("cy")), float(dot.get("r"))) for dot in gap if local(dot.tag) == "circle"]
        if gap.get("data-gap") is not None and dots and \
                min(y - r for y, r in dots) < high and low < max(y + r for y, r in dots):
            problems.append("arrow %d is level with a gap mark" % ARROWS)
    look, name, _ = cascade(card, rules, svg)
    if look.get("stroke") != ACCENT:
        problems.append("the card's border ends in %s, not the accent %s" % (look.get("stroke"), ACCENT))
    turn = keyframes_from(svg).get(name, {}) if "a" in card.get("class", "").split() else {}
    if turn.get("stroke") in (None, ACCENT) or set(turn) != {"stroke"}:
        problems.append("the card's border does not turn to the accent: %s %r" % (name, turn))
    draws, turns = cascade(line, rules, svg)[2], own_start(card, svg)
    arrives = (own_start(line, svg) or 0.0) + (draws or 0.0)
    if turns is None or abs(turns - arrives) > .01:
        problems.append("the card's border turns at %s s, not as the arrow's tip arrives at %.2f s" % (turns, arrives))
    return problems


def dash_problems(svg):
    """Unless every arrow's line draws itself on with a dash of its own length in user units: no pathLength (a
    renderer that ignores it would lay the dash pattern out in user units, dotting the line), one dash as long as the
    line with a gap at least as long, and its draw's keyframes starting the dash offset at that length."""
    rules, frames, problems = style_rules(svg), keyframes_from(svg), []
    problems += ["a pathLength on a <%s>" % local(element.tag) for element in ET.fromstring(svg).iter()
                 if element.get("pathLength") is not None]
    for number, group, line, _ in demo_arrows(svg):
        points = path_points(line.get("d", "")) if line is not None else None
        if not points:
            problems.append("arrow %s has no straight line" % number)
            continue
        length = sum(abs(x1 - x0) + abs(y1 - y0) for (x0, y0), (x1, y1) in zip(points, points[1:]))
        dash = [float(value) for value in re.findall(r"\d*\.?\d+", arrow_look(group, line, rules).get(
            "stroke-dasharray", ""))]
        if not (dash == [length] or len(dash) == 2 and dash[0] == length <= dash[1]):
            problems.append("arrow %s's dash is %r, not its length %g" % (number, dash, length))
        name = cascade(line, rules, svg)[1]
        hidden = frames.get(name, {}).get("stroke-dashoffset")
        if hidden is None or float(hidden) != length:
            problems.append("arrow %s's line does not start hidden: %s's dash offset %s, not %g"
                            % (number, name, hidden, length))
    return problems


def arrow_motion_problems(svg):
    """What keeps an arrow from drawing itself on in turn and from being whole in the last frame: its line drawn on
    (its dash, which dash_problems checks) and its head riding the line's end there (from the line's start, hidden),
    both of class `a`, with one start, over DRAW; a connector starting once the block above it has landed and still
    drawing as the next beat lands; the last arrow drawing as the card appears, done before a row is picked out; and
    in the base state, nothing offset, moved or faded, and every head where its line ends."""
    rules, frames, problems = style_rules(svg), keyframes_from(svg), []
    root = ET.fromstring(svg)
    motions = {key: {element.get("data-" + key): own_motion(element, svg) for element in root.iter()
                     if element.get("data-" + key) is not None} for key in ("beat", "quote", "card")}
    starts = {key: {at: motion and motion[1] for at, motion in found.items()} for key, found in motions.items()}
    landed = {key: {at: motion and motion[1] + motion[2] for at, motion in found.items()}
              for key, found in motions.items()}
    picked = [own_start(element, svg) for element in root.iter() if "pick" in element.get("class", "").split()]
    began = []
    for number, group, line, head in demo_arrows(svg):
        if line is None or head is None:
            problems.append("arrow %s is not one line and one head" % number)
            continue
        (look, name, seconds), (_, ride, ride_seconds) = cascade(line, rules, svg), cascade(head, rules, svg)
        start = own_start(line, svg)
        if start is None or own_start(head, svg) != start or "a" not in head.get("class", "").split():
            problems.append("arrow %s's head does not start with its line" % number)
        if set(frames.get(name, {})) != {"stroke-dashoffset"} or ride_seconds != seconds or seconds is None \
                or not DRAW[0] <= seconds <= DRAW[1]:
            problems.append("arrow %s does not draw on over %s s: %s, %s" % (number, DRAW, name, seconds))
            continue
        own = [name for part in (group, line, head) for name in ("transform", "opacity", "stroke-dasharray",
                                                                "stroke-dashoffset") if part.get(name) is not None]
        own += [found for part in (group, line, head)
                for found in re.findall(r"[\w-]*(?:dash|transform|opacity)[\w-]*", part.get("style", ""))]
        if float(look.get("stroke-dashoffset", "0")) or own:
            problems.append("arrow %s is offset, moved or faded in the base state: %r" % (number, own))
        ends = path_points(line.get("d", "")) or []
        (x0, y0), (x1, y1) = ends if len(ends) == 2 else ((0, 0), (0, 0))
        state = frames.get(ride, {})
        slide = re.fullmatch(r"translate([XY])\((-?\d*\.?\d+)px\)", state.get("transform", ""))
        back = {"X": x0 - x1, "Y": y0 - y1}
        if not slide or float(slide.group(2)) != back[slide.group(1)] or back["X" if slide.group(1) == "Y" else "Y"] \
                or state.get("opacity") != "0":
            problems.append("arrow %s's head does not ride from its line's start, hidden: %s %r"
                            % (number, ride, state))
        began.append(start or 0.0)
        if number != str(ARROWS):
            above = [landed["beat"].get(number)] + ([landed["quote"].get("1")] if number == "1" else [])
            after = starts["beat"].get(str(int(number) + 1))
            if None in above or after is None or start is None:
                problems.append("arrow %s has no beats around it" % number)
            elif start < max(above):
                problems.append("arrow %s draws before the block above it has landed" % number)
            elif not start <= after <= start + seconds:
                problems.append("arrow %s does not draw as beat %s lands" % (number, int(number) + 1))
            continue
        card, card_landed = list(starts["card"].values()), list(landed["card"].values())
        if len(card) != 1 or None in card or start is None or not card[0] <= start < card_landed[0]:
            problems.append("arrow %s does not draw as the card appears" % number)
        elif picked and start + seconds > min(picked):
            problems.append("arrow %s is still drawing when a row is picked out" % number)
    if began != sorted(began) or len(set(began)) != len(began):
        problems.append("the arrows do not draw one after another: %r" % began)
    return problems


def demo_frame_problems(svg):
    """What the frame of the demo does not hold: every line left of the card starting on the MARGIN px margin; each
    gap mark three dots at least DOT[0] px in radius and DOT[1] px apart, in a column; the card CARD_WIDTH px
    wide with its border; the file's name FILE_PX px."""
    (blocks, card), rules, problems = demo_frame(svg), style_rules(svg), []
    for element, text, data, _ in text_elements(svg):
        if ("beat" in data or "quote" in data) and float(element.get("x", "0")) != MARGIN:
            problems.append("%r starts at %s, not on the %d px margin" % (text, element.get("x"), MARGIN))
        if "file" in data and styled(element, rules).get("font-size") != "%dpx" % FILE_PX:
            problems.append("the file's name is set at %s, not %d px" % (styled(element, rules).get("font-size"),
                                                                        FILE_PX))
    border = re.fullmatch(r"(\d*\.?\d+)(px)?", styled(card, rules).get("stroke-width", "0") if card is not None else "")
    if card is None or not border or float(card.get("width")) + float(border.group(1)) != CARD_WIDTH:
        problems.append("the card is not %d px wide with its border" % CARD_WIDTH)
    for gap in ET.fromstring(svg).iter():
        if gap.get("data-gap") is None:
            continue
        spots = sorted((float(dot.get("cy")), float(dot.get("cx")), float(dot.get("r")))
                       for dot in gap if local(dot.tag) == "circle")
        steps = [b[0] - a[0] for a, b in zip(spots, spots[1:])]
        if len(spots) != 3 or len(gap) != 3 or len({x for _, x, _ in spots}) != 1 \
                or min(r for _, _, r in spots) < DOT[0] or min(steps) < DOT[1]:
            problems.append("a gap mark is not three dots of %g px or more, %g px or more apart: %r"
                            % (DOT[0], DOT[1], spots))
    return problems


# Tests

class FirstScreen(unittest.TestCase):
    def test_the_promise_and_the_install_lines_come_first(self):
        self.assertEqual(first_screen_problems(read(README)), [])

    def test_a_next_step_dropped_moved_below_the_demo_sent_elsewhere_or_grown_long_is_caught(self):
        text = read(README)
        step = [p.strip() for p in text.split("\n", 1)[1].split("\n\n") if p.strip()][2]
        caption = next(line for line in text.split("\n") if line.startswith("<sub>"))
        dropped = text.replace(step + "\n\n", "", 1)
        for name, planted in (
                ("dropped", dropped),
                ("below the demo", dropped.replace(caption + "\n", caption + "\n\n" + step + "\n", 1)),
                ("sent elsewhere", text.replace(step, step.replace(NEXT_STEP, "](docs/install.md)"), 1)),
                ("on two lines", text.replace(step, step.replace(": [", ":\n[", 1), 1)),
                ("grown long", text.replace(step, step + " It reads your files, then asks what it cannot find.", 1))):
            with self.subTest(plant=name):
                self.assertNotEqual(planted, text)
                self.assertIn("the line under who it is for is not one short line that leads to the install lines",
                              first_screen_problems(planted))

    def test_a_section_moved_above_install_is_caught(self):
        text = read(README)
        moved = text.replace("## Install\n", "## Why it helps\n\nIt helps.\n\n## Install\n", 1)
        self.assertNotEqual(moved, text)
        self.assertIn("the first section is not Install", first_screen_problems(moved))

    def test_every_readme_command_is_a_route_of_the_install_page(self):
        self.assertEqual(readme_commands_problems(read(README), read(INSTALL)), [])

    def test_a_command_that_drifts_from_the_install_page_is_caught(self):
        drifted = read(README).replace("npx skills add ", "npx skills install ", 1)
        self.assertTrue(readme_commands_problems(drifted, read(INSTALL)))

    def test_an_old_title_an_old_promise_or_a_line_under_it_that_drops_who_it_is_for_is_caught(self):
        text = read(README)
        title, rest = text.split("\n", 1)
        promise, audience = [p.strip() for p in rest.split("\n\n") if p.strip()][:2]
        for planted, expected in (
                (title.replace(TITLE, "master prompts for coding agents") + "\n" + rest, "line 1 is not the title"),
                (text.replace(promise, "**%s turns a task into a master prompt.**" % NAME_TOKEN, 1),
                 "the promise is not the first paragraph"),
                (text.replace(audience + "\n\n", "", 1), "the line under the promise does not say"),
                (text.replace(audience, audience.replace(" or Codex", ""), 1),
                 "the line under the promise does not say")):
            with self.subTest(expected=expected, planted=planted[:60]):
                self.assertNotEqual(planted, text)
                self.assertTrue(any(problem.startswith(expected) for problem in first_screen_problems(planted)))

    def test_the_release_badge_sits_in_the_badge_row_on_the_repository(self):
        self.assertEqual(release_badge_problems(read(README)), [])

    def test_a_release_badge_on_another_repository_or_out_of_the_row_is_caught(self):
        text = read(README)
        ci = re.search(r"github\.com/([^\s()]+?)/actions/workflows/ci", text)
        repo = REPO_TOKEN if STAGED else ci.group(1)
        badge = RELEASE_BADGE.format(repo=repo)
        for planted in (text.replace("github.com/%s/releases" % repo, "github.com/someone/else/releases", 1),
                        text.replace("release/%s)" % repo, "release/someone/else)", 1),
                        text.replace(" " + badge, "", 1) + "\n" + badge + "\n"):
            with self.subTest(planted=planted[planted.find("[![Release"):][:80]):
                self.assertNotEqual(planted, text)
                self.assertTrue(release_badge_problems(planted))


class Links(unittest.TestCase):
    def test_every_relative_link_and_anchor_resolves(self):
        for path in LINKED:
            with self.subTest(file=os.path.relpath(path, ROOT)):
                self.assertEqual(link_problems(path, read(path)), [])

    def test_the_pages_link_each_other_and_the_demo(self):
        readme = read(README)
        for target in ("docs/install.md", "docs/media/demo.svg"):
            self.assertIn("](%s" % target, readme)

    def test_a_broken_file_and_a_broken_anchor_are_caught(self):
        text = read(README) + "\n[a](docs/missing.md) [b](#no-such-heading) [c](docs/install.md#no-such-heading)\n"
        found = link_problems(README, text)
        self.assertEqual(len(found), 3, found)


class Claims(unittest.TestCase):
    def test_the_readme_makes_no_unsupported_claim(self):
        self.assertEqual(claim_problems(read(README)), [])

    def test_each_unsupported_claim_is_caught(self):
        for planted in ("It is better than writing it by hand.", "No task lost.", "It wins every time.",
                        "It wins.", "It read the site's four files.", "Tested on Gemini CLI 0.63.0.",
                        "It is tested on Codex and Copilot CLI.", "Tested in Cursor.",
                        "Tested on claude.ai and the GitHub CLI (October 2026).",
                        "Tested on Codex, OpenCode; also tested with Cursor."):
            with self.subTest(planted=planted):
                self.assertTrue(claim_problems(read(README) + "\n" + planted + "\n"))


class KeptClauses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {os.path.basename(path): read(path) for path in LINKED}

    def test_each_clause_that_holds_a_claim_is_kept(self):
        self.assertEqual(kept_problems(self.texts), [])

    def test_a_dropped_clause_is_caught(self):
        for name, heading, clause in KEPT:
            with self.subTest(clause=clause):
                self.assertIn(clause, self.texts[name])
                planted = dict(self.texts, **{name: self.texts[name].replace(clause, "", 1)})
                self.assertEqual(kept_problems(planted), ["%s, %s: %r" % (name, heading.strip(), clause)])


class PlainWords(unittest.TestCase):
    def test_the_top_half_is_plain(self):
        self.assertEqual(plain_problems(read(README)), [])

    def test_only_the_page_s_own_prose_is_measured(self):
        sample = ("# T — x\n\n**One two three.** Four five.\n\n[![b](i.svg)](u) ![alt words here](a.svg)\n\n"
                  "> Quoted words are left out.\n\n```sh\ncode words\n```\n\n| a | b |\n|---|---|\n| c | d |\n\n"
                  "- Item [link text](u) `code`.\n\n<details>\n<summary>Sum mary</summary>\n\n</details>\n\n"
                  + PLAIN_END + "\n\nAfter words.\n")
        self.assertEqual(plain_units(sample), [(True, "T — x"), (False, "One two three."), (False, "Four five."),
                                               (False, "Item link text code."), (False, "Sum mary")])
        self.assertEqual(plain_measure(sample), (11, 4))

    def test_an_unexplained_word_of_the_trade_is_caught_and_an_explained_one_is_not(self):
        text = read(README)
        for old, new, word in (("A script checks every plan", "A linter checks every plan", "linter"),
                               ("where your agent can start them", "where the harness can start them", "harness"),
                               ("where your agent can start them", "where the harness, the model and the plan allow",
                                "harness"),
                               ("turns \"done\" into checks", "turns \"done\" into a bar of checks", "bar")):
            with self.subTest(word=word):
                self.assertIn(old, text)
                found = plain_problems(text.replace(old, new, 1))
                self.assertTrue(any(problem.startswith("%r is not explained" % word) for problem in found), found)
        explained = text.replace("where your agent can start them",
                                 "where the harness (the tool your agent runs in) can start them", 1)
        self.assertNotEqual(explained, text)
        self.assertEqual(plain_problems(explained), [])

    def test_a_technical_word_hidden_or_unexplained_where_it_first_appears_is_caught(self):
        text = read(README)
        named = "who hands work to an AI coding agent such as Claude Code or Codex."
        unnamed = "who runs Claude Code or Codex and hands work to an AI coding agent."
        for old, new, expected in (
                ("a master prompt: one file that", "a master prompt that", "master prompt is not explained"),
                (" (helper agents that have not seen your chat)", "", "subagents is not explained"),
                ("its stop rules end the work", "its stop rules apply", "stop rules is not explained"),
                ("## Install\n", "Your agent may start subagents.\n\n## Install\n", "subagents is not explained"),
                (" in the open Agent Skills format", "", "Agent Skills is not used"),
                (", a shared standard many AI agents read", "", "Agent Skills is not explained"),
                (named, unnamed, "Claude Code is not explained"),
                (named, unnamed, "Codex is not explained")):
            with self.subTest(expected=expected):
                self.assertIn(old, text)
                found = plain_problems(text.replace(old, new, 1))
                self.assertTrue(any(problem.startswith(expected) for problem in found), found)

    def test_claude_code_and_codex_called_ai_coding_agents_are_explained(self):
        text = read(README)
        old = "who hands work to an AI coding agent such as Claude Code or Codex."
        for new in ("who hands work to Claude Code or Codex (AI coding agents).",
                    "who hands work to an AI agent. Claude Code and Codex are AI coding agents."):
            with self.subTest(new=new):
                self.assertIn(old, text)
                self.assertEqual(plain_problems(text.replace(old, new, 1)), [])

    def test_agent_skills_said_to_be_a_standard_agents_read_is_explained(self):
        text = read(README)
        old = "in the open Agent Skills format, a shared standard many AI agents read"
        for new in ("in Agent Skills — an open standard that many AI agents read",
                    "in the Agent Skills format: a standard that AI coding agents share"):
            with self.subTest(new=new):
                self.assertIn(old, text)
                self.assertEqual(plain_problems(text.replace(old, new, 1)), [])

    def test_short_sentences_strung_back_into_long_ones_are_caught(self):
        text = read(README)
        top, rest = text.split("\n%s\n" % PLAIN_END, 1)
        strung = re.sub(r"(?<=[a-z])\. (?=[A-Z])", ", and ", top) + "\n%s\n" % PLAIN_END + rest
        self.assertNotEqual(strung, text)
        self.assertTrue(any(problem.startswith("the sentences average") for problem in plain_problems(strung)))


class Positioning(unittest.TestCase):
    def test_the_second_faq_entry_places_it_among_its_peers_without_ranking(self):
        self.assertEqual(positioning_problems(read(README)), [])

    def test_a_moved_a_narrowed_a_ranking_or_an_untrue_entry_is_caught(self):
        text = read(README)
        entries = faq_entries(text)
        plants = [text.replace(entries[1] + "\n" + entries[2], entries[2] + "\n" + entries[1], 1),
                  text.replace("Task Master or superpowers?", "or superpowers?", 1),
                  text.replace(UNTRIED, "It works well alongside all of them.", 1)]
        plants += [text.replace(entries[1], entries[1] + " It is %s." % words, 1)
                   for words in ("better", "unlike them", "what they lack", "worse", "superior", "simpler than them")]
        for planted in plants:
            with self.subTest(planted=[entry for entry in faq_entries(planted) if entry not in entries][:1]):
                self.assertNotEqual(planted, text)
                self.assertTrue(positioning_problems(planted))


class PlanFirst(unittest.TestCase):
    def test_the_third_faq_entry_says_what_the_skill_does_with_a_plan_request(self):
        self.assertEqual(plan_first_problems(read(README)), [])

    def test_a_moved_a_reworded_a_ranking_or_a_narrowed_entry_is_caught(self):
        text = read(README)
        entries = faq_entries(text)
        moved = "the FAQ's third entry is not the one question %r" % PLAN_FIRST
        swap = lambda a, b: text.replace(entries[a] + "\n" + entries[b], entries[b] + "\n" + entries[a], 1)
        plants = [("moved down", swap(2, 3), moved), ("moved up", swap(1, 2), moved),
                  ("reworded", text.replace(PLAN_FIRST, "Why not just ask my agent for a plan?", 1), moved)]
        plants += [(words, text.replace(entries[2], entries[2] + " It is %s." % words, 1), "ranks: ")
                   for words in ("better", "unlike your agent", "what your agent lacks", "more careful than it")]
        plants += [("without " + clause, text.replace(entries[2], entries[2].replace(clause, "", 1), 1),
                    "does not say %r" % clause) for clause in PLAN_FIRST_SAYS]
        for name, planted, expected in plants:
            with self.subTest(plant=name):
                self.assertNotEqual(planted, text)
                found = plan_first_problems(planted)
                self.assertTrue(any(problem.startswith(expected) for problem in found), (expected, found))


class Folded(unittest.TestCase):
    def test_the_reply_and_the_two_passages_are_folded_and_the_rest_is_in_view(self):
        self.assertEqual(folded_problems(read(README)), [])

    def test_a_fold_github_would_not_render_or_that_folds_too_much_or_too_little_is_caught(self):
        text = read(README)
        head = re.search(r"<details>\n<summary>[^\n]*</summary>\n\n", text).group(0)
        for planted, expected in (
                (text.replace(head, head[:-1], 1), "no blank line after <summary>"),
                (text.replace("\n\n</details>\n", "\n</details>\n", 1), "no blank line before </details>"),
                (text.replace(head, "", 1).replace("</details>\n", "", 1), "not inside one <details>"),
                (text.replace("\n> **Ruled out", "\n</details>\n\n> **Ruled out", 1)
                     .replace("\n\n</details>\n\nThe rest", "\n\nThe rest", 1), "not folded"),
                (text.replace(head, "", 1).replace("> Hi, can you", head + "> Hi, can you", 1), "not in view")):
            with self.subTest(expected=expected):
                self.assertNotEqual(planted, text)
                self.assertTrue(any(expected in problem for problem in folded_problems(planted)),
                                folded_problems(planted))


class RetiredWording(unittest.TestCase):
    def test_no_file_reads_as_if_the_landing_page_were_built(self):
        self.assertEqual(retired_problems(tree_texts(ROOT)), [])

    def test_the_wording_is_caught_in_any_file_and_any_case(self):
        planted = dict(tree_texts(ROOT), **{"examples/x/README.md": "# A page, %s in the cloud\n" % RETIRED[0].title()})
        self.assertEqual(retired_problems(planted), ["examples/x/README.md:1: " + RETIRED[0]])


class InstallStatuses(unittest.TestCase):
    def test_only_the_five_routes_run_are_tested_and_the_rest_documented(self):
        self.assertEqual(status_problems(read(INSTALL)), [])

    def test_the_readme_says_which_routes_are_tested_and_calls_no_other_tested(self):
        readme = read(README)
        self.assertIn("Tested on Claude Code, Codex, OpenCode, Antigravity and claude.ai (October 2026). Also "
                      "installs on Gemini CLI, Copilot CLI, Cursor and the GitHub CLI; reports welcome.", readme)
        self.assertEqual([claim for claim in claim_problems(readme) if claim == UNTESTED_CLAIM], [])

    def test_a_route_marked_tested_that_was_not_or_a_tested_route_misdated_is_caught(self):
        text = read(INSTALL)
        for old, new, harness in (
                ("| installs and removes cleanly from a clone (0.63.0, 2026-10-13) |",
                 "| tested on 0.63.0, 2026-10-13 |", "Gemini CLI"),
                ("| installs and removes cleanly from a clone (0.63.0, 2026-10-13) |",
                 "| installs and removes cleanly (0.63.0, 2026-10-13) |", "Gemini CLI"),
                ("| documented |\n| GitHub CLI", "| tested on 1.0.95, 2026-10-13 |\n| GitHub CLI", "Copilot CLI"),
                ("(preview; gh 2.90 or newer) | documented |", "(preview; gh 2.90 or newer) | tested on 2.102.0, "
                 "2026-10-13 |", "GitHub CLI"),
                ("-a cursor` | documented |", "-a cursor` | documented, tested |", "Cursor"),
                ("tested on 0.162.1, 2026-10-13", "tested on 0.162.1", "Codex"),
                ("-a opencode` | tested on 1.19.0, 2026-10-13 |", "-a opencode` | tested on 2026-10-13 |", "OpenCode"),
                ("-a antigravity` | tested on 2.23.0, 2026-10-13 |", "-a antigravity` | documented |", "Antigravity"),
                ("| tested on 2.1.296, 2026-10-13 (marketplace", "| tested (marketplace", "Claude Code")):
            with self.subTest(change=new):
                self.assertIn(old, text)
                self.assertIn(harness, " ".join(status_problems(text.replace(old, new, 1))))


class Demo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = read(DEMO)
        cls.readme = read(README)
        cls.example = demo_example(cls.readme)
        cls.files = example_files(cls.example)

    def planted(self, old, new):
        """The SVG with its first `old` replaced by `new`; `old` must be there."""
        self.assertIn(old, self.svg)
        return self.svg.replace(old, new, 1)

    def restarted(self, markup, seconds, length=None):
        """The SVG with the elements in `markup` (a piece of it) running their change from `seconds` into the cycle,
        over `length` seconds (their own when None): each keyframes `markup` names is copied, so moved, under a new
        name that only `markup` uses."""
        period, moved, added = demo_cycle(self.svg)[0], markup, []
        for name in sorted(set(re.findall(r"animation-name:([\w-]+)", markup))):
            begin, end = re.search(r"@keyframes %s\{0%%,[\d.]+%%\{([^}]*)\}[\d.]+%%\{([^}]*)\}\}" % name,
                                   self.svg).groups()
            own = [motion for motion in (own_motion(element, self.svg) for element in ET.fromstring(self.svg).iter())
                   if motion and motion[0] == name][0][2]
            added.append("@keyframes %s-moved{0%%,%g%%{%s}%g%%{%s}}" % (
                name, seconds * 100 / period, begin, (seconds + (length or own)) * 100 / period, end))
            moved = moved.replace("animation-name:%s\"" % name, "animation-name:%s-moved\"" % name)
        planted = self.planted(markup, moved)
        return planted.replace("\n@media", "\n%s\n@media" % "\n".join(added), 1)

    def plant_text(self, text):
        """The SVG with one more line of text before its end."""
        return self.svg.replace("</svg>", '<text class="quote" x="56" y="40">%s</text>\n</svg>' % text, 1)

    def assertCaught(self, found, expected):
        self.assertTrue(any(expected in problem for problem in found), (expected, found))

    def test_the_demo_is_a_safe_self_contained_svg(self):
        self.assertEqual(demo_safety_problems(self.svg), [])
        for plant, expected in (('<script>alert(1)</script>', "a <script> element"),
                                ('<rect fill="url(https://example.com/p)"/>', "url(https://example.com/p"),
                                ('<!ENTITY x "y">', "holds <!ENTITY")):
            with self.subTest(plant=plant[:40]):
                self.assertCaught(demo_safety_problems(self.svg.replace("</svg>", plant + "</svg>", 1)), expected)

    def test_the_demo_is_about_960_wide_and_as_tall_as_its_layout(self):
        self.assertEqual(demo_size_problems(self.svg), [])
        root = ET.fromstring(self.svg)
        for name, value in (("width", "1200"), ("height", "640"), ("height", "400")):
            with self.subTest(**{name: value}):
                planted = self.planted('%s="%s"' % (name, root.get(name)), '%s="%s"' % (name, value))
                self.assertCaught(demo_size_problems(planted), "%s '%s'" % (name, value))

    def test_large_beats_and_no_text_under_20_px(self):
        self.assertEqual(demo_type_problems(self.svg), [])
        beat = re.search(r"\.beat\{[^}]*", self.svg).group(0)
        row = re.search(r"\.row\{[^}]*", self.svg).group(0)
        mono = re.search(r"\.file\{font-family:[^;]*", self.svg).group(0)
        for planted, expected in (
                (self.planted(beat, beat.replace("font-size:%dpx" % BEAT_PX, "font-size:40px")),
                 "under %d px" % BEAT_PX),
                (self.planted(row, re.sub(r"font-size:\d+px", "font-size:18px", row)), "under %d px" % MIN_FONT_PX),
                (self.planted(beat, beat.replace("font-weight:600", "font-weight:900")), "not semibold"),
                (self.planted(mono, ".file{font-family:serif"), "'master-prompt.md' is set in 'serif'"),
                (self.planted(beat, beat + ";font:12px serif"), "a font shorthand"),
                (self.planted("<text class=\"quote\"", '<text font-size="12" class="quote"'), "outside the style")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_type_problems(planted), expected)

    def test_at_most_about_40_words_and_25_in_the_beats(self):
        self.assertEqual(demo_word_problems(self.svg), [])
        for planted, expected in ((self.plant_text("It also reads every file you have."), "words on screen"),
                                  (self.planted(">A plan your agent<", ">A clear, detailed plan your agent<"),
                                   "in the beats and the quote")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_word_problems(planted), expected)

    def test_the_three_beats_say_what_the_example_carries(self):
        self.assertEqual(beat_problems(self.svg, self.files["README.md"]), [])
        readme, settle = self.files["README.md"], re.search(r"\.settle\{fill:[^}]*\}", self.svg).group(0)
        for planted, text, expected in (
                (self.planted(">One message in.<", ">One sentence in.<"), readme, "the beats say"),
                (self.planted(">can run alone.<", ">runs by itself.<"), readme, "the beats say"),
                (self.svg, readme.replace("whole first message", "first message"), "does not say"),
                (self.planted(settle, ".settle{fill:%s}" % INK), readme, "ends in %s, not %s" % (INK, MUTED))):
            with self.subTest(expected=expected):
                self.assertCaught(beat_problems(planted, text), expected)

    def test_the_quote_is_fragments_of_the_translation_in_order(self):
        self.assertEqual(quote_problems(self.svg, self.files["README.md"]), [])
        for old, new, expected in (
                ("looks premium", "looks luxurious", "not in the translation"),
                ("“…a landing", "“a landing", "words dropped unmarked"),
                ("premium…”", "premium”", "at the end: words dropped unmarked"),
                ("for my supplement", "for my… supplement", "an ellipsis drops nothing"),
                ("“…a landing", "“…nding", "cuts a word"),
                ("“…a landing page for my supplement", "“…that looks premium… a landing page for my supplement",
                 "after the fragment before it"),
                ("“…a landing", "…a landing", "quotation marks")):
            with self.subTest(change=new):
                self.assertCaught(quote_problems(self.planted(old, new), self.files["README.md"]), expected)

    def test_the_thumbnail_rows_are_the_prompt_s_headings_in_order_with_every_gap_shown(self):
        prompt = self.files[FILE]
        self.assertEqual(thumbnail_problems(self.svg, prompt), [])
        rows = [value for kind, value in thumbnail(self.svg) if kind == "row"]
        self.assertTrue(set(PICKED) <= set(rows))
        gap = re.search(r'<g class="gap" data-gap="\d+">[^\n]*</g>\n(?=<text [^>]*data-row="Stop rules)',
                        self.svg).group(0)
        method = re.search(r'<text [^>]*data-row="Method"[^>]*>Method</text>\n', self.svg).group(0)
        bar = re.search(r'<text [^>]*data-row="The bar"[^>]*>The bar</text>\n', self.svg).group(0)
        for planted, expected in (
                (self.svg.replace(">The bar<", ">The checks<", 1).replace('"The bar"', '"The checks"'),
                 "'The checks' is not a `##` heading"),
                (self.planted(gap, ""), "the rows and gaps are"),
                (self.planted(bar, '<g class="gap" data-gap=""></g>\n' + bar), "the rows and gaps are"),
                (self.planted(method + bar, bar + method), "'Method' is not a `##` heading of %s after" % FILE),
                (self.planted(">%s<" % FILE, ">prompt.md<"), "does not name"),
                (self.planted('data-gap="1"', 'data-gap="Working folder"'), "the rows and gaps are"),
                (self.planted('data-gap="5"', 'data-gap="4"'), "the rows and gaps are")):
            with self.subTest(expected=expected):
                self.assertCaught(thumbnail_problems(planted, prompt), expected)

    def test_a_changed_example_makes_the_thumbnail_stale(self):
        prompt = self.files[FILE]
        for old, new in (("\n## Subagent contracts\n", "\n## Budget\n\nTwo hours.\n\n## Subagent contracts\n"),
                         ("\n## The bar\n", "\n## The checks\n"),
                         ("\n## Scope\n", "\n")):
            with self.subTest(change=new.strip()[:20]):
                self.assertIn(old, prompt)
                self.assertTrue(thumbnail_problems(self.svg, prompt.replace(old, new, 1)))
        fenced = prompt.replace("\n## Scope\n", "\n```\n## Not a heading\n```\n\n## Scope\n", 1)
        self.assertEqual(thumbnail_problems(self.svg, fenced), [])

    def test_every_row_from_mission_to_the_stop_rules_is_picked_out_in_the_accent_in_turn(self):
        self.assertEqual(picked_problems(self.svg), [])
        pick = re.search(r"\.pick\{fill:[^}]*\}", self.svg).group(0)
        row = re.search(r"\.row\{[^}]*\}", self.svg).group(0)
        mission = re.search(r'<text class="row a pick"( [^>]*data-row="Mission") style="animation-name:[\w-]+"',
                            self.svg)
        unpicked = '<text class="row"%s' % mission.group(1)
        for planted, expected in (
                (self.planted(mission.group(0), unpicked), "the picked-out rows are ['Method', "),
                (re.sub(r'<text class="row a pick"( [^>]*data-row="Stop rules)', r'<text class="row"\1', self.svg),
                 "the picked-out rows are ['Mission', 'Method', 'The bar']"),
                (self.planted(pick, ".pick{fill:#93c5fd}"), "picked out but not in the accent"),
                (self.planted(mission.group(0), unpicked).replace(row, row.replace(MUTED, ACCENT), 1),
                 "'Mission' is not picked out but in the accent"),
                (self.restarted(mission.group(0), 6.5), "not picked out one after another"),
                (self.restarted(mission.group(0), 5.9), "not picked out one after another")):
            with self.subTest(expected=expected):
                self.assertCaught(picked_problems(planted), expected)

    def test_the_beats_land_in_turn_and_all_is_still_by_seven_seconds(self):
        self.assertEqual(demo_timing_problems(self.svg), [])
        self.assertLessEqual(max(end for _, end in demo_times(self.svg)), VISIBLE_BY)

    def test_a_late_an_unordered_a_typed_or_a_bouncing_demo_is_caught(self):
        def moved(key, value, seconds, length=None):
            found = re.search(r'<[^>]* data-%s="%s"[^>]*>' % (key, re.escape(value)), self.svg)
            return self.restarted(found.group(0), seconds, length)
        easing = re.search(r"cubic-bezier\([^)]*\)", self.svg).group(0)
        rise = re.search(r"translateY\(\d+px\)", self.svg).group(0)
        settle = re.search(r'<text class="beat a settle"[^>]*>', self.svg).group(0)
        last = re.search(r'<g class="a" data-beat="3"[^>]*>\n<text class="beat"', self.svg).group(0)
        line = re.search(r'<path class="line a"[^>]*>', self.svg).group(0)
        for planted, expected in (
                (moved("card", FILE, 0.5), "the thumbnail does not land with the third beat"),
                (moved("beat", "2", 0.1), "the beats do not land one after another"),
                (moved("quote", "1", 3.5), "the quote does not land with the first beat"),
                (moved("row", "The bar", 9.6), "still moving at 10.3 s"),
                (moved("row", "The bar", 9.6), "later than %s s" % LONGEST),
                (moved("row", "Method", 0.5), "is picked out before the thumbnail lands"),
                (self.restarted(settle, 1.0), "settles before the next beat"),
                (self.planted(last, last[:-1] + ' a settle" style="animation-name:settle-440"'),
                 "no beat comes after it"),
                (self.planted(easing, "cubic-bezier(.3,1.6,.6,1)"), "overshoots"),
                (self.planted("8%{opacity:1", "8%{animation-timing-function:linear;opacity:1"),
                 "an easing of its own: animation-timing-function:linear"),
                (self.planted(rise, "translateY(24px)"), "translateY(24)"),
                (self.planted(rise, "scale(1.2)"), "scale(1.2)"),
                (moved("beat", "2", 2.6, 1.2), "a fade-and-rise of 1.2 s"),
                (self.restarted(line, 2.4, .9), "a draw of 0.9 s")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_timing_problems(planted), expected)

    def test_the_last_frame_shows_at_once_when_motion_is_reduced(self):
        self.assertEqual(demo_last_frame_problems(self.svg), [])
        for planted, expected in ((self.planted(".card{", ".a{opacity:0}.card{"), "hidden outside the keyframes"),
                                  (self.planted("{.a{animation:none!important}}", "{.a{opacity:1}}"),
                                   "does not stop .a")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_last_frame_problems(planted), expected)

    def test_one_cycle_builds_holds_still_and_fades_out_together_without_end(self):
        self.assertEqual(demo_cycle_problems(self.svg), [])
        loop = re.search(r"@keyframes loop\{[^\n]*\}\}", self.svg).group(0)
        whole, gone = re.search(r"([\d.]+)%\{opacity:1\}([\d.]+)%,100%\{opacity:0\}\}", loop).groups()
        pick = re.search(r'<text class="row a pick"[^>]* style="animation-name:([\w-]+)"', self.svg)
        ends = re.search(r"@keyframes %s\{[^\n]*%%\{fill:%s\}\}" % (pick.group(1), ACCENT), self.svg).group(0)
        outside = self.svg.replace('<g class="arrow into"', '</g>\n<g class="arrow into"', 1).replace(
            "</g>\n</g>\n</svg>", "</g>\n</svg>", 1)
        for planted, expected in (
                (self.planted(" infinite}", "}"), "the cycle plays 1 times, not without end"),
                (self.planted(" infinite}", " 3}"), "the cycle plays 3 times, not without end"),
                (self.planted(pick.group(0), pick.group(0)[:-1] + ';animation-duration:12s"'),
                 "an animation timing of its own: animation-duration:12s"),
                (self.planted(".pick{", ".a.pick{animation-duration:10s}.pick{"),
                 "an animation timing of its own: animation-duration:10s"),
                (self.planted(pick.group(0), pick.group(0)[:-1] + ';animation-delay:1s"'),
                 "an animation timing of its own: animation-delay:1s"),
                (self.planted(pick.group(0), pick.group(0).split(" style=")[0]), "runs no keyframes of the cycle"),
                (self.planted(ends, ends.replace("{fill:%s}}" % ACCENT, "{fill:%s}}" % MUTED)),
                 "so the frame moves while it holds"),
                (self.planted(loop, loop.replace(whole + "%", "85.6%")), "holds 3.7 s, under %s s" % HOLD),
                (self.planted(loop, "@keyframes loop{0%{opacity:0}2.4%,100%{opacity:1}}"),
                 "whole as the cycle ends, so the next one starts with a cut"),
                (self.planted(loop, loop.replace(gone + "%,", "93.7%,")), "under %s s: a cut" % RESET),
                (self.planted(loop, loop.replace(gone + "%,100%", gone + "%")),
                 "whole as the cycle ends, so the next one starts with a cut"),
                (self.planted(loop, loop.replace("100%{opacity:0}", "{opacity:0}99.2%{opacity:.5}100%{opacity:0}")
                              .replace(gone + "%,{", gone + "%{")),
                 "comes back before the cycle ends"),
                (self.planted(loop, loop.replace(whole + "%{opacity:1}", "40%%{opacity:.5}%s%%{opacity:1}" % whole)),
                 "the frame fades during the build"),
                (outside, "a <path> does not fade out with the rest"),
                (self.planted(' data-loop="1"', ""), "no one group of class `a` marked data-loop")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_cycle_problems(planted), expected)

    def test_no_gradient_shadow_stray_colour_or_emoji(self):
        self.assertEqual(demo_look_problems(self.svg), [])
        for planted, expected in (
                (self.svg.replace("</svg>", '<defs><radialGradient id="g"/></defs></svg>', 1), "<radialGradient>"),
                (self.planted(".card{", ".card{filter:drop-shadow(0 8px 24px #000);"), "holds filter"),
                (self.planted(ACCENT, "#22d3ee"), "the colour #22d3ee"),
                (self.plant_text("Ready \U0001F680"), "an emoji")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_look_problems(planted), expected)

    def test_no_brand_no_result_no_harness_named(self):
        decisions = self.files["decisions.md"]
        self.assertEqual(demo_words_problems(self.svg, decisions), [])
        for plant, expected in [(name, "names %s" % name) for name in brand_names(decisions)] + [
                ("The page was built tonight.", "claims a result: built"),
                ("Finished by morning.", "claims a result: Finished"),
                ("All done.", "claims a result: done"),
                ("Better than writing it by hand.", "claims better than"),
                ("Runs in Claude Code.", "names Claude Code"),
                ("Or in Codex.", "names Codex")]:
            with self.subTest(plant=plant):
                self.assertCaught(demo_words_problems(self.plant_text(plant), decisions), expected)


    def group_of(self, number):
        """Arrow `number`'s group, as the SVG holds it."""
        return re.search(r'<g class="arrow[^"]*" data-arrow="%d">.*?</g>\n' % number, self.svg, re.S).group(0)

    def arrow_at(self, number, seconds):
        """The SVG with arrow `number`'s line and head starting at `seconds`."""
        return self.restarted(self.group_of(number), seconds)

    def test_three_arrows_lead_from_beat_to_beat_and_into_the_card(self):
        self.assertEqual(arrow_problems(self.svg), [])
        lines = re.findall(r'<path class="line[^"]*"[^>]* d="([^"]+)"', self.svg)
        heads = re.findall(r'<path class="head[^"]*" d="([^"]+)"', self.svg)
        arrow = re.search(r"\.arrow\{[^}]*\}", self.svg).group(0)
        x0, y0, x1 = re.fullmatch(r"M(\d+) (\d+)H(\d+)", lines[2]).groups()
        for planted, expected in (
                (self.planted(self.group_of(2), ""), "numbered ['1', '3']"),
                (self.svg.replace("</svg>", self.group_of(3).replace('-arrow="3"', '-arrow="4"') + "</svg>", 1),
                 "not 1 to 3"),
                (self.planted(lines[0], re.sub(r"M(\d+) \d+", r"M\1 176", lines[0])), "between beat 1 and beat 2"),
                (self.planted(lines[1], re.sub(r"V\d+", "V368", lines[1])), "between beat 2 and beat 3"),
                (self.planted(lines[0], re.sub(r"M\d+", "M700", lines[0])), "does not run down the left column"),
                (self.arrow_tip_at(int(x1) + TIP_GAP), "not %d px short of the card's edge" % TIP_GAP),
                (self.arrow_tip_at(int(x1) + TIP_GAP - 1), "not %d px short of the card's edge" % TIP_GAP),
                (self.arrow_tip_at(int(x1) + 8), "not %d px short of the card's edge" % TIP_GAP),
                (self.arrow_tip_at(int(x1) - 8), "not %d px short of the card's edge" % TIP_GAP),
                (self.planted(lines[2], "M%s 280H%s" % (x0, x1)), "does not run along beat 3's last line"),
                (self.planted(lines[2], "M%s 500H%s" % (x0, x1)), "off its straight edge"),
                (self.planted(lines[2], "M360 %sH%s" % (y0, x1)), "where beat 3's last word may still be"),
                (self.planted(lines[0], re.sub(r"V(\d+)", r"C80 210 80 230 64 \1", lines[0])), "one straight stroke"),
                (self.planted(arrow, arrow.replace("stroke-width:2px", "stroke-width:3px")), "stroked 3px wide"),
                (self.planted(arrow, arrow.replace("stroke-width:2px", "stroke-width:1px")), "stroked 1px wide"),
                (self.planted(arrow, arrow.replace(DIM, ACCENT)),
                 "arrow 1 is stroked %s, not %s" % (ACCENT, DIM)),
                (self.planted(".arrow.into{stroke:%s}" % ACCENT, ".arrow.into{}"), "arrow 3 is stroked %s" % DIM),
                (self.planted(arrow, arrow.replace("fill:none", "fill:%s" % DIM)), "is filled %s" % DIM),
                (self.planted(arrow, arrow.replace("linecap:round", "linecap:butt")), "with butt caps"),
                (self.planted(heads[0], heads[0] + "Z"), "head is not two strokes meeting at its line's end"),
                (self.planted(heads[0], re.sub(r"^M(\d+) (\d+)", lambda m: "M%d %d" % (int(m.group(1)) - 6,
                                                                                    int(m.group(2)) - 6), heads[0])),
                 "does not reach back evenly"),
                (self.planted(heads[2], re.sub(r"M(\d+)", lambda m: "M%d" % (int(m.group(1)) + 12), heads[2])),
                 "does not reach back evenly")):
            with self.subTest(expected=expected):
                self.assertCaught(arrow_problems(planted), expected)

    def test_each_arrow_draws_itself_on_with_the_one_easing_as_its_beat_or_the_card_lands(self):
        self.assertEqual(arrow_motion_problems(self.svg), [])
        head = re.search(r'<path class="head[^"]*"[^>]*/>', self.group_of(1)).group(0)
        line = re.search(r'<path class="line[^"]*"[^>]*/>', self.group_of(1)).group(0)
        dash = re.search(r"\.line\{[^}]*\}", self.svg).group(0)
        ride = re.search(r"translateY\(-\d+px\)", self.svg).group(0)
        for planted, expected in (
                (self.restarted(head, 9.0), "head does not start with its line"),
                (self.planted(line, re.sub(r' style="[^"]*"', "", line)), "does not draw on over"),
                (self.planted(line, line.replace("draw-", "down-")), "does not draw on over"),
                (self.planted(dash, dash[:-1] + ";stroke-dashoffset:.5}"), "offset, moved or faded in the base state"),
                (self.planted(head, head.replace(" d=", ' transform="translate(0 4)" d=')), "in the base state"),
                (self.planted(ride, "translateY(-24px)"), "head does not ride from its line's start"),
                (self.planted("translateX(-", "translateY(-"), "head does not ride from its line's start"),
                (self.planted("%{opacity:0;transform:translateY(-", "%{transform:translateY(-"),
                 "head does not ride from its line's start, hidden"),
                (self.arrow_at(1, 1.0), "arrow 1 draws before the block above it has landed"),
                (self.arrow_at(2, 4.6), "arrow 2 does not draw as beat 3 lands"),
                (self.arrow_at(3, 4.5), "arrow 3 does not draw as the card appears"),
                (self.arrow_at(3, 5.5), "arrow 3 is still drawing when a row is picked out")):
            with self.subTest(expected=expected):
                self.assertCaught(arrow_motion_problems(planted), expected)

    def test_every_arrow_is_whole_in_the_last_frame(self):
        self.assertEqual(demo_last_frame_problems(self.svg) + arrow_motion_problems(self.svg), [])
        for planted, expected in ((self.planted(".arrow{", ".arrow{opacity:0;"), "hidden outside the keyframes"),
                                  (self.planted(".line{", ".line{stroke-dashoffset:1;"), "in the base state")):
            with self.subTest(expected=expected):
                self.assertCaught(demo_last_frame_problems(planted) + arrow_motion_problems(planted), expected)

    def arrow_tip_at(self, x):
        """The SVG with the last arrow's line and chevron ending at `x`, the line's start where it was."""
        group = self.group_of(ARROWS)
        line = re.search(r' d="M(\d+) (\d+)H\d+"', group)
        x0, y = int(line.group(1)), int(line.group(2))
        moved = group.replace(line.group(0), ' d="M%d %dH%d"' % (x0, y, x))
        moved = re.sub(r' d="M[\d ]+L[\d ]+L[\d ]+"',
                       ' d="M%d %dL%d %dL%d %d"' % (x - 6, y - 6, x, y, x - 6, y + 6), moved)
        return self.planted(group, moved)

    def arrow_moved(self, y):
        """The SVG with the last arrow's line and chevron moved to the height `y`."""
        group = self.group_of(ARROWS)
        line = re.search(r' d="M(\d+) \d+H(\d+)"', group)
        x0, x1 = int(line.group(1)), int(line.group(2))
        moved = group.replace(line.group(0), ' d="M%d %dH%d"' % (x0, y, x1))
        moved = re.sub(r' d="M[\d ]+L[\d ]+L[\d ]+"',
                       ' d="M%d %dL%d %dL%d %d"' % (x1 - 6, y - 6, x1, y, x1 - 6, y + 6), moved)
        return self.planted(group, moved)

    def test_the_last_arrow_lands_on_the_card_and_the_card_answers_it(self):
        self.assertEqual(landing_problems(self.svg), [])
        rows = {text: int(float(element.get("y"))) for element, text, data, _ in text_elements(self.svg)
                if "row" in data}
        last_gap = re.findall(r'<g class="gap"[^>]*>.*?</g>', self.svg)[-1]
        middle = sorted(float(cy) for cy in re.findall(r'cy="([\d.]+)"', last_gap))[1]
        card = re.search(r"\.card\{[^}]*\}", self.svg).group(0)
        rect = re.search(r'<rect class="card a"[^>]*/>', self.svg).group(0)
        turn = re.search(r"(@keyframes lit-\d+\{0%,[\d.]+%\{)([^}]*)", self.svg)
        for planted, expected in (
                (self.arrow_moved(rows["interrupt policy"] - 8), "level with the row 'interrupt policy'"),
                (self.arrow_moved(rows["interrupt policy"] + 10), "level with the row 'interrupt policy'"),
                (self.arrow_moved(int(middle)), "level with a gap mark"),
                (self.planted(card, card.replace("stroke:%s" % ACCENT, "stroke:%s" % DIM)),
                 "the card's border ends in %s, not the accent" % DIM),
                (self.planted(rect, rect.replace("card a", "card")), "the card's border does not turn"),
                (self.planted(turn.group(0), turn.group(1) + "stroke:%s" % ACCENT), "the card's border does not turn"),
                (self.restarted(rect, 4.9), "not as the arrow's tip arrives"),
                (self.arrow_at(ARROWS, 5.2), "not as the arrow's tip arrives at 5.70 s")):
            with self.subTest(expected=expected):
                self.assertCaught(landing_problems(planted), expected)

    def test_each_line_s_dash_is_its_own_length_with_no_path_length(self):
        self.assertEqual(dash_problems(self.svg), [])
        line = re.search(r'<path class="line a"', self.svg).group(0)
        dash = re.search(r"\.line\{[^}]*\}", self.svg).group(0)
        reach = re.search(r"\.line\.reach\{[^}]*\}", self.svg).group(0)
        offset = re.search(r"(@keyframes reach-\d+\{0%,[\d.]+%\{stroke-dashoffset:)(\d+)", self.svg)
        # The scheme a renderer that ignores pathLength draws dotted: a unit path length, a 1 2 dash, an offset of 1.
        unit = re.sub(r'(<path class="line[^"]*")', r'\1 pathLength="1"', self.svg)
        unit = re.sub(r"stroke-dashoffset:\d+", "stroke-dashoffset:1", re.sub(r"stroke-dasharray:\d+",
                                                                             "stroke-dasharray:1 2", unit))
        for planted, expected in (
                (self.planted(line, line + ' pathLength="1"'), "a pathLength on a <path>"),
                (unit, "a pathLength on a <path>"),
                (unit, "arrow 1's dash is [1.0, 2.0], not its length"),
                (unit, "arrow 3's line does not start hidden"),
                (self.planted(reach, ""), "arrow 3's dash is"),
                (self.planted(dash, ".line{stroke-dasharray:4 4}"), "arrow 1's dash is [4.0, 4.0]"),
                (self.planted(dash, dash[:-1] + " 8}"), "arrow 2's dash is"),
                (self.planted(dash, ".line{}"), "arrow 1's dash is []"),
                (self.planted(offset.group(0), offset.group(1) + "104"), "arrow 3's line does not start hidden")):
            with self.subTest(expected=expected):
                self.assertCaught(dash_problems(planted), expected)

    def test_the_quote_sits_on_the_margin_the_gaps_read_and_the_card_is_280_wide_with_a_22_px_name(self):
        self.assertEqual(demo_frame_problems(self.svg), [])
        gap = re.search(r'<g class="gap"[^>]*>(.*?)</g>', self.svg).group(1)
        dots = re.findall(r"<circle [^>]*/>", gap)
        for planted, expected in (
                (self.planted('<text class="quote" x="%d"' % MARGIN, '<text class="quote" x="%d"' % (MARGIN - 8)),
                 "not on the %d px margin" % MARGIN),
                (self.planted(gap, gap.replace('r="2.5"', 'r="1.75"')), "a gap mark is not three dots"),
                (self.planted(gap, dots[0] + re.sub(r'cy="([\d.]+)"', lambda m: 'cy="%g"' % (float(m.group(1)) - 2),
                                                    dots[1]) + dots[2]), "a gap mark is not three dots"),
                (self.planted(gap, dots[0] + dots[1]), "a gap mark is not three dots"),
                (self.planted('width="%d"' % (CARD_WIDTH - 1), 'width="247"'), "not %d px wide" % CARD_WIDTH),
                (self.planted("font-size:%dpx" % FILE_PX, "font-size:20px"), "not %d px" % FILE_PX)):
            with self.subTest(expected=expected):
                self.assertCaught(demo_frame_problems(planted), expected)

    def test_the_caption_links_the_example_the_demo_shows(self):
        self.assertIsNotNone(self.example)
        self.assertTrue(os.path.isdir(self.example), self.example)

    def test_the_caption_says_the_prompt_is_real_and_a_model_answered_its_questions(self):
        self.assertEqual(caption_problems(self.readme), [])

    def test_a_caption_or_alt_text_that_drops_either_fact_is_caught(self):
        alt, caption = demo_caption(self.readme)
        for where, old, phrase, new in (
                ("alt text", alt, CAPTION[0], alt.replace(CAPTION[0], "a prompt the skill wrote", 1)),
                ("alt text", alt, CAPTION[1], alt.replace(CAPTION[1], "its questions answered", 1)),
                ("caption", caption, CAPTION[0], caption.replace(CAPTION[0], "a prompt the skill wrote", 1)),
                ("caption", caption, CAPTION[1], caption.replace(CAPTION[1], "its questions answered", 1))):
            with self.subTest(where=where, phrase=phrase):
                self.assertNotEqual(old, new)
                self.assertIn("the %s does not say %r" % (where, phrase),
                              caption_problems(self.readme.replace(old, new, 1)))

    def test_the_alt_text_lists_every_line_the_demo_shows(self):
        self.assertEqual(alt_problems(self.readme, self.svg), [])

    def test_an_alt_text_that_drifts_from_the_demo_is_caught(self):
        alt = demo_caption(self.readme)[0]
        for old, new in (("It asks what’s missing. ", ""), ("looks premium", "looks luxurious"),
                         ("The bar", "The checks"), ("master-prompt.md", "prompt.md")):
            with self.subTest(change=old):
                self.assertIn(old, alt)
                self.assertTrue(alt_problems(self.readme.replace(alt, alt.replace(old, new), 1), self.svg))


if __name__ == "__main__":
    unittest.main()
