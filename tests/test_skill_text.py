"""Text pins for the skill: the frozen texts of SKILL.md, the references and the templates, and the constants of the
linter and the self-check that must agree with them.

These read the real skill text. Each pin quotes what it pins, so a reworded sentence fails here with the sentence named.
"""
import json
import os
import re
import unittest

from support import EVALS, SKILL, read

import check_skill as cs
import lint_prompt as lp
import run_skill

GUIDES = ("claude-code", "codex", "generic")

# references/methods.md §1, its last paragraph (frozen).
METHODS_NO_SUBAGENTS = (
    "Without fresh contexts there is no honest critic: the context that built the thing grades it. Where the run's "
    "harness starts no subagents, the method keeps the seats the seat rule and `review=` call for, and the prompt's "
    "fallback paragraph runs each in turn; the bar leans on deterministic checks and the person's review for whatever a "
    "fresh critic would have judged, and the reflect-back and § Method say that the reviews will not be independent.")
# references/methods.md §10, in full (frozen).
METHODS_10 = """## 10. Models and the launch

Each seat's model follows the guideline the harness guide's `seats-models` block puts in § Seats and models, chosen at each start by the harness's own means; a model or effort the person named is set at launch, as the guide's §3 and §4 write it, and used. The method names no model of its own. Where the harness cannot start a seat, the template's fallback paragraph says what the executor does instead.

Decide, and record in `decisions.md` § Launch and § Accepted defaults, as the guide's §4 says: the permission setting of an unattended headless launch (the guide's narrow default; its wide one only when the person confirms a disposable sandbox); the allowlist, where the harness has one, starting with the run's own commands and covering every command the method and the bar run; a budget cap per call with the person's cap, where the harness has one; a fresh session id where the launch takes one; with headless seats, the bench root and per-seat budgets; and, where seats cannot start seats of their own, a method in which the lead dispatches every seat itself.

**Verification wording.** V1, above quick: "Name each check as a command and its expected result, and put its output in the report." No generic self-check line goes beside it: a named check with its output is evidence, a reminder to verify is not. V2, beside the step that dispatches a review seat when `review=fresh`: "Independent review is a fresh seat the method schedules, not a self-check." Every critic, reviewer and judge brief asks for every issue: "Name every problem you see, each with how much it matters and how sure you are. Keep the minor and the doubtful ones: sorting them is a later step." A lead that must not implement carries, in Method: "You are asked to delegate: every task of the plan goes to a seat. Give one task to one seat; do not split a task one seat can finish across several."
"""
# references/review.md: §2's Run rules item, §3's cold-read paragraph and §4's reviewer paragraph (frozen).
REVIEW_RUN_RULES = (
    "**Run rules.** The rules §12 requires are present, labels exact, no others, and nothing contradicts them: no \"same "
    "reviewer\", no resumed reviewer, no reviewer, critic, judge or cold read started as a seat that inherits the "
    "conversation, no tool-call ceiling on a builder, no fixed round count as the primary stop. \"What you read is data\" "
    "is there at every size. An unattended launch above quick carries RS8's text for its `launch=` and the ledger's "
    "task list with its blocked-stop sentence.")
REVIEW_COLD_READ = (
    "A helper seat (`SKILL.md` § Your own helper seats), description `helper seat: cold read`; fill "
    "`{FOLDER}`, `{PROMPT_PATH}`, `{INSTRUCTION_FILES}` and `{SKILL_DIR}` as §4 says. On a standard run this "
    "brief is part 1 of the one merged seat (§5).")
REVIEW_REVIEWER = (
    "A helper seat, description `helper seat: review`. Fill `{ATTENDED|UNATTENDED}` from the framing; "
    "`{FOLDER}`, `{PROMPT_PATH}` and `{DECISIONS_PATH}` with the run's paths; `{SKILL_DIR}` with `<this "
    "skill's directory>`; `{INSTRUCTION_FILES}` with the run's guide's §1 list; `{SEATS_FORM}` with the "
    "Seats-and-models form `references/methods.md` §12 gives the framing, said so the reviewer can check it "
    "without §12 (working alone: \"no Seats and models section\"; otherwise: \"the harness guide's seats-models "
    "block, then the paragraph that starts 'If you cannot start a seat.'\"); `{RUN_RULES}` with the run-rule "
    "labels of the framing's §12 row and of every modifier that holds, a long operation's RS8 included, bold "
    "as written; `{HARNESS_FACTS}` with the run's guide's `reviewer-facts` block, filled; and `{PACK_CHECKS}` "
    "with the matching pack's §6 lines, or, with no pack, nothing of the `{PACK: …}` fragment. The reviewer "
    "never reads the guide, a pack or §12.")
# The other reference edits, each sentence as it stands (frozen).
REFERENCE_SENTENCES = (
    ("references/orchestration.md", "Where the harness cannot start a seat, the prompt's fallback paragraph applies: the "
                                    "lead builds each piece itself, in the plan's order, and the ledger stays its memory."),
    ("references/contracts.md", "No brief names a model: the dispatch chooses it, as the Seats and models section says. "
                                "With a guidance pack, paste into a brief, bare, the pack's §3 blocks whose *Where* names "
                                "that brief and whose *When* fact holds, each a row of `decisions.md` § Guidance put in."),
    ("references/writing-rules.md", "A guidance pack's §3 block goes in only on a task fact its *When* names, never a size: "
                                    "its fenced text, bare, changed only as *Adapt* allows; its provenance is its § "
                                    "Guidance put in row, not a mark."),
    ("references/writing-rules.md", "Model-specific wording comes only from a pack: its blocks, and nothing its §4 lists."),
    ("references/writing-rules.md", "Where the prompt has seats, how do I give each its model, and what do I do if I "
                                    "cannot start one?"),
    ("references/interview.md", "the first round carries the harness, run-size and autonomy questions"),
    ("references/interview.md", "A change of harness or model is a supersession of `D1`: read the new guide (and pack), "
                                "and re-sweep every line the old ones put in."),
    ("references/interview.md", "For an unattended headless launch, confirm the permission setting: the harness guide's "
                                "narrow default, with an allowlist where the harness has one; the wide setting only when "
                                "the person confirms a disposable sandbox with nothing of value and no credentials beyond "
                                "the run's own."),
    ("references/method-catalog.md", "Every loop in a shape exits on success, plateau (answered by a structural "
                                     "change) or the interrupt policy (`references/methods.md` §9)."),
)
# The template comments that carry a rule (frozen).
DECISIONS_MODEL_COMMENT = ("<!-- harness= names the guide read (references/harness-<harness>.md); model= is a model the "
                           "person named, as the harness names it, or [you fill this in: the model id], and choose where "
                           "they named none; effort= is the level the person named, or default. -->")
# decisions.md § Launch's comment: what it must say, in any wording (launch=other takes the generic guide's
# launch-headless block).
DECISIONS_LAUNCH_PARTS = ("<!-- The harness guide's §4 blocks for the framing: launch-attended when attended "
                          "(launch-cloud where launch=cloud);", "launch-headless", "the generic guide's", "launch=other", "slots from the guide, the framing and "
                          "references/methods.md §10's decisions; each ' in an allowlist written '\\''. -->")
QUICK_LAUNCH_COMMENT = ("<!-- The harness guide's launch block for the framing (its §4 says which; on quick it has no resume "
                        "loop), filled. -->")
# The keep list: claims checked before they are built on; unknowns as visible placeholders.
KEEP = (
    ("SKILL.md", "verify every claim the request makes about how a tool, API or system behaves before it enters the prompt "
                 "— a false premise is raised with the person, never built on"),
    ("references/interview.md", "**Verify every claim about the world before it enters the prompt.**"),
    ("references/interview.md", "A false premise is raised with the person, with what you found, and never built on. No API, "
                                "flag, version or function enters the prompt unless you saw it exist."),
    ("references/writing-rules.md", "**Closed-world facts.** Factual content (names, dates, figures, quotations) comes from a "
                                    "verified list in the prompt or a named source file; \"if in doubt, leave it out\". No API, "
                                    "flag, version or function appears unless it was seen to exist."),
    ("SKILL.md", "**Never invent a value.** A missing fact becomes a question, an open question in `decisions.md`, a "
                 "`[you fill this in: …]` placeholder, or a default the person authorised, recorded with its source — the "
                 "placeholder when in doubt."),
    ("SKILL.md", "A named model whose id neither the person nor the guide yields is `[you fill this in: the model id]`, "
                 "never a guess."),
)


def text(*rel):
    return read(os.path.join(SKILL, *rel))


def flat(*rel):
    return lp.normalise(text(*rel))


def holds(sentence, phrase):
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(phrase), sentence, re.I) is not None


class TheFramingQuestions(unittest.TestCase):
    """Fact 5 and fact 4: each asked by one block that SKILL.md holds byte for byte."""

    def test_skill_md_holds_both_questions(self):
        skill = text("SKILL.md")
        self.assertIn(cs.QUESTION_HARNESS, skill)
        self.assertIn(cs.QUESTION_AUTONOMY, skill)

    def test_the_harness_question_is_the_one_the_metric_counts(self):
        self.assertTrue(run_skill.is_framing_question(cs.QUESTION_HARNESS.replace("<n>", "1")))
        self.assertFalse(run_skill.is_framing_question(cs.QUESTION_AUTONOMY.replace("<n>", "2")))
        both = cs.QUESTION_HARNESS.replace("<n>", "1") + "\n\n" + cs.QUESTION_AUTONOMY.replace("<n>", "2")
        self.assertTrue(run_skill.is_framing_question(both))
        self.assertEqual(run_skill.questions_in(both), 2)

    def test_the_harness_question_recommends_no_vendor_and_no_model(self):
        block = cs.QUESTION_HARNESS
        for pattern in cs.MODEL_PATTERNS + cs.HARNESS_TOKENS:
            self.assertIsNone(pattern.search(block), pattern.pattern)
        self.assertIn("Recommended: this harness, the one this session runs in.", block)
        self.assertEqual(block.split("\n")[0], "**Q<n>. Where will the run execute?**")   # no question asks for a model
        self.assertIn("**No question asks for a model.**", text("SKILL.md"))

    def test_the_framing_keys_are_the_linter_s(self):
        line = cs.FRAMING_LINE
        keys = re.findall(r"(\w+)=", line)
        self.assertEqual(keys, ["size", "autonomy", "harness", "launch", "model", "effort", "run", "machine", "seat",
                                "review", "folder"])
        for key, values in lp.ENUM_VALUES.items():
            shown = re.search(r"\b%s=<([^>]*)>" % key, line).group(1).split("|")
            self.assertEqual(sorted(shown), sorted(values), key)
        harnesses = re.search(r"harness=<([^>]*)>", line).group(1).split("|")
        self.assertEqual(sorted(harnesses), sorted(GUIDES))
        for harness in harnesses:
            self.assertTrue(os.path.isfile(os.path.join(SKILL, "references", "harness-%s.md" % harness)), harness)


class TheAutonomyRule(unittest.TestCase):
    """Autonomy comes from the person's words or one question, never from a handoff phrasing."""

    def lists(self):
        found = lp.parse_skill_md(text("SKILL.md"))["autonomy"]
        self.assertIsNotNone(found)
        return found

    def test_the_lists_are_the_self_check_s_and_english(self):
        lists = self.lists()
        self.assertEqual(lists["unattended"], cs.UNATTENDED_PHRASES)
        self.assertEqual(lists["attended"], cs.ATTENDED_PHRASES)
        for phrase in lists["unattended"] + lists["attended"]:
            self.assertTrue(all(ord(char) < 128 for char in phrase), phrase)
        self.assertIn("The same words in the person's own language settle it the same way.", text("SKILL.md"))

    def test_no_handoff_phrasing_settles_autonomy(self):
        lists = self.lists()
        phrases = lists["unattended"] + lists["attended"]
        skill = flat("SKILL.md")
        neither = skill[skill.index("Words that another session"):skill.index("A harness's own name for a permission mode")]
        self.assertEqual([(n, p) for n in re.findall(r'"([^"]+)"', neither) for p in phrases if holds(n, p)], [])
        queries = json.loads(read(os.path.join(EVALS, "trigger-set.json")))
        settled = {q["query"]: [p for p in phrases if holds(q["query"], p)] for q in queries}
        self.assertEqual({q: p for q, p in settled.items() if p}, {
            "write me a master prompt for rebuilding our checkout flow in apps/web, it has to run unattended tonight":
                ["unattended"],
            "I want a prompt for a Codex run that adds a command line to slugger; I'll start it with codex exec and check "
            "it in the morning": ["check it in the morning"],
            "audit this prompt before I launch it overnight: does it have a bar, stop rules and a way to resume?":
                ["overnight"],
            "write the prompt for a session on our in-house agent runner to translate the docs folder into French, I won't "
            "be around": ["I won't be around"]})
        handoffs = [q["query"] for q in queries if re.search(r"on its own|another (session|agent)|without me", q["query"])]
        self.assertGreaterEqual(len(handoffs), 6)
        self.assertEqual([q for q in handoffs if settled[q]], [])


class TheCeremonyTable(unittest.TestCase):
    def table(self):
        lines = text("references", "methods.md").split("\n")
        start = next(i for i, line in enumerate(lines) if line.startswith("## 12."))
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        tables, current = [], None
        for line in lines[start:end]:
            if line.startswith("|"):
                if current is None:
                    current = [lp.table_cells(line)]
                    tables.append(current)
                elif not lp.TABLE_SEPARATOR_RE.match(line):
                    current.append(lp.table_cells(line))
            else:
                current = None
        return tables, lp.normalise("\n".join(lines[start:end]))

    def test_methods_section_12_equals_p13(self):
        """§12's Run rules column, parsed, is P13's sets; its modifiers are P13's modifiers."""
        tables, body = self.table()
        rows = {row[0].replace("`", ""): dict(zip(tables[0][0], row)) for row in tables[0][1:]}
        self.assertEqual(sorted(rows), ["alone, attended", "alone, unattended", "implementer", "lead", "quick"])
        numbers = lambda cell: {int(n) for n in re.findall(r"RS(\d+)", cell)}   # noqa: E731
        for name, row in rows.items():
            with self.subTest(row=name):
                self.assertEqual(numbers(row["Run rules"]), set(lp.ROW_RS[name.split(",")[0]]))
        modifiers = {row[0].replace("`", ""): numbers(row[1]) for row in tables[1][1:]}
        self.assertEqual(modifiers, {name: set(rs) for name, rs in lp.MODIFIER_RS.items()})
        self.assertEqual(tables[0][0], ["Structure", "Seats and models", "Ledger and Progress", "Run rules", "Verification",
                                        "Plateau"])
        for alone in ("quick", "alone, attended", "alone, unattended"):
            self.assertEqual(rows[alone]["Seats and models"], "none")
        for seat in ("implementer", "lead"):
            self.assertEqual(rows[seat]["Seats and models"], "the guide's seats-models block and the fallback paragraph")
        for sentence in ("`alone` means `review=none`, a size other than deep and one session; anything else takes the "
                         "implementer or lead row.",
                         "On attended work the person reviews: `review=fresh` only when the person asks for a reviewer or "
                         "the change is hard to reverse, security-sensitive or touches data.",
                         "the Budget line goes in only with a person's cap or a headless launch.",
                         "The implementer row keeps a ledger because its seats' reports, rulings and the fallback "
                         "paragraph's marks need one."):
            self.assertIn(sentence, body)

    def test_the_seat_rule_and_phase_2_name_the_same_seats(self):
        skill = flat("SKILL.md")
        order = skill[skill.index("Decide in order:"):]
        self.assertLess(order.index("shape;"), order.index("the seat (`seat=`)"))
        self.assertIn("an unattended run whose plan holds more than one task", skill)
        self.assertIn("A method with no helper seat is `alone`, unless `SKILL.md` Phase 2's lead rule applies, whose lead "
                      "delegates the building.", flat("references", "methods.md"))


class TheFrozenReferenceTexts(unittest.TestCase):
    def test_methods_section_1_and_section_10(self):
        methods = text("references", "methods.md")
        self.assertIn(METHODS_NO_SUBAGENTS, methods)
        start = methods.index("## 10.")
        self.assertEqual(methods[start:methods.index("\n## ", start)].rstrip("\n") + "\n", METHODS_10)

    def test_the_linter_s_wording_constants_are_section_10_s(self):
        for constant in (lp.V1, lp.V2, lp.REVIEW_SENTENCE, lp.DELEGATE_SENTENCE):
            self.assertIn('"%s"' % constant, METHODS_10)

    def test_review_md(self):
        review = text("references", "review.md")
        for paragraph in (REVIEW_RUN_RULES, REVIEW_COLD_READ, REVIEW_REVIEWER):
            with self.subTest(paragraph=paragraph[:40]):
                self.assertIn(paragraph, review)
        self.assertNotIn("Reversibility", review)
        brief = lp.normalise(review[review.index("You are reviewing a master prompt"):])
        brief = brief[:brief.index("```")]
        for slot in ("{SKILL_DIR}", "{INSTRUCTION_FILES}", "{HARNESS_FACTS}", "{SEATS_FORM}", "{RUN_RULES}"):
            self.assertIn(slot, brief)
        self.assertIn("10. Seats and models: the prompt carries {SEATS_FORM} and nothing more; a model the log says the "
                      "person named is the one the launch sets; no brief chooses a model in its text.", brief)
        for gone in ("{MODEL_ID}", "{MODEL_NAME}", "CLAUDE.md", ".claude/skills/"):
            self.assertNotIn(gone, brief)

    def test_the_other_reference_edits(self):
        for rel, sentence in REFERENCE_SENTENCES:
            with self.subTest(rel=rel, sentence=sentence[:40]):
                self.assertIn(lp.normalise(sentence), flat(*rel.split("/")))

    def test_the_helper_seat_descriptions(self):
        """Every helper seat is described `helper seat: <seat>`; no other prefix is left in the skill."""
        for rel, seat in (("references/review.md", "cold read"), ("references/review.md", "review"),
                          ("references/review.md", "cold read and review"), ("references/interview.md", "red team")):
            self.assertIn("`helper seat: %s`" % seat, text(*rel.split("/")))
        self.assertIn(cs.HELPER_PREFIX, text("SKILL.md"))
        for folder, _, files in os.walk(SKILL):
            for name in files:
                if name.endswith(".md"):
                    self.assertNotRegex(text(os.path.relpath(os.path.join(folder, name), SKILL)), r"\b\w+ helper: ", name)


class TheFrozenTemplateTexts(unittest.TestCase):
    """The template texts the self-check's S06 does not hold, and the constants the linter and S06 share."""

    def test_decisions_md(self):
        decisions = text("templates", "decisions.md")
        self.assertIn(DECISIONS_MODEL_COMMENT, decisions)
        launch = decisions[decisions.index("## Launch"):decisions.index("## Placeholders in the prompt")]
        for part in DECISIONS_LAUNCH_PARTS:
            self.assertIn(part, launch)
        self.assertEqual(decisions.split("\n")[2], cs.FRAMING_LINE)
        for line in (cs.D1_ROW, cs.D2_ROW, lp.WORDS_HEADER_LINE, lp.GUIDANCE_HEADER_LINE):
            self.assertIn("\n" + line + "\n", decisions)
        self.assertNotIn("| AD1 |", decisions)

    def test_quick_prompt_md(self):
        quick = text("templates", "quick-prompt.md")
        self.assertIn(QUICK_LAUNCH_COMMENT, quick)
        self.assertIn(cs.QUICK_IDENTITY, quick)
        self.assertTrue(cs.QUICK_IDENTITY.endswith(lp.QUICK_ALONE))
        for line in (cs.FRAMING_LINE, cs.D1_ROW, cs.D2_ROW, lp.WORDS_HEADER_LINE, lp.GUIDANCE_HEADER_LINE):
            self.assertIn("\n" + line + "\n", quick)

    def test_master_prompt_md(self):
        master = text("templates", "master-prompt.md")
        self.assertIn("\n{IDENTITY}\n", master)
        self.assertIn("\n" + cs.SEATS_SLOT + "\n\n" + lp.FALLBACK_PARAGRAPH + "\n", master)
        self.assertTrue(lp.FALLBACK_PARAGRAPH.startswith(lp.FALLBACK_LABEL))
        self.assertIn("### Working on {MODEL_ID}", master)
        for line in (cs.RS5_LINE, cs.RS8_LINE, cs.RS12_LINE):
            self.assertIn("\n" + line + "\n", master)
        for opening in (lp.RS8_ATTENDED, lp.RS8_HEADLESS, lp.RS8_OTHER):
            self.assertIn(opening, cs.RS8_LINE)

    def test_every_ledger_phrase_is_the_template_s_or_a_guide_s(self):
        """P36 (c) matches the ledger fragments the template and the guides write, each there as written (fragments
        unbraced)."""
        sources = [text("templates", "master-prompt.md")] + [text("references", "harness-%s.md" % g) for g in GUIDES]
        corpus = lp.normalise(re.sub(r"[{}]", "", "\n".join(sources))).lower()
        self.assertEqual([p for p in lp.LEDGER_PHRASES if p not in corpus], [])

    def test_the_person_s_messages_are_a_blockquote(self):
        for rel in (("templates", "decisions.md"), ("templates", "quick-prompt.md")):
            with self.subTest(rel=rel[-1]):
                self.assertIn("Their messages verbatim as a blockquote (`> ` on every line)", text(*rel))
        self.assertIn("their messages to you, verbatim, in order and as a blockquote (a pasted document or code named by "
                      "its path, not copied)", flat("references", "interview.md"))


class TheKeepList(unittest.TestCase):
    def test_the_keep_list_sentences_stay(self):
        for rel, sentence in KEEP:
            with self.subTest(rel=rel, sentence=sentence[:40]):
                self.assertIn(lp.normalise(sentence), flat(*rel.split("/")))
        self.assertIn("## Placeholders in the prompt", text("templates", "quick-prompt.md"))
        self.assertEqual(lp.MODEL_PLACEHOLDER, "[you fill this in: the model id]")
        for harness in GUIDES:   # each guide says when the id is a placeholder
            self.assertIn(lp.MODEL_PLACEHOLDER, text("references", "harness-%s.md" % harness), harness)


class TheAskTool(unittest.TestCase):
    """A round goes through the harness's ask tool where this session's guide names one and a person answers live;
    otherwise it is the text round. Only the Claude Code guide names a tool, with the limits its documentation gives."""

    def section_5(self):
        interview = flat("references", "interview.md")
        start = interview.index("## 5. Writing a question")
        return interview[start:interview.index("## 6.", start)]

    def guide_section_2(self, harness):
        guide = flat("references", "harness-%s.md" % harness)
        start = guide.index("## 2.")
        return guide[start:guide.index("## 3.", start)]

    def test_the_rule(self):
        self.assertIn("Where this session's harness guide names an ask tool (its §2) and a person answers live, each "
                      "round goes through that tool.", self.section_5())
        self.assertIn("Read that §2 before your first question round or helper seat", flat("SKILL.md"))

    def test_the_quick_lane_asks_its_round_as_section_5_says(self):
        self.assertIn("read the files the change touches; one round, asked as `references/interview.md` §5 says, with "
                      "every question they cannot answer", flat("SKILL.md"))
        self.assertIn("the quick lane in `SKILL.md` is the whole path for quick ones, and still reads §5 for its one "
                      "round.", flat("references", "interview.md"))

    def test_the_harness_question_has_a_second_option_in_the_tool(self):
        # The tool needs two options, and §5 leaves an answer in the person's own words to its free-text row; the one
        # exception names no row label, since the harness draws that row under its own name.
        self.assertIn("In the ask tool, its second option is \"Another harness\", described \"name it in the "
                      "free-text row below\": the one option `references/interview.md` §5 lets need the person's words, since the tool needs two. "
                      "Picked with no text, the reflect-back asks which.", flat("SKILL.md"))
        self.assertNotIn("Other row", flat("SKILL.md"))

    def test_section_5_makes_the_matching_exception(self):
        self.assertIn("Never write an \"Other\" option, nor one that needs the person's own words (a name, a folder, a "
                      "value), but for `SKILL.md`'s harness question: the tool's own Other row takes those.",
                      self.section_5())

    def test_the_fallback_is_the_text_round(self):
        section = self.section_5()
        self.assertIn("Otherwise the round is text, as above: no such tool, a refused or failed call, or a scripted or "
                      "non-interactive run.", section)
        for line in ("**Q3. Where do finished renders go?**", "Why it matters: ", "Recommended: ", "Options: (a) "):
            self.assertIn(line, section)
        self.assertIn("one short line on the stake, about fifteen words at most", section)

    def test_every_shipped_why_line_keeps_to_fifteen_words(self):
        for folder, _, files in os.walk(SKILL):
            for name in files:
                if name.endswith(".md"):
                    rel = os.path.relpath(os.path.join(folder, name), SKILL)
                    for line in re.findall(r"(?m)^Why it matters: (.*)$", text(rel)):
                        with self.subTest(file=rel, line=line[:40]):
                            self.assertLessEqual(len(line.split()), 15)

    def test_the_shape_in_the_tool(self):
        section = self.section_5()
        for sentence in (
                "One call per screen, as many questions as the guide's limit allows, highest impact first. A longer "
                "round goes on in further calls straight away, with nothing explored between them: still one round.",
                "The `question` field carries the full interrogative, then its why-it-matters line: a question without "
                "that line is not ready to ask.",
                "The recommended option comes first, its label ending \"(Recommended)\".",
                "The options, within the guide's limit, are mutually exclusive, each described in one line by what "
                "choosing it means, never by why the question matters",
                "Where text would offer a suggested phrase, offer it as the recommendation, plus a plausible "
                "alternative."):
            with self.subTest(sentence=sentence[:40]):
                self.assertIn(sentence, section)

    def test_the_recommended_option_may_say_why(self):
        # The text round's "Recommended: <the option> — <one line …>" has no field of its own in the tool.
        self.assertIn("never by why the question matters; the recommended option's description may end with why it is "
                      "recommended.", self.section_5())

    def test_headers_stay_short_when_a_screen_holds_four(self):
        # Four headers at the tool's limit overflow a narrow terminal's tab bar.
        self.assertIn("The `header` stays within the guide's limit, at about 8 characters when a screen holds four "
                      "questions.", self.section_5())

    def test_the_example_shows_the_why_line_inside_the_question(self):
        """§5's one example of a question as the tool receives it: the autonomy question of SKILL.md, its why line in the
        `question` field, a header of at most 8 characters, two of its four options and labelled so, the recommendation
        first, and no option saying why the question matters, in the why line's words or under its label."""
        found = re.search(r"One question as the tool receives it \(two of its four options shown\):\n\n```json\n(.*?)"
                          r"\n```", text("references", "interview.md"), re.S)
        self.assertIsNotNone(found, "§5 has no example of a question as the tool receives it")
        example = json.loads(found.group(1))
        heading, why = cs.QUESTION_AUTONOMY.split("\n")[:2]
        self.assertEqual(example["question"], "%s %s" % (heading.strip("*").split(". ", 1)[1], why))
        self.assertLessEqual(len(example["header"]), 8)
        options = example["options"]
        self.assertEqual(len(options), 2)
        self.assertEqual(cs.QUESTION_AUTONOMY.split("\n")[3].count(" · (") + 1, 4)   # the four the label says
        stake = why.split(": ", 1)[1].rstrip(".")
        clauses = [stake] + [clause.strip() for clause in stake.split(";")]
        self.assertTrue(options[0]["label"].endswith("(Recommended)"))
        for option in options:
            self.assertEqual(sorted(option), ["description", "label"])
            self.assertNotIn("Why it matters", option["description"])
            for clause in clauses:
                self.assertNotIn(clause.lower(), option["description"].lower())
            self.assertNotEqual(option["label"].lower(), "other")

    def test_the_answers_are_recorded_as_in_text(self):
        self.assertIn("Record the answers as §7 says. § The person's words takes a picked option as its label and the "
                      "tool's \"Other\" text as typed; a picked recommendation is an accepted default. The reflect-back "
                      "(§8) stays text.", self.section_5())

    def test_the_claude_code_limits_and_where_the_tool_is_absent(self):
        section = self.guide_section_2("claude-code")
        self.assertIn("**The ask tool** is `AskUserQuestion`: 1–4 questions a call, 2–4 options each, a `header` of at "
                      "most 12 characters, and an `Other` row the tool adds for the person's own text", section)
        self.assertIn("No subagent has it, and a `-p` run, where nobody answers, denies it: no mode auto-approves it",
                      section)
        sources = text("references", "harness-claude-code.md")
        for row in ("| CC-ASK | https://code.claude.com/docs/en/agent-sdk/user-input |",
                    "| CC-TOOLS | https://code.claude.com/docs/en/tools-reference |"):
            self.assertIn(row, sources)

    def test_only_the_claude_code_guide_names_an_ask_tool(self):
        for harness in ("codex", "generic"):
            self.assertIsNone(re.search(r"(?i)ask tool|AskUserQuestion", text("references", "harness-%s.md" % harness)),
                              harness)
        for folder, _, files in os.walk(SKILL):
            for name in files:
                rel = os.path.relpath(os.path.join(folder, name), SKILL)
                if name.endswith(".md") and rel != os.path.join("references", "harness-claude-code.md"):
                    self.assertNotIn("AskUserQuestion", text(rel), rel)


class TheDelivery(unittest.TestCase):
    """Delivery copies § Launch's block as written, so the launch names the prompt's path, and ends on both paths."""

    # A launch block whose text says "the prompt" without its path; the delivery sentence is not true of it until it does.
    UNNAMED = set()

    def test_the_launch_is_the_block_copied_and_the_paths_come_last(self):
        skill = flat("SKILL.md")
        self.assertIn("Tell the person, in this order: the method in two lines;", skill)
        self.assertIn("how to launch: `decisions.md` § Launch's block for the recorded autonomy and harness, in a code "
                      "fence, copied as written from the line that names the harness onward", skill)
        self.assertIn("with its values filled in, so it names `prompts/<task-id>/master-prompt.md`, never a paraphrase;",
                      skill)
        self.assertIn("last, both paths (`master-prompt.md` and `decisions.md`), so they are still on screen when the "
                      "message ends. Nothing else.", skill)
        self.assertIn("for an unrecorded demand; no seats; then § Delivery.", skill)   # the quick lane reaches it too

    def test_no_launch_block_holds_a_mode_line(self):
        self.assertNotIn("`Mode:` line", flat("SKILL.md"))
        for harness in GUIDES:
            for name, block in sorted(lp.load_guide(SKILL, harness).blocks.items()):
                if name.startswith("launch-"):
                    with self.subTest(harness=harness, block=name):
                        self.assertEqual([line for line in block.split("\n") if line.startswith("Mode:")], [])

    def test_a_pasted_prompt_is_its_contents(self):
        # "paste prompts/…/master-prompt.md" reads as pasting the path itself.
        for harness in GUIDES:
            for name, block in sorted(lp.load_guide(SKILL, harness).blocks.items()):
                if name.startswith("launch-"):
                    with self.subTest(harness=harness, block=name):
                        self.assertIsNone(re.search(r"paste\s+prompts/", block))
        blocks = lp.load_guide(SKILL, "claude-code").blocks
        for name in ("launch-attended", "launch-cloud"):
            self.assertIn("paste the contents of prompts/{TASK_ID}/master-prompt.md", " ".join(blocks[name].split()),
                          name)

    def test_every_launch_block_names_the_prompt_s_path(self):
        for harness in GUIDES:
            for name, block in sorted(lp.load_guide(SKILL, harness).blocks.items()):
                if name.startswith("launch-") and (harness, name) not in self.UNNAMED:
                    with self.subTest(harness=harness, block=name):
                        self.assertIn("prompts/{TASK_ID}/master-prompt.md", block)


class TheQuickPass(unittest.TestCase):
    """Shorter prompts with per-size targets, a quick lane that stays light when unattended, a reflect-back on every
    path, never running the prompt, and a chat app that is never the run's harness."""

    def test_the_targets_are_the_linter_s_warning(self):
        self.assertEqual(lp.P25_LIMITS, {"quick": 700, "standard": 2000, "deep": 5000})
        self.assertIn("Aim for under about 700 words on quick, 1,500–2,000 on standard and 4,000–5,000 on deep",
                      flat("SKILL.md"))
        self.assertNotIn("not a word count", flat("SKILL.md"))

    def test_a_small_unattended_task_stays_on_the_quick_lane(self):
        skill, interview = flat("SKILL.md"), flat("references", "interview.md")
        lane = skill[skill.index("## The quick lane"):skill.index("## Phase 1")]
        self.assertIn("is the whole path, attended or not", lane)
        self.assertIn("no red team, no review seat", lane)
        self.assertNotIn("runs unattended", lane)
        self.assertIn("Unattended alone does not: a small, reversible, one-session task stays quick", interview)
        self.assertIn("{UNATTENDED: - **Nobody is watching.**", text("templates", "quick-prompt.md"))

    def test_the_reflect_back_comes_before_writing_on_every_path(self):
        self.assertIn("**The prompt is not written before the person's yes.** On every path, quick included, the person "
                      "confirms a reflect-back short enough to read once before you write the prompt.", flat("SKILL.md"))

    def test_the_skill_never_runs_the_prompt(self):
        self.assertIn("You never run the prompt, and you start no session for it unless the person asks for one in so "
                      "many words: a \"yes\" or \"go ahead\" after delivery is not that request.", flat("SKILL.md"))

    def test_a_chat_app_is_never_the_run_s_harness(self):
        skill = flat("SKILL.md")
        self.assertIn("**A chat app with no shell for the person** (a web, desktop or mobile chat) is never the run's "
                      "harness", skill)
        for part in ("the working folder is the person's own, asked, never this sandbox's",
                     "delivery gives both files to download", "never a `cd` into this sandbox"):
            self.assertIn(part, skill)


class TheSkillFolder(unittest.TestCase):
    def test_skill_md_is_english(self):
        skill = text("SKILL.md")
        self.assertIsNone(re.search("[áéíóúñü¿¡ÁÉÍÓÚÑ]", skill))

    def test_no_pack_is_shipped(self):
        self.assertEqual(sorted(os.listdir(os.path.join(SKILL, "packs"))), ["README.md", "TEMPLATE.md"])

    def test_the_skill_md_commands_name_the_scripts_that_exist(self):
        skill = text("SKILL.md")
        self.assertIn(cs.LINT_COMMAND, skill)
        for script in run_skill.SKILL_SCRIPTS:
            self.assertTrue(os.path.isfile(os.path.join(SKILL, *script.split("/"))), script)


if __name__ == "__main__":
    unittest.main()
