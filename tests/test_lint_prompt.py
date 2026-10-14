"""Tests for scripts/lint_prompt.py, the master-prompt linter.

The fixtures under fixtures/prompts/ (a prompt holds no comment, so they are described here); "named" means the
person named example-model-1, "choose" that they named no model:
- good-quick: the quick lane's one screen (claude-code, attended, working alone, the harness's default effort; named).
- good-standard: an implementer with a fresh reviewer (claude-code, attended, interactive; named). It carries one block
  of fixtures/packs/sample-pack.md bare, with its decisions.md row.
- good-alone: an executor that works alone, unattended, launched headless (claude-code, high effort; choose).
- good-lead: a lead that delegates, unattended, in a cloud session, on a disposable machine (claude-code; choose).
- good-codex: an implementer with an explorer seat, unattended, launched headless (codex, high effort; named).
- good-generic: an implementer with an explorer seat, attended, on a harness with no guide of its own (choose).
- causes/c1 ... c6: each one edit of a good fixture, erring on exactly the rule its cause breaks.
"""
import json
import os
import re
import shutil
import tempfile
import unittest

import support
from support import PACKS, PROMPTS, SKILL, read, run_py, write

import check_skill
import lint_prompt as lp

LINTER = support.LINTER
MODEL, OTHER = "example-model-1", "example-model-2"
GOOD = ("good-quick", "good-standard", "good-alone", "good-lead", "good-codex", "good-generic")
FIX = {}
for _name in GOOD:
    _decisions = read(os.path.join(PROMPTS, _name + ".decisions.md"))
    FIX[_name] = (read(os.path.join(PROMPTS, _name + ".md")), _decisions, lp.parse_framing(_decisions)[0])
STANDARD, STANDARD_DECISIONS, STANDARD_FRAMING = FIX["good-standard"]
QUICK, QUICK_DECISIONS, QUICK_FRAMING = FIX["good-quick"]
ALONE, ALONE_DECISIONS, ALONE_FRAMING = FIX["good-alone"]
LEAD, LEAD_DECISIONS, LEAD_FRAMING = FIX["good-lead"]
CODEX, CODEX_DECISIONS, CODEX_FRAMING = FIX["good-codex"]
GENERIC, GENERIC_DECISIONS, GENERIC_FRAMING = FIX["good-generic"]
GUIDES = {h: lp.load_guide(SKILL, h) for h in ("claude-code", "codex", "generic")}
PACK = lp.load_packs(PACKS)[0]
BLOCKS = {block.name: block for block in PACK.blocks}


def fill_block(harness, block_id, framing, values, optional=()):
    """A guide block as the skill fills it: fragments by the framing, `{ text}` kept when listed, slots by `values`."""
    text = lp.expand_fragments(GUIDES[harness].blocks[block_id], framing)[0]
    text = re.sub(r"(?<!\$)\{( [^{}\n]*)\}", lambda m: m.group(1) if m.group(1) in optional else "", text)
    return re.sub(r"(?<!\$)\{([A-Z][A-Z0-9_]*)\}", lambda m: values[m.group(1)], text)


def lint(text, framing=None, decisions=None, packs=PACKS, **override):
    framing = dict(STANDARD_FRAMING if framing is None else framing)
    framing.update(override)
    framing = {k: v for k, v in framing.items() if v is not None}
    return lp.lint_text(text, framing, decisions, SKILL, packs)


def put(text, section, line):
    """Insert a paragraph at the start of `## <section>` ('identity' appends to the identity paragraph)."""
    lines = text.split("\n")
    if section == "identity":
        at = next(i for i, raw in enumerate(lines) if raw.strip() and not raw.startswith("#"))
        lines[at] = lines[at] + " " + line
        return "\n".join(lines)
    at = next(i for i, raw in enumerate(lines) if re.match(r"^##\s+%s\s*$" % re.escape(section), raw))
    return "\n".join(lines[:at + 1] + ["", line] + lines[at + 1:])


def quick_unattended(text=QUICK):
    """A quick prompt as an unattended run's: the quick template's unattended line after its interrupt policy."""
    policy = next(raw for raw in text.split("\n") if raw.startswith("- **Stop and ask only for:**"))
    return text.replace(policy, policy + "\n" + lp.QUICK_UNATTENDED_LINE)


def of(findings, rule, level=None):
    return [f for f in findings if f.rule == rule and (level is None or f.level == level)]


def errors(findings):
    return [f for f in findings if f.level == "ERROR"]


def shown(findings):
    return [f.as_text() for f in findings if f.level != "ALLOWED"]


def branch(finding):
    """The branch letter a finding's message names: '(a)' ... '(g)'."""
    found = re.search(r"\(([a-g])\)", finding.message)
    return "(%s)" % found.group(1) if found else None


def add_row(decisions, header, row):
    """decisions.md with `row` added as the last row of the table whose header row is `header`."""
    lines = decisions.split("\n")
    at = lines.index(header) + 2
    while at < len(lines) and lines[at].startswith("|"):
        at += 1
    return "\n".join(lines[:at] + [row] + lines[at:])


class GoodPrompts(unittest.TestCase):
    def check_clean(self, name):
        text, decisions, framing = FIX[name]
        self.assertEqual(shown(lint(text, framing, decisions)), [])

    def test_good_quick_has_no_finding(self):
        self.check_clean("good-quick")

    def test_good_standard_has_no_finding(self):
        self.check_clean("good-standard")

    def test_good_alone_has_no_finding(self):
        self.check_clean("good-alone")

    def test_good_lead_has_no_finding(self):
        self.check_clean("good-lead")

    def test_good_codex_has_no_finding(self):
        self.check_clean("good-codex")

    def test_good_generic_has_no_finding(self):
        self.check_clean("good-generic")

    def test_every_good_prompt_lints_clean_through_the_command(self):
        """The skill ships no pack, so the command reads none; each fixture exits 0 with nothing to say."""
        for name in GOOD:
            with self.subTest(fixture=name):
                path = os.path.join(PROMPTS, name)
                proc = run_py(LINTER, [path + ".md", "--decisions", path + ".decisions.md"])
                self.assertEqual((proc.returncode, proc.stdout.strip()), (0, "errors: 0, warnings: 0, allowed: 0"),
                                 proc.stdout + proc.stderr)

    def test_the_fixtures_cover_each_harness_seat_and_launch(self):
        framings = [FIX[name][2] for name in GOOD]
        self.assertEqual({f["harness"] for f in framings}, {"claude-code", "codex", "generic"})
        self.assertEqual({f["seat"] for f in framings}, {"alone", "implementer", "lead"})
        self.assertEqual({f["launch"] for f in framings}, {"interactive", "headless", "cloud"})
        self.assertEqual({f["effort"] for f in framings}, {"default", "high"})
        self.assertEqual({f["model"] for f in framings}, {MODEL, lp.MODEL_CHOOSE})

    def test_good_standard_carries_a_pack_block_bare_with_its_row(self):
        self.assertNotIn("<!--", STANDARD)
        self.assertIn(BLOCKS["Scope discipline"].text, STANDARD)
        document = lp.lint_document(STANDARD, STANDARD_FRAMING, STANDARD_DECISIONS, SKILL, PACKS)
        self.assertEqual(document.published_words, len(BLOCKS["Scope discipline"].text.split()))
        self.assertIn("| Scope discipline [SP #scope] | sample-pack.md | D4: the run changes code |", STANDARD_DECISIONS)
        self.assertEqual(lp.lint_document(STANDARD, STANDARD_FRAMING, STANDARD_DECISIONS, SKILL, []).published_words, 0)

    def test_product_words_in_content_sections_give_no_error(self):
        text = put(STANDARD, "Required product",
                   "The service calls a hosted model for summaries, ships a TODO app with a TBD label on drafts, draws a "
                   "skill tree for each player, and shows a double-check dialog before deleting; the pricing page lists a "
                   "model tier per plan.")
        self.assertEqual(errors(lint(text)), [])


class Zones(unittest.TestCase):
    LINE = "Fill the TBD fields as discussed."

    def test_same_line_is_error_in_instruction_and_warn_in_content(self):
        instruction = lint(put(STANDARD, "Method", self.LINE))
        content = lint(put(STANDARD, "Context", self.LINE))
        self.assertEqual({f.rule for f in errors(instruction)}, {"P06", "P12"})
        self.assertEqual(errors(content), [])
        self.assertEqual({f.rule for f in content if f.level == "WARN"}, {"P06", "P12"})

    def test_literal_spans_are_exempt_in_content_and_not_in_instruction(self):
        content = lint(put(STANDARD, "Context", "The old brief said `the model named in every dispatch`."))
        self.assertEqual(of(content, "P05"), [])
        instruction = lint(put(STANDARD, "Method", "Keep `the model named in every dispatch` out of the briefs."))
        self.assertEqual([f.level for f in of(instruction, "P05")], ["WARN"])

    def test_blockquote_is_a_literal_span(self):
        found = lint(put(STANDARD, "Context", "> Make it robust, the old README said."))
        self.assertFalse(of(found, "P24"))

    def test_pack_text_is_exempt_from_content_rules(self):
        """A pack block found in the prompt is the pack's text, which no content rule judges; the same words outside
        it are found."""
        pack = lp.Pack("robust-pack.md", read(os.path.join(PACKS, "sample-pack.md")).replace(
            "Change only what the task names.", "Change only what the task names, and keep it robust."))
        block = next(b for b in pack.blocks if b.name == "Scope discipline")
        text = put(STANDARD, "Context", block.text)
        self.assertEqual(of(lp.lint_text(text, STANDARD_FRAMING, None, SKILL, [pack]), "P24"), [])
        self.assertTrue(of(lp.lint_text(put(STANDARD, "Context", "The result stays robust."), STANDARD_FRAMING, None,
                                        SKILL, [pack]), "P24"))

    def test_guide_blocks_found_whole_are_exempt_and_a_changed_one_is_not(self):
        """The codex seats-models block found whole is the guide's text, blanked before any content rule reads it. With
        words added it is the writer's: P04 errs and the content rules read it."""
        self.assertEqual(shown(lint(CODEX, CODEX_FRAMING, CODEX_DECISIONS)), [])
        self.assertIn("seats-models", lp.Prompt(CODEX, frozen=lp.Context(CODEX_FRAMING, SKILL).seats_blocks()).frozen_found)
        changed = CODEX.replace("names another model.", "names another model, as needed.", 1)
        self.assertNotEqual(changed, CODEX)
        found = lint(changed, CODEX_FRAMING)
        self.assertEqual([f.level for f in of(found, "P04")], ["ERROR"])
        self.assertEqual([f.level for f in of(found, "P06")], ["ERROR"])


class Rules(unittest.TestCase):
    def test_p05_model_line_in_a_brief(self):
        found = lint(put(STANDARD, "Appendix A: subagent briefs", "Model: the fast one. The model named in every dispatch."))
        self.assertEqual(len(of(found, "P05", "WARN")), 2)
        self.assertFalse(of(lint(put(STANDARD, "Context", "Model: the product's pricing model.")), "P05"))

    def test_p06_words_slots_and_placeholder_table(self):
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", "Retry as needed.")), "P06")], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Context", "The TBD column stays.")), "P06")], ["WARN"])
        self.assertFalse(of(lint(put(STANDARD, "Context", "The `TODO` marker stays.")), "P06"))
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", "Write <the seat name> in the ledger.")), "P06")],
                         ["WARN"])
        self.assertFalse(of(lint(put(STANDARD, "Context", "<task>\nMove the endpoints.\n</task>")), "P06"))
        self.assertFalse(of(lint(put(STANDARD, "Context", "See <https://example.com/docs/router>.")), "P06"))
        marker = put(STANDARD, "Environment and constraints", "The API base URL is [you fill this in: the staging API base URL].")
        self.assertEqual([f.level for f in of(lint(marker, decisions=STANDARD_DECISIONS), "P06")], ["ERROR"])
        recorded = add_row(STANDARD_DECISIONS, "| Marker | What the person must supply | Blocks |",
                           "| [you fill this in: the staging API base URL] | the URL | phase 1 |")
        self.assertFalse(of(lint(marker, decisions=recorded), "P06"))
        self.assertEqual([f.level for f in of(lint(marker), "P06")], ["SKIPPED"])
        allowed = STANDARD_DECISIONS + "\nP06 lint-allow: parked | at: The API base URL is\n"   # never clears the table
        self.assertEqual([f.level for f in of(lint(marker, decisions=allowed), "P06")], ["ERROR"])

    def test_p07_working_folder_needs_an_absolute_path(self):
        base = STANDARD.replace("`/srv/projects/billing-web` — run", "The repository root — run")
        self.assertEqual([f.level for f in of(lint(base), "P07")], ["ERROR"])
        for path in ("`$HOME/work/billing`", "`~/work/billing`", "`C:\\work\\billing`"):
            self.assertFalse(of(lint(STANDARD.replace("`/srv/projects/billing-web`", path)), "P07"), path)

    def test_p07_the_framing_folder_starts_with_a_slash_or_home_never_a_tilde(self):
        """folder= fills the launch's `cd "{FOLDER}"`, where no quoting expands a `~` and some characters break it."""
        def with_folder(value):
            return STANDARD_DECISIONS.replace("folder=/srv/projects/billing-web", "folder=" + value)

        def p07(decisions):
            return of(lp.lint_text(STANDARD, lp.parse_framing(decisions)[0], decisions, SKILL, PACKS), "P07")

        for bad in ("~/work/billing", "~", "work/billing", "<absolute path>", "$HOMEDIR/x", "${HOME}x"):
            with self.subTest(folder=bad):
                found = p07(with_folder(bad))
                self.assertEqual([(f.level, f.line, f.allowable) for f in found], [("ERROR", None, False)])
        for good in ("/srv/projects/billing-web", "$HOME/work/bill ing", "/", "${HOME}/work", "$HOME", "/srv/it's fine"):
            with self.subTest(folder=good):
                self.assertEqual(p07(with_folder(good)), [])
        for char in ('"', "`", "\\", "!", "$"):
            with self.subTest(char=char):
                found = p07(with_folder("/srv/bill%sing" % char))
                self.assertEqual(len(found), 1)
                self.assertIn("holds %s," % char, found[0].message)

    def test_p08_wait_rule_label_and_phrase(self):
        self.assertEqual([f.level for f in of(lint(STANDARD.replace("**Wait rule.** ", "")), "P08")], ["ERROR"])
        weak = re.sub(r"\*\*Wait rule\.\*\* .*", "**Wait rule.** Report at the end.", STANDARD)
        self.assertEqual([f.level for f in of(lint(weak), "P08")], ["WARN"])
        capital = re.sub(r"\*\*Wait rule\.\*\* .*", "**Wait rule.** Only when T1 to T3 pass, report.", STANDARD)
        self.assertFalse(of(lint(capital), "P08"))

    def test_p09_bar_items_need_a_backticked_command_or_path(self):
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "The bar", "- **T5** The page looks right.")), "P09")],
                         ["WARN"])
        self.assertFalse(of(lint(put(STANDARD, "The bar", "- **T5** runs:\n```\npython3 -m pytest -q\n```")), "P09"))
        row = put(STANDARD, "The bar", "| Id | Check |\n| --- | --- |\n| T6 | the page loads |")
        self.assertEqual([f.level for f in of(lint(row), "P09")], ["WARN"])

    def test_p10_paragraph_length_but_never_a_run_rule(self):
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Context", ("word " * 170).strip() + ".")), "P10")],
                         ["WARN"])
        self.assertFalse(of(lint(put(STANDARD, "Context", ("x" * 799) + ".")), "P10"))
        self.assertFalse(of(lint(put(STANDARD, "Context", "- " + ("a" * 500) + "\n- " + ("b" * 500))), "P10"))
        rs8 = next(line for line in LEAD.split("\n") if line.startswith("- " + lp.RS_LABELS[8]))
        self.assertGreater(len(rs8), 800)   # RS8's text for an unattended run is the template's own
        self.assertFalse(of(lint(LEAD, LEAD_FRAMING), "P10"))

    def test_p11_decision_ids_need_decisions_md_named(self):
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Context", "Paths stay as D4 says.")), "P11")], ["ERROR"])
        named = put(STANDARD, "Context", "Paths stay as D4 says (see `decisions.md`, read on demand).")
        self.assertFalse(of(lint(named), "P11"))

    def test_p11_with_the_log_only_a_logged_id_counts_inside_a_literal_span_too(self):
        logged = put(STANDARD, "Context", "Per `D4`, the list is the source.")
        self.assertEqual([f.level for f in of(lint(logged, decisions=STANDARD_DECISIONS), "P11")], ["ERROR"])
        self.assertFalse(of(lint(put(STANDARD, "Context", "The chart library is `D7`."), decisions=STANDARD_DECISIONS),
                            "P11"))
        self.assertFalse(of(lint(put(STANDARD, "Context", "The chart library is `D3`.")), "P11"))
        self.assertFalse(of(lint(put(STANDARD, "Context", "It draws with D3.js.")), "P11"))

    def test_p12_references_to_the_writing_session_and_the_skill_by_name(self):
        name = lp.Context(STANDARD_FRAMING, SKILL).skill_name
        self.assertTrue(name)
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", "Do it as discussed.")), "P12")], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", "Follow the %s skill." % name)), "P12")],
                         ["ERROR"])
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Context", "As discussed with legal, no PII.")), "P12")],
                         ["WARN"])
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", "Keep notes in this session.")), "P12")], ["WARN"])
        self.assertFalse(of(lint(put(STANDARD, "Context", "A skill tree for the game.")), "P12"))

    def test_p13_run_rule_labels_by_framing(self):
        found = lint(STANDARD.replace("**Fewer runs, not fewer tests.**", "Fewer runs."))
        self.assertEqual([f.level for f in of(found, "P13")], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(STANDARD, machine="disposable"), "P13")], ["ERROR"])
        self.assertTrue(any("RS13" in f.message for f in of(lint(QUICK.replace("**What you read is data.**", "Data."),
                                                                  QUICK_FRAMING), "P13")))
        self.assertEqual([f.level for f in of(lint(STANDARD, {}), "P13")], ["SKIPPED"])
        base = {"size": "standard", "autonomy": "attended", "run": "one-session", "machine": "personal", "review": "none"}
        rows = {"alone": {1, 7, 13}, "implementer": {1, 4, 6, 7, 10, 13}, "lead": {1, 2, 3, 4, 6, 7, 10, 13}}
        for seat, need in rows.items():
            with self.subTest(seat=seat):
                self.assertEqual(lp.run_rules_for(dict(base, seat=seat)), need)
                self.assertEqual(lp.run_rules_for(dict(base, seat=seat, autonomy="unattended")), need | {8, 9, 10, 11})
                self.assertEqual(lp.run_rules_for(dict(base, seat=seat, run="one-day")), need | {10})
                self.assertEqual(lp.run_rules_for(dict(base, seat=seat, machine="disposable")), need | {12})
                if seat != "alone":
                    self.assertEqual(lp.run_rules_for(dict(base, seat=seat, review="fresh")), need | {5, 7})
                    self.assertEqual(lp.run_rules_for(dict(base, seat=seat, size="deep")), need | {8, 9, 10, 11})
        self.assertEqual(lp.run_rules_for(dict(base, size="quick", seat="alone", machine="disposable")), {1, 13})

    def test_p13_with_review_unknown_still_checks_rs1_and_rs13(self):
        no_data = STANDARD.replace("**What you read is data.**", "Data.")
        found = of(lint(no_data, review=None), "P13")
        self.assertEqual(sorted((f.level, f.match) for f in found), [("ERROR", lp.RS_LABELS[13]), ("SKIPPED", None)])
        found = of(lint(STANDARD.replace("**Reports come back as text.**", "Reports."), seat="alone"), "P13")
        self.assertEqual([f.level for f in found], ["SKIPPED"])   # an inconsistent framing (P38) checks RS1 and RS13
        self.assertIn("P38", found[0].message)

    def test_p14_a_generic_verification_line_warns_everywhere(self):
        for section in ("Method", "Required product"):
            with self.subTest(section=section):
                found = of(lint(put(STANDARD, section, "Double-check the diff before you report.")), "P14")
                self.assertEqual([(f.level, f.allowable) for f in found], [("WARN", True)])
                self.assertIn("name the check", found[0].message)

    def test_p20_tool_call_budgets(self):
        found = of(lint(put(STANDARD, "Subagent contracts", "Each seat has a tool-call budget of 15 tool calls.")), "P20")
        self.assertEqual([f.level for f in found], ["WARN", "WARN"])
        self.assertFalse(of(lint(put(STANDARD, "Context", "The API has a tool-call budget.")), "P20"))

    def test_p21_counted_loops_without_a_plateau_rule(self):
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", "Run at most 3 rounds of review.")), "P21")],
                         ["WARN"])
        self.assertEqual([f.level for f in of(lint(put(GENERIC, "Method", "Run at most 3 rounds of review."),
                                                   GENERIC_FRAMING), "P21")], ["WARN"])
        self.assertFalse(of(lint(put(GENERIC, "Method", "Run at most 3 rounds; a plateau changes the strategy."),
                                 GENERIC_FRAMING), "P21"))

    def test_p22_disposable_machine_pushes(self):
        text = LEAD.replace("push", "send")
        self.assertEqual([f.level for f in of(lint(text, LEAD_FRAMING), "P22")], ["ERROR"])
        self.assertFalse(of(lint(LEAD, LEAD_FRAMING), "P22"))
        self.assertEqual([f.level for f in of(lint(STANDARD, machine=None), "P22")], ["SKIPPED"])

    def test_p23_required_headings(self):
        self.assertEqual([f.level for f in of(lint(STANDARD.replace("## Context\n", "## Background\n")), "P23")], ["ERROR"])
        self.assertFalse(of(lint(QUICK, QUICK_FRAMING), "P23"))
        numbered = STANDARD.replace("## Mission\n", "## 2. Mission\n").replace("## Scope\n", "## 04 / Scope\n")
        self.assertFalse(of(lint(numbered), "P23"))
        lead = LEAD.replace("## Subagent contracts\n", "## Seat contracts\n")
        self.assertEqual([f.level for f in of(lint(lead, LEAD_FRAMING), "P23")], ["ERROR"])

    def test_p24_soft_adjectives(self):
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Required product", "Robust and polished errors.")), "P24")],
                         ["WARN", "WARN"])
        self.assertFalse(of(lint(put(STANDARD, "Required product", "The `robust` flag and \"polished\" copy.")), "P24"))

    def test_p25_word_count_counts_every_word(self):
        padded = put(QUICK, "Scope", ("filler " * 700).strip())
        self.assertEqual([f.level for f in of(lint(padded, QUICK_FRAMING), "P25")], ["WARN"])
        document = lp.lint_document(STANDARD, STANDARD_FRAMING, None, SKILL, PACKS)
        self.assertEqual(document.words, len(STANDARD.split()))

    def test_p26_weak_result_line(self):
        self.assertEqual([f.level for f in of(lint(STANDARD.replace("A weak result exports", "It exports")), "P26")],
                         ["ERROR"])
        self.assertFalse(of(lint(QUICK, QUICK_FRAMING), "P26"))

    def test_p29_identity_paragraph(self):
        identity = STANDARD.split("\n")[2]
        self.assertTrue(identity.startswith("You build this change yourself"))
        self.assertFalse(of(lint(STANDARD), "P29"))
        self.assertEqual([f.level for f in of(lint(STANDARD.replace(identity + "\n\n", "")), "P29")], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(STANDARD.replace("# Add a CSV", "Add a CSV")), "P29")], ["ERROR"])

    def test_the_whole_preamble_is_instruction_text_and_the_title_is_not(self):
        text = STANDARD.replace("# Add a CSV export to the invoices list\n",
                                "# Add a CSV export to the invoices list as needed\n")
        self.assertEqual([f.level for f in of(lint(text), "P06")], ["WARN"])   # the title names the task: content
        text = STANDARD.replace("# Add a CSV export", "Retry as needed.\n\n# Add a CSV export")
        self.assertEqual([f.level for f in of(lint(text), "P06")], ["ERROR"])

    def test_p30_allowance_lines(self):
        text = put(STANDARD, "Context", "A robust thing.")
        for line, words in (("P99 lint-allow: x | at: A robust thing.", "unknown rule"),
                            ("P04 lint-allow: x | at: A robust thing.", "cannot be allowed"),
                            ("P24 lint-allow: | at: A robust thing.", "empty reason"),
                            ("P24 lint-allow: the brand | at: A sturdy thing.", "no prompt line holds"),
                            ("P24 lint-allow: the brand | at: ## ", "prompt lines hold"),
                            ("P24 lint-allow: the brand | at:", "empty `at:` anchor"),
                            ("P34 lint-allow: quoted | at: A robust thing.", "only allowable branch"),
                            ("- P24 lint-allow the brand", "does not parse")):
            with self.subTest(line=line):
                found = of(lint(text, decisions=STANDARD_DECISIONS + "\n" + line + "\n"), "P30")
                self.assertEqual([(f.level, f.allowable) for f in found], [("ERROR", False)])
                self.assertIn(words, found[0].message)
        for prose in ("No lint-allow line was needed.", "lint-allow P24: the brand", "Kept: P24 lint-allow: the brand"):
            with self.subTest(prose=prose):
                found = lint(text, decisions=STANDARD_DECISIONS + "\n" + prose + "\n")
                self.assertFalse(of(found, "P30"))
                self.assertEqual([f.level for f in of(found, "P24")], ["WARN"])
        commented = STANDARD_DECISIONS + "\n<!-- each allowance: Pnn lint-allow: <reason> | at: <a line> -->\n"
        self.assertFalse(of(lint(text, decisions=commented), "P30"))


class LintAllow(unittest.TestCase):
    TEXT = put(STANDARD, "Context", "The landing copy stays robust.\n\nThe second line is robust too.")

    def test_allowed_finding_has_its_reason_and_does_not_count(self):
        decisions = STANDARD_DECISIONS + "\nP24 lint-allow: the person's own word | at: The landing copy stays robust.\n"
        found = of(lint(self.TEXT, decisions=decisions), "P24")
        self.assertEqual(sorted(f.level for f in found), ["ALLOWED", "WARN"])
        allowed = next(f for f in found if f.level == "ALLOWED")
        self.assertEqual(allowed.reason, "the person's own word")
        self.assertTrue(allowed.as_text().endswith("(lint-allow: the person's own word)"))

    def test_allow_covers_one_block_only(self):
        decisions = STANDARD_DECISIONS + "\nP24 lint-allow: one | at: The second line is robust too.\n"
        found = of(lint(self.TEXT, decisions=decisions), "P24")
        self.assertEqual([f.level for f in sorted(found, key=lambda f: f.line)], ["WARN", "ALLOWED"])

    def test_allow_covers_a_fenced_block(self):
        text = put(STANDARD, "Context", "```\nrobust\npolished\n```")
        found = of(lint(text, decisions=STANDARD_DECISIONS + "\nP24 lint-allow: quoted | at: polished\n"), "P24")
        self.assertEqual(found, [])   # fences are literal: nothing to allow
        text = put(STANDARD, "Context", "- robust here\n  and polished here")
        found = of(lint(text, decisions=STANDARD_DECISIONS + "\nP24 lint-allow: the list | at: and polished here\n"), "P24")
        self.assertEqual([f.level for f in found], ["ALLOWED", "ALLOWED"])

    def test_p24_on_a_value_the_person_gave_is_cleared_by_lint_allow(self):
        text = put(STANDARD, "Method", "The vendor's tool is called Robust Export and stays as it is.")
        self.assertEqual([f.level for f in of(lint(text), "P24")], ["WARN"])
        decisions = STANDARD_DECISIONS + "\nP24 lint-allow: the vendor tool's own name | at: The vendor's tool is called\n"
        self.assertEqual([f.level for f in of(lint(text, decisions=decisions), "P24")], ["ALLOWED"])

    def test_non_allowable_rule_is_refused(self):
        decisions = STANDARD_DECISIONS + "\nP13 lint-allow: no | at: The landing copy stays robust.\n"
        found = lint(self.TEXT.replace("**Fewer runs, not fewer tests.**", "Fewer runs."), decisions=decisions)
        self.assertEqual([f.level for f in of(found, "P13")], ["ERROR"])
        self.assertEqual([f.level for f in of(found, "P30")], ["ERROR"])

    def test_line_less_finding_is_allowed_by_a_record_without_an_anchor(self):
        padded = put(QUICK, "Scope", ("filler " * 700).strip())
        decisions = QUICK_DECISIONS + "\nP25 lint-allow: the oracle is long\n"
        self.assertEqual([f.level for f in of(lint(padded, QUICK_FRAMING, decisions), "P25")], ["ALLOWED"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def files(self, text=STANDARD, decisions=STANDARD_DECISIONS):
        prompt, record = os.path.join(self.tmp, "master-prompt.md"), os.path.join(self.tmp, "decisions.md")
        write(prompt, text)
        write(record, decisions)
        return prompt, record

    def test_exit_codes(self):
        prompt, record = self.files()
        self.assertEqual(run_py(LINTER, [prompt, "--decisions", record]).returncode, 0)
        prompt, record = self.files(STANDARD.replace("**Wait rule.** ", ""))
        self.assertEqual(run_py(LINTER, [prompt, "--decisions", record]).returncode, 1)
        self.assertEqual(run_py(LINTER, [os.path.join(self.tmp, "missing.md")]).returncode, 2)
        self.assertEqual(run_py(LINTER, [prompt, "--size", "huge"]).returncode, 2)
        self.assertEqual(run_py(LINTER, []).returncode, 2)

    def test_text_output_lines(self):
        prompt, record = self.files(put(STANDARD, "Context", "A robust thing."))
        proc = run_py(LINTER, [prompt, "--decisions", record])
        lines = proc.stdout.strip().split("\n")
        self.assertRegex(lines[0], r"^P24 WARN line \d+: soft adjective with no metric: 'robust'$")
        self.assertEqual(lines[-1], "errors: 0, warnings: 1, allowed: 0")

    def test_json_shape(self):
        prompt, record = self.files(put(STANDARD, "Context", "A robust thing."))
        data = json.loads(run_py(LINTER, [prompt, "--decisions", record, "--json"]).stdout)
        self.assertEqual(sorted(data), ["allowed", "errors", "file", "findings", "framing", "published_words", "warnings",
                                        "words"])
        self.assertEqual(sorted(data["findings"][0]), ["level", "line", "match", "message", "reason", "rule"])
        self.assertEqual((data["errors"], data["warnings"], data["allowed"]), (0, 1, 0))
        self.assertEqual(data["framing"], dict(STANDARD_FRAMING))
        self.assertEqual(data["published_words"], 0)   # the skill ships no pack
        self.assertEqual(data["words"], len(put(STANDARD, "Context", "A robust thing.").split()))

    def test_framing_from_decisions_and_flags(self):
        framing, invalid = lp.parse_framing(STANDARD_DECISIONS)
        self.assertEqual(framing, {"size": "standard", "autonomy": "attended", "harness": "claude-code",
                                   "launch": "interactive", "model": MODEL, "effort": "default", "run": "one-session",
                                   "machine": "personal", "seat": "implementer", "review": "fresh",
                                   "folder": "/srv/projects/billing-web"})
        self.assertEqual(invalid, {})
        framing, invalid = lp.parse_framing("Framing: size=huge; harness=Other Thing; model=%s; folder=/x; y\n"
                                            % lp.MODEL_PLACEHOLDER)
        self.assertEqual((framing, invalid), ({"harness": "Other Thing", "model": lp.MODEL_PLACEHOLDER, "folder": "/x; y"},
                                              {"size": "huge"}))
        prompt, record = self.files(decisions=STANDARD_DECISIONS.replace("size=standard", "size=huge"))
        proc = run_py(LINTER, [prompt, "--decisions", record, "--json"])
        self.assertIn("framing size='huge' is not one of quick|standard|deep", proc.stderr)
        data = json.loads(run_py(LINTER, [prompt, "--decisions", record, "--json", "--size", "standard",
                                          "--model", OTHER]).stdout)
        self.assertEqual((data["framing"]["size"], data["framing"]["model"]), ("standard", OTHER))
        self.assertTrue(any(f["rule"] == "P04" for f in data["findings"]))   # the seats block names the framing's model


class Matcher(unittest.TestCase):
    def test_reflowed_pack_text_is_found(self):
        reflowed = BLOCKS["Scope discipline"].text.replace(" Leave every file", "\nLeave every\nfile")
        text = STANDARD.replace(BLOCKS["Scope discipline"].text, reflowed)
        self.assertNotEqual(text, STANDARD)
        prompt = lp.Prompt(text, PACK.blocks)
        self.assertEqual(list(prompt.found), [BLOCKS["Scope discipline"].key])
        self.assertEqual(prompt.found[BLOCKS["Scope discipline"].key].missing, [])

    def test_a_partial_line_keeps_its_other_words_linted(self):
        text = put(STANDARD, "Context", "Change only what the task names. The page stays robust.")
        found = lint(text)
        self.assertEqual([f.level for f in of(found, "P24")], ["WARN"])

    def test_a_person_s_value_is_exempt_in_its_own_section_only(self):
        decisions = add_row(STANDARD_DECISIONS, lp.WORDS_HEADER_LINE,
                            "| W9 | \"robust exports\" | value | Exports stay robust exports. | Context | none: a name |")
        text = put(STANDARD, "Context", "Exports stay robust exports.")
        self.assertFalse(of(lint(text, decisions=decisions), "P24"))
        elsewhere = put(STANDARD, "Required product", "Exports stay robust exports.")
        self.assertTrue(of(lint(elsewhere, decisions=decisions), "P24"))

    def test_without_packs_nothing_is_matched_and_p33_says_nothing(self):
        found = lp.lint_text(STANDARD, STANDARD_FRAMING, STANDARD_DECISIONS, SKILL, [])
        self.assertEqual(of(found, "P33"), [])
        self.assertEqual(lp.load_packs(os.path.join(SKILL, "packs")), [])   # README.md and TEMPLATE.md are no packs

    def test_the_pack_is_parsed_with_its_matches_and_blocks(self):
        self.assertEqual(PACK.matches, [MODEL])
        self.assertEqual([b.name for b in PACK.blocks], ["Scope discipline", "Steady progress", "Plain final report"])
        self.assertEqual(BLOCKS["Steady progress"].when, "autonomy=unattended")
        self.assertTrue(BLOCKS["Scope discipline"].adapt_nothing)
        self.assertFalse(BLOCKS["Plain final report"].adapt_nothing)
        star = lp.Pack("p.md", "## 1. Facts\n| `MATCHES` | `example-*, other-model` | |\n")
        self.assertEqual([star.matches_model(m) for m in (MODEL, OTHER, "other-model", "another")], [True, True, True, False])


class P32(unittest.TestCase):
    def test_an_html_comment_in_the_delivered_prompt(self):
        text = put(STANDARD, "Context", "<!-- a note -->\nText `<!-- in code -->`.\n\n```\n<!-- in a fence -->\n```")
        found = of(lint(text), "P32")
        self.assertEqual([(f.level, f.allowable) for f in found], [("ERROR", False)])


class P33(unittest.TestCase):
    def test_a_b_the_guidance_record(self):
        dropped = STANDARD_DECISIONS.replace("| Scope discipline [SP #scope] | sample-pack.md | D4: the run changes code | "
                                             "Run rules, Working on |\n", "")
        self.assertEqual([branch(f) for f in errors(of(lint(STANDARD, decisions=dropped), "P33"))], ["(a)"])
        missing = STANDARD.replace(BLOCKS["Scope discipline"].text, "Keep the change small.")
        self.assertEqual([branch(f) for f in errors(of(lint(missing, decisions=STANDARD_DECISIONS), "P33"))], ["(b)"])
        self.assertEqual([f.level for f in of(lint(STANDARD), "P33")], ["SKIPPED"])   # (a), (b), (d) need decisions

    def test_d_the_fact_its_block_s_when_names(self):
        text = STANDARD.replace(BLOCKS["Scope discipline"].text, BLOCKS["Steady progress"].text)
        row = "| Steady progress [SP #progress] | sample-pack.md | %s | Run rules, Working on |"
        decisions = STANDARD_DECISIONS.replace("| Scope discipline [SP #scope] | sample-pack.md | D4: the run changes code | "
                                               "Run rules, Working on |", row % "autonomy=unattended")
        found = errors(of(lint(text, decisions=decisions), "P33"))
        self.assertEqual([branch(f) for f in found], ["(d)"])   # the framing is attended
        unattended = decisions.replace("autonomy=attended", "autonomy=unattended")
        framing = dict(STANDARD_FRAMING, autonomy="unattended")
        self.assertFalse(errors(of(lp.lint_text(text, framing, unattended, SKILL, PACKS), "P33")))
        self.assertFalse(errors(of(lint(STANDARD, decisions=STANDARD_DECISIONS.replace("D4: the run", "D3: the run")), "P33")))
        found = errors(of(lint(STANDARD, decisions=STANDARD_DECISIONS.replace("D4: the run", "D1: the run")), "P33"))
        self.assertEqual([branch(f) for f in found], ["(d)"])   # D1 is the harness, never a task fact

    def test_when_keys_reads_a_second_key_after_a_bare_or(self):
        self.assertEqual(lp.when_keys("autonomy=unattended or run=multi-session"),
                         ({"autonomy": {"unattended"}, "run": {"multi-session"}}, False))
        self.assertEqual(lp.when_keys("run=one-day or multi-session"), ({"run": {"one-day", "multi-session"}}, False))
        self.assertEqual(lp.when_keys("launch=headless, or a seat runs for hours"), ({"launch": {"headless"}}, True))
        self.assertEqual(lp.when_keys("size=deep"), ({}, False))
        self.assertEqual(lp.when_keys("the run changes code"), ({}, False))

    def test_b_a_row_naming_no_block_warns(self):
        decisions = add_row(STANDARD_DECISIONS, lp.GUIDANCE_HEADER_LINE,
                            "| No such block [SP] | sample-pack.md | D4: the run changes code | Run rules |")
        self.assertEqual([f.level for f in of(lint(STANDARD, decisions=decisions), "P33")], ["WARN"])

    def test_e_pack_text_altered(self):
        text = STANDARD.replace("Change only what the task names.", "Change what the task names.")
        found = errors(of(lint(text, decisions=STANDARD_DECISIONS), "P33"))
        self.assertEqual([branch(f) for f in found], ["(e)"])

    def test_c_a_block_of_a_pack_that_does_not_match_the_model(self):
        found = errors(of(lint(STANDARD, decisions=STANDARD_DECISIONS, model=OTHER), "P33"))
        self.assertEqual([branch(f) for f in found], ["(c)"])
        self.assertIn("does not match model=%s" % OTHER, found[0].message)
        second = lp.Pack("second-pack.md", read(os.path.join(PACKS, "sample-pack.md")).replace("### Scope discipline",
                                                                                               "### Another block"))
        found = errors(of(lp.lint_text(STANDARD, STANDARD_FRAMING, STANDARD_DECISIONS, SKILL, [PACK, second]), "P33"))
        self.assertEqual({branch(f) for f in found}, {"(c)"})   # the text is in both packs: each block is refused
        self.assertTrue(all("two or more packs match it" in f.message for f in found))

    def test_c_no_pack_is_read_with_model_choose(self):
        self.assertIsNone(lp.Context(dict(STANDARD_FRAMING, model=lp.MODEL_CHOOSE), SKILL, PACKS).pack)
        self.assertEqual(lp.Context(STANDARD_FRAMING, SKILL, PACKS).pack.name, PACK.name)
        star = lp.Pack("star.md", "## 1. Facts\n| `MATCHES` | `*` | |\n")   # a prefix that matches any id
        self.assertTrue(star.matches_model(lp.MODEL_CHOOSE))
        self.assertIsNone(lp.Context(dict(STANDARD_FRAMING, model=lp.MODEL_CHOOSE), SKILL, [star]).pack)
        found = errors(of(lint(STANDARD, decisions=STANDARD_DECISIONS, model=lp.MODEL_CHOOSE), "P33"))
        self.assertEqual([branch(f) for f in found], ["(c)"])
        self.assertIn("model=choose reads no pack", found[0].message)


class P34(unittest.TestCase):
    def test_a_b_c_the_autonomy_row(self):
        no_row = "\n".join(line for line in ALONE_DECISIONS.split("\n") if "| D2 | Autonomy |" not in line)
        self.assertEqual([branch(f) for f in errors(of(lint(ALONE, ALONE_FRAMING, no_row), "P34"))], ["(a)"])
        wrong = ALONE_DECISIONS.replace("| D2 | Autonomy | unattended,", "| D2 | Autonomy | attended,")
        self.assertIn("(b)", [branch(f) for f in errors(of(lint(ALONE, ALONE_FRAMING, wrong), "P34"))])
        default = ALONE_DECISIONS.replace("| Stated | 2026-10-01 | live |\n", "| Default accepted | 2026-10-01 | live |\n", 2)
        self.assertIn("(c)", [branch(f) for f in errors(of(lint(ALONE, ALONE_FRAMING, default), "P34"))])
        unquoted = ALONE_DECISIONS.replace("\"I'll start it and walk away\"", "the person said so")
        self.assertEqual([branch(f) for f in errors(of(lint(ALONE, ALONE_FRAMING, unquoted), "P34"))], ["(c)"])

    def test_c_e_the_row_against_the_words_it_quotes(self):
        lists = lp.Context(ALONE_FRAMING, SKILL).autonomy_lists
        self.assertIn("start it and walk away", lists["unattended"])
        self.assertIn("I'll watch it", lists["attended"])
        contradicted = ALONE_DECISIONS.replace("\"I'll start it and walk away\"", "\"I'll watch it\"")
        found = errors(of(lint(ALONE, ALONE_FRAMING, contradicted), "P34"))
        self.assertEqual([(branch(f), f.allowable) for f in found], [("(e)", True)])
        both = ALONE_DECISIONS.replace("\"I'll start it and walk away\"", "\"I'll watch it, then leave it running\"")
        self.assertEqual([f.level for f in of(lint(ALONE, ALONE_FRAMING, both), "P34")], ["WARN"])

    def test_d_rs8_s_text_follows_autonomy_and_launch(self):
        headless = next(line for line in ALONE.split("\n") if line.startswith("- " + lp.RS_LABELS[8]))
        other = next(line for line in LEAD.split("\n") if line.startswith("- " + lp.RS_LABELS[8]))
        self.assertIn(lp.RS8_HEADLESS, headless)
        self.assertIn(lp.RS8_OTHER, other)
        self.assertFalse(errors(of(lint(ALONE, ALONE_FRAMING), "P34")))
        self.assertFalse(errors(of(lint(LEAD, LEAD_FRAMING), "P34")))
        found = errors(of(lint(ALONE, ALONE_FRAMING, launch="cloud"), "P34"))
        self.assertEqual([branch(f) for f in found], ["(d)"])
        self.assertIn("HEADLESS text", found[0].message)
        found = errors(of(lint(LEAD, LEAD_FRAMING, launch="headless"), "P34"))
        self.assertEqual([branch(f) for f in found], ["(d)"])
        self.assertEqual([branch(f) for f in errors(of(lint(ALONE, ALONE_FRAMING, autonomy="attended"), "P34"))], ["(d)"])
        attended = put(STANDARD, "Run rules", "- " + lp.RS_LABELS[8] + " " + lp.RS8_ATTENDED + " that the run stops.")
        self.assertFalse(errors(of(lint(attended), "P34")))
        self.assertEqual([branch(f) for f in errors(of(lint(attended, autonomy="unattended", launch="headless"), "P34"))],
                         ["(d)"])
        self.assertEqual([f.level for f in of(lint(ALONE, ALONE_FRAMING, ALONE_DECISIONS, launch=None), "P34")],
                         ["SKIPPED"])

    def test_p34_is_allowable_only_in_e(self):
        contradicted = ALONE_DECISIONS.replace("\"I'll start it and walk away\"", "\"I'll watch it\"")
        allowed = contradicted + "\nP34 lint-allow: the person said they will not watch it\n"
        self.assertEqual([f.level for f in of(lint(ALONE, ALONE_FRAMING, allowed), "P34")], ["ALLOWED"])
        no_row = "\n".join(line for line in allowed.split("\n") if "| D2 | Autonomy |" not in line)
        self.assertEqual([f.level for f in of(lint(ALONE, ALONE_FRAMING, no_row), "P34")], ["ERROR"])


class P35(unittest.TestCase):
    def test_a_the_record_exists(self):
        empty = re.sub(r"\| W1 .*\n\| W2 .*\n", "", STANDARD_DECISIONS)
        self.assertNotEqual(empty, STANDARD_DECISIONS)
        self.assertEqual([branch(f) for f in of(lint(STANDARD, decisions=empty), "P35")], ["(a)"])
        self.assertEqual([f.level for f in of(lint(STANDARD), "P35")], ["SKIPPED"])

    def test_b_c_the_kind_and_the_carried_text(self):
        kind = STANDARD_DECISIONS.replace("| wish | The export", "| hope | The export")
        self.assertEqual([branch(f) for f in of(lint(STANDARD, decisions=kind), "P35")], ["(b)"])
        dropped = STANDARD.replace("1. The export holds exactly the filtered rows, in the list's order.\n", "")
        self.assertEqual([branch(f) for f in of(lint(dropped, decisions=STANDARD_DECISIONS), "P35")], ["(c)"])

    def test_c_the_section_launch_and_outside_the_prompt(self):
        for cell, ok in (("Launch", True), ("not in the prompt: the person's own note", True),
                         ("not in the prompt:", False), ("Nowhere", False)):
            with self.subTest(cell=cell):
                decisions = add_row(STANDARD_DECISIONS, lp.WORDS_HEADER_LINE,
                                    "| W9 | \"tonight\" | wish | the launch time | %s | none: the launch |" % cell)
                self.assertEqual(not of(lint(STANDARD, decisions=decisions), "P35"), ok)

    def test_d_a_value_is_the_value_as_said(self):
        decisions = add_row(STANDARD_DECISIONS, lp.WORDS_HEADER_LINE,
                            "| W9 | \"invoices.csv\" | value | The export holds exactly the filtered rows | Mission | T2 |")
        self.assertEqual([branch(f) for f in of(lint(STANDARD, decisions=decisions), "P35")], ["(d)"])

    def test_d_a_prohibition_s_paths_and_names_as_written(self):
        self.assertEqual(lp.identifiers("don't touch src/billing or `migrations`, e.g. the .env file"),
                         ["migrations", "src/billing", ".env"])
        self.assertTrue(lp.carries_identifier("Forbidden: `src/billing/` and more", "src/billing"))
        self.assertFalse(lp.carries_identifier("Forbidden: `src/billing_v2/`", "src/billing"))
        decisions = STANDARD_DECISIONS.replace("\"leave web/payments alone\"", "\"leave web/payment_api alone\"")
        found = of(lint(STANDARD, decisions=decisions), "P35")
        self.assertEqual([(f.level, branch(f)) for f in found], [("WARN", "(d)")])

    def test_e_checked_by_the_bar(self):
        for cell, ok in (("T2", True), ("T9", False), ("none: the reason", True), ("none:", False), ("the reviewer", False)):
            with self.subTest(cell=cell):
                decisions = STANDARD_DECISIONS.replace("| Mission | T2 |", "| Mission | %s |" % cell)
                self.assertEqual(not of(lint(STANDARD, decisions=decisions), "P35"), ok)
        quality = add_row(STANDARD_DECISIONS, lp.WORDS_HEADER_LINE,
                          "| W9 | \"it must feel fast\" | quality | The export holds exactly the filtered rows | Mission | "
                          "none: subjective |")
        self.assertEqual([branch(f) for f in of(lint(STANDARD, decisions=quality), "P35")], ["(e)"])


class P36(unittest.TestCase):
    def test_a_no_review_sentence_without_a_review_seat(self):
        found = errors(of(lint(STANDARD, review="none"), "P36"))
        self.assertEqual(sorted(branch(f) for f in found), ["(a)", "(a)"])   # V2's words and RS5's label
        self.assertEqual([f.level for f in of(lint(STANDARD, review=None), "P36")], ["SKIPPED"])

    def test_b_no_seat_text_on_a_run_that_works_alone(self):
        text = put(ALONE, "Method", lp.DELEGATE_SENTENCE)
        self.assertEqual([branch(f) for f in errors(of(lint(text, ALONE_FRAMING), "P36"))], ["(b)"])
        text = put(ALONE, "Run rules", "- " + lp.RS_LABELS[4] + " Seats report as text.")
        self.assertEqual([branch(f) for f in errors(of(lint(text, ALONE_FRAMING), "P36"))], ["(b)"])

    def test_c_no_ledger_sentence_without_a_ledger(self):
        text = QUICK.replace("note it in your report", "note it in the ledger or your report")
        self.assertEqual([branch(f) for f in errors(of(lint(text, QUICK_FRAMING), "P36"))], ["(c)"])
        accounting = put(QUICK, "Scope", "The app posts each sale in the ledger.")
        self.assertFalse(of(lint(accounting, QUICK_FRAMING), "P36"))

    def test_c_names_its_escape_and_skips_when_unknown(self):
        text = QUICK.replace("note it in your report", "note it in the ledger or your report")
        found = errors(of(lint(text, QUICK_FRAMING), "P36"))
        self.assertIn("inline code", found[0].message)
        found = of(lint(text, dict(QUICK_FRAMING, size="standard", seat=None, run=None)), "P36")
        self.assertIn("SKIPPED", [f.level for f in found])

    def test_b_and_c_read_no_code_block(self):
        fence = "```\n- " + lp.RS_LABELS[4] + " quoted\nrecord in the ledger\n```"
        self.assertFalse(of(lint(put(QUICK, "Scope", fence), QUICK_FRAMING), "P36"))
        indented = "Quoted:\n\n    " + lp.DELEGATE_SENTENCE
        self.assertFalse(of(lint(put(QUICK, "Scope", indented), QUICK_FRAMING), "P36"))

    def test_d_e_the_warnings_for_any_model(self):
        no_v1 = STANDARD.replace(lp.V1, "")
        self.assertEqual([(f.level, branch(f)) for f in of(lint(no_v1), "P36")], [("WARN", "(d)")])
        no_v2 = STANDARD.replace(lp.V2, "")
        for model in (MODEL, OTHER):
            with self.subTest(model=model):
                found = of(lint(no_v2.replace(MODEL, model), model=model), "P36")
                self.assertEqual([(f.level, branch(f)) for f in found], [("WARN", "(e)")])


class P37(unittest.TestCase):
    def test_a_the_seats_models_text_on_a_run_that_works_alone(self):
        for harness in ("claude-code", "codex", "generic"):
            for model in (lp.MODEL_CHOOSE, MODEL):
                with self.subTest(harness=harness, model=model):
                    block = fill_block(harness, "seats-models", {"model": model}, {"MODEL_ID": MODEL})
                    framing = dict(ALONE_FRAMING, harness=harness)
                    found = errors(of(lint(put(ALONE, "Method", block), framing), "P37"))
                    self.assertEqual([branch(f) for f in found], ["(a)"])
        block = fill_block("claude-code", "seats-models", {"model": lp.MODEL_CHOOSE}, {})
        self.assertEqual([branch(f) for f in errors(of(lint(put(QUICK, "Scope", block), QUICK_FRAMING), "P37"))], ["(a)"])
        self.assertFalse(of(lint(put(ALONE, "Method", "```\n%s\n```" % block), ALONE_FRAMING), "P37"))
        self.assertFalse(of(lint(STANDARD), "P37"))
        self.assertEqual([f.level for f in of(lint(put(ALONE, "Method", block), ALONE_FRAMING, harness=None), "P37")],
                         ["SKIPPED"])

    def test_b_a_run_rule_outside_the_table_s_set_warns(self):
        text = put(GENERIC, "Run rules", "- " + lp.RS_LABELS[2] + " Only you change git state.")
        found = of(lint(text, GENERIC_FRAMING), "P37")
        self.assertEqual([(f.level, branch(f)) for f in found], [("WARN", "(b)")])
        rs8 = put(GENERIC, "Run rules", "- " + lp.RS_LABELS[8] + " " + lp.RS8_ATTENDED + ".")
        self.assertFalse(of(lint(rs8, GENERIC_FRAMING), "P37"))   # a long operation is no framing fact


class P38(unittest.TestCase):
    def test_the_seat_rule(self):
        for override in ({"seat": "alone", "review": "fresh"}, {"seat": "alone", "size": "deep", "review": "none"},
                         {"seat": "implementer", "run": "one-day"}, {"size": "quick", "seat": "lead"}):
            with self.subTest(**override):
                self.assertEqual([f.level for f in of(lint(STANDARD, **override), "P38")], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(STANDARD, seat="alone", review=None), "P38")], ["SKIPPED"])

    def test_the_new_framing_fields(self):
        cases = {"harness": ("cursor", "harness=cursor names no guide"),
                 "launch": ("headless", "launch=headless with autonomy=attended"),
                 "effort": ("very high", "effort=very high is neither"),
                 "model": ("two words", "model=two words is neither")}
        for key, (value, words) in cases.items():
            with self.subTest(key=key):
                found = of(lint(STANDARD, **{key: value}), "P38")
                self.assertEqual([(f.level, f.allowable) for f in found], [("ERROR", False)])
                self.assertIn(words, found[0].message)
        self.assertEqual(lp.framing_conflicts({"autonomy": "unattended", "launch": "interactive"}, SKILL),
                         ["launch=interactive with autonomy=unattended: an unattended run is launched headless or cloud "
                          "or other"])
        for ok in ({"model": lp.MODEL_PLACEHOLDER}, {"model": lp.MODEL_CHOOSE}, {"effort": "default"}, {"effort": "xhigh"},
                   {"harness": "generic"}):
            self.assertEqual(lp.framing_conflicts(ok, SKILL), [], ok)

    def test_a_seat_whose_prompt_says_it_works_alone(self):
        self.assertEqual(lp.Context(STANDARD_FRAMING, SKILL).alone_sentences(), [lp.QUICK_ALONE])
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "Method", lp.QUICK_ALONE)), "P38")], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(put(STANDARD, "identity", lp.QUICK_ALONE)), "P38")], ["ERROR"])
        self.assertFalse(of(lint(put(STANDARD, "Method", "```\n" + lp.QUICK_ALONE + "\n```")), "P38"))

    def test_an_inconsistent_framing_is_never_allowable(self):
        decisions = STANDARD_DECISIONS + "\nP38 lint-allow: no\n"
        found = lint(STANDARD, decisions=decisions, seat="alone")
        self.assertEqual([f.level for f in of(found, "P38")], ["ERROR"])
        self.assertEqual([f.level for f in of(found, "P30")], ["ERROR"])


class P40(unittest.TestCase):
    def test_every_good_launch_passes(self):
        for name in GOOD:
            text, decisions, framing = FIX[name]
            with self.subTest(fixture=name):
                self.assertEqual(of(lint(text, framing, decisions), "P40"), [])

    def test_a_changed_line_errs_naming_it(self):
        decisions = STANDARD_DECISIONS.replace("then paste the contents of prompts/", "then type the contents of prompts/")
        found = of(lint(STANDARD, decisions=decisions), "P40")
        self.assertEqual([(f.level, f.allowable) for f in found], [("ERROR", False)])
        self.assertIn("its line 4", found[0].message)
        decisions = STANDARD_DECISIONS.replace("--model %s" % MODEL, "--model %s" % OTHER)
        self.assertEqual([f.level for f in of(lint(STANDARD, decisions=decisions), "P40")], ["ERROR"])

    def test_the_effort_fragments_follow_the_framing(self):
        self.assertEqual([f.level for f in of(lint(ALONE, ALONE_FRAMING, ALONE_DECISIONS, effort="default"), "P40")],
                         ["ERROR"])
        self.assertEqual([f.level for f in of(lint(STANDARD, decisions=STANDARD_DECISIONS, effort="high"), "P40")],
                         ["ERROR"])

    def test_a_command_split_across_lines_errs(self):
        decisions = ALONE_DECISIONS.replace(" --permission-mode acceptEdits --allowed-tools",
                                            "\n    --permission-mode acceptEdits --allowed-tools", 1)
        found = of(lint(ALONE, ALONE_FRAMING, decisions), "P40")
        self.assertEqual(len(found), 1)
        self.assertIn("split across lines", found[0].message)

    def test_a_line_of_another_launch_block_errs(self):
        headless = fill_block("claude-code", "launch-headless", ALONE_FRAMING, {
            "MODEL_ID": MODEL, "EFFORT": "high", "FOLDER": "/srv/projects/billing-web", "TASK_ID": "invoice-csv-export",
            "BENCH_MKDIR": "", "RUN_DIR": "prompts/invoice-csv-export/run", "SESSION_ID": "s-1",
            "PERMISSION_MODE": "acceptEdits", "ALLOWED_TOOLS": "Bash(git *)", "EXTRA_FLAGS": ""})
        loop = "\n".join(line for line in headless.split("\n") if line.strip() == "done )" or "for n in 1 2 3" in line)
        decisions = STANDARD_DECISIONS.replace("## Placeholders in the prompt", loop + "\n\n## Placeholders in the prompt")
        found = of(lint(STANDARD, decisions=decisions), "P40")
        self.assertEqual(len(found), 1)
        self.assertIn("launch-headless", found[0].message)

    def test_a_quick_unattended_launch_has_no_resume_loop(self):
        """The quick lane takes a small unattended task. A quick run keeps no ledger, so its launch is the guide's
        launch-headless block without the `{LOOP: …}` text; the block with the loop is not this framing's launch."""
        framing = dict(QUICK_FRAMING, autonomy="unattended", launch="headless")
        values = {"MODEL_ID": MODEL, "FOLDER": "/srv/projects/slugger", "TASK_ID": "slug-fix", "BENCH_MKDIR": "",
                  "RUN_DIR": "prompts/slug-fix/run", "SESSION_ID": "s-1", "PERMISSION_MODE": "acceptEdits",
                  "ALLOWED_TOOLS": "Bash(date *),Bash(mkdir *),Bash(pwd)", "EXTRA_FLAGS": ""}
        decisions = (QUICK_DECISIONS.replace("autonomy=attended; harness=claude-code; launch=interactive",
                                             "autonomy=unattended; harness=claude-code; launch=headless")
                     .replace("| D2 | Autonomy | attended | \"I'll watch it\" |",
                              "| D2 | Autonomy | unattended, headless | \"I'll start it and walk away\" |")
                     .replace("I'll watch it.", "I'll start it and walk away."))
        start = decisions.index("## Launch\n") + len("## Launch\n")
        end = decisions.index("## Placeholders")
        for size, levels in (("quick", []), ("standard", ["ERROR"])):
            with self.subTest(block_for=size):
                block = fill_block("claude-code", "launch-headless", dict(framing, size=size), values)
                self.assertEqual("for n in 1 2 3" in block, size != "quick")
                filled = decisions[:start] + "\n" + block + "\n\n" + decisions[end:]
                found = lint(quick_unattended(), framing, filled)
                self.assertEqual([f.level for f in of(found, "P40")], levels)
                if size == "quick":
                    self.assertEqual(shown(errors(found)), [])

    def test_launch_other_takes_the_generic_guide_s_headless_block(self):
        framing = dict(ALONE_FRAMING, launch="other")
        block = fill_block("generic", "launch-headless", framing, {"MODEL_ID": MODEL, "EFFORT": "high",
                                                                   "FOLDER": "/srv/projects/weather-cli",
                                                                   "TASK_ID": "config-keys-rename"})
        start = ALONE_DECISIONS.index("## Launch\n") + len("## Launch\n")
        end = ALONE_DECISIONS.index("## Placeholders")
        decisions = ALONE_DECISIONS[:start] + "\n" + block + "\n\n" + ALONE_DECISIONS[end:]
        self.assertEqual(of(lint(ALONE, framing, decisions), "P40"), [])
        found = of(lint(ALONE, framing, ALONE_DECISIONS), "P40")
        self.assertTrue(found and all(f.level == "ERROR" for f in found))

    def test_the_allowlist_flag_is_read_from_the_guide(self):
        self.assertEqual(GUIDES["claude-code"].allow_flag(), "--" + "allowed-tools")
        self.assertEqual(ALONE_DECISIONS.count("--" + "allowed-tools '"), 2)
        decisions = ALONE_DECISIONS.replace("Bash(pwd),", "Bash(pwd),Bash(env),").replace("--" + "allowed-tools '",
                                                                                         "--tools '")
        self.assertEqual(of(lint(ALONE, ALONE_FRAMING, decisions), "P42"), [])   # this guide's flag is not --tools
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, os.path.basename(SKILL))
            shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns("__pycache__"))
            guide = os.path.join(copy, "references", "harness-claude-code.md")
            write(guide, read(guide).replace("--" + "allowed-tools '{ALLOWED_TOOLS}'", "--tools '{ALLOWED_TOOLS}'"))
            self.assertEqual(lp.load_guide(copy, "claude-code").allow_flag(), "--tools")
            found = of(lp.lint_text(ALONE, ALONE_FRAMING, decisions, copy, PACKS), "P42")
            self.assertEqual([(f.level, f.match) for f in found], [("ERROR", "Bash(env)")])
            self.assertEqual(of(lp.lint_text(ALONE, ALONE_FRAMING, decisions, copy, PACKS), "P40"), [])

    def test_it_needs_the_decisions_and_the_framing(self):
        self.assertEqual([f.level for f in of(lint(STANDARD), "P40")], ["SKIPPED"])
        self.assertEqual([f.level for f in of(lint(STANDARD, decisions=STANDARD_DECISIONS, launch=None), "P40")],
                         ["SKIPPED"])
        self.assertEqual([f.level for f in of(lint(STANDARD, decisions=STANDARD_DECISIONS, harness=None), "P40")],
                         ["SKIPPED"])


class P41(unittest.TestCase):
    def test_a_run_with_seats_carries_the_fallback_paragraph_word_for_word(self):
        for name in ("good-standard", "good-lead", "good-codex", "good-generic"):
            self.assertIn(lp.FALLBACK_PARAGRAPH, FIX[name][0])
        changed = STANDARD.replace("so its review was not independent", "so its review was weaker")
        found = of(lint(changed), "P41")
        self.assertEqual([(f.level, f.allowable) for f in found], [("ERROR", False)])
        self.assertIn("changed", found[0].message)
        dropped = STANDARD.replace(lp.FALLBACK_PARAGRAPH, "")
        self.assertIn("missing", of(lint(dropped), "P41")[0].message)

    def test_a_run_that_works_alone_carries_none(self):
        self.assertFalse(of(lint(ALONE, ALONE_FRAMING), "P41"))
        found = of(lint(put(ALONE, "Method", lp.FALLBACK_PARAGRAPH), ALONE_FRAMING), "P41")
        self.assertEqual([f.level for f in found], ["ERROR"])
        self.assertEqual([f.level for f in of(lint(put(QUICK, "Scope", lp.FALLBACK_PARAGRAPH), QUICK_FRAMING), "P41")],
                         ["ERROR"])

    def test_it_needs_the_seat(self):
        self.assertEqual([f.level for f in of(lint(STANDARD, seat=None), "P41")], ["SKIPPED"])


class P44(unittest.TestCase):
    """A quick, unattended prompt keeps the quick template's unattended line: its only resume and turn-end rule."""

    UNATTENDED = dict(QUICK_FRAMING, autonomy="unattended")

    def test_the_template_writes_the_line(self):
        self.assertIn("{UNATTENDED: %s}" % lp.QUICK_UNATTENDED_LINE, read(os.path.join(SKILL, "templates",
                                                                                       "quick-prompt.md")))

    def test_a_quick_unattended_prompt_with_the_line_passes(self):
        self.assertEqual(of(lint(quick_unattended(), self.UNATTENDED), "P44"), [])

    def test_the_line_removed_errs(self):
        found = of(lint(QUICK, self.UNATTENDED), "P44")
        self.assertEqual([(f.level, f.allowable, f.line) for f in found], [("ERROR", False, None)])
        self.assertIn("missing", found[0].message)

    def test_the_line_changed_errs(self):
        text = quick_unattended().replace("reread this prompt and the files you changed", "reread this prompt")
        found = of(lint(text, self.UNATTENDED), "P44")
        self.assertEqual([f.level for f in found], ["ERROR"])
        self.assertIn("changed", found[0].message)
        self.assertEqual(found[0].line, text.split("\n").index(next(raw for raw in text.split("\n")
                                                                     if lp.QUICK_UNATTENDED_LABEL in raw)) + 1)

    def test_only_a_quick_unattended_run(self):
        self.assertEqual(of(lint(QUICK, QUICK_FRAMING), "P44"), [])                   # attended
        self.assertEqual(of(lint(ALONE, ALONE_FRAMING), "P44"), [])                   # unattended, above quick
        for missing in ("size", "autonomy"):
            with self.subTest(missing=missing):
                found = of(lint(QUICK, self.UNATTENDED, **{missing: None}), "P44")
                self.assertEqual([f.level for f in found], ["SKIPPED"])


class P04(unittest.TestCase):
    def test_the_seats_models_block(self):
        self.assertFalse(of(lint(STANDARD), "P04"))
        self.assertFalse(of(lint(QUICK, QUICK_FRAMING), "P04"))
        self.assertFalse(of(lint(ALONE, ALONE_FRAMING), "P04"))   # a run that works alone carries no section
        dropped = STANDARD.replace(fill_block("claude-code", "seats-models", STANDARD_FRAMING, {"MODEL_ID": MODEL}), "")
        self.assertNotEqual(dropped, STANDARD)
        self.assertEqual([f.level for f in of(lint(dropped), "P04")], ["ERROR"])

    def test_a_changed_block_line_is_named(self):
        changed = STANDARD.replace("which runs your exact model", "which runs a model")
        self.assertNotEqual(changed, STANDARD)
        found = of(lint(changed), "P04")
        self.assertEqual([f.level for f in found], ["ERROR"])
        self.assertIn("seats-models", found[0].message)
        self.assertIn("`model` the alias of your own model's family", found[0].message)

    def test_the_seats_models_block_in_both_model_variants_per_guide(self):
        for name, harness in (("good-standard", "claude-code"), ("good-codex", "codex"), ("good-generic", "generic")):
            text, decisions, framing = FIX[name]
            ours = fill_block(harness, "seats-models", framing, {"MODEL_ID": MODEL})
            self.assertIn(ours, text)
            other = lp.MODEL_CHOOSE if framing["model"] == MODEL else MODEL
            block = fill_block(harness, "seats-models", dict(framing, model=other), {"MODEL_ID": MODEL})
            self.assertNotEqual(block, ours)
            variant = text.replace(ours, block)
            with self.subTest(harness=harness, model=other):
                self.assertFalse(of(lint(variant, dict(framing, model=other)), "P04"))
                self.assertEqual([f.level for f in of(lint(variant, framing), "P04")], ["ERROR"])
                self.assertEqual([f.level for f in of(lint(text, dict(framing, model=other)), "P04")], ["ERROR"])
        named = fill_block("claude-code", "seats-models", STANDARD_FRAMING, {"MODEL_ID": OTHER})
        text = STANDARD.replace(fill_block("claude-code", "seats-models", STANDARD_FRAMING, {"MODEL_ID": MODEL}), named)
        self.assertEqual([f.level for f in of(lint(text), "P04")], ["ERROR"])   # {MODEL_ID} is the framing's model
        self.assertFalse(of(lint(text, model=OTHER), "P04"))

    def test_the_block_follows_the_model_not_the_launch(self):
        self.assertFalse(of(lint(CODEX, CODEX_FRAMING), "P04"))
        self.assertFalse(of(lint(CODEX, CODEX_FRAMING, launch="cloud"), "P04"))
        self.assertFalse(of(lint(CODEX, CODEX_FRAMING, launch=None), "P04"))
        self.assertFalse(of(lint(CODEX, CODEX_FRAMING, effort="default"), "P04"))
        self.assertEqual([f.level for f in of(lint(CODEX, CODEX_FRAMING, model=lp.MODEL_CHOOSE), "P04")], ["ERROR"])

    def test_the_headless_line_where_the_prompt_starts_headless_seats(self):
        values = {"MODEL_ID": MODEL, "SEAT_BUDGET_USD": "3", "RUN_DIR": "prompts/invoice-csv-export/run",
                  "BENCH_ROOT": "/srv/projects/benches/invoice-csv-export", "FOLDER": STANDARD_FRAMING["folder"]}
        for model in (MODEL, lp.MODEL_CHOOSE):
            framing = dict(STANDARD_FRAMING, model=model)
            line = fill_block("claude-code", "headless-line", framing, values)
            seats = fill_block("claude-code", "seats-models", framing, values)
            text = STANDARD.replace(fill_block("claude-code", "seats-models", STANDARD_FRAMING, values),
                                    seats + "\n\n" + line)
            with self.subTest(model=model):
                self.assertEqual(("--model <seat-model>" in line), model == lp.MODEL_CHOOSE)
                self.assertFalse(of(lint(text, framing), "P04"))
                broken = text.replace("--session-id <uuid>", "--session <uuid>")
                self.assertEqual([f.level for f in of(lint(broken, framing), "P04")], ["ERROR"])

    def test_it_needs_the_framing_and_its_guide(self):
        for override in ({"model": None}, {"seat": None}, {"harness": None}, {"harness": "cursor"}):
            with self.subTest(**override):
                self.assertEqual([f.level for f in of(lint(STANDARD, **override), "P04")], ["SKIPPED"])
        for override in ({"size": None}, {"effort": None}, {"launch": None}):
            with self.subTest(**override):
                self.assertEqual(of(lint(STANDARD, **override), "P04"), [])


class P42(unittest.TestCase):
    """What the launch lets an unattended run do: the wide permission setting only on a disposable machine the person
    confirmed, quoted; an allowlist that prints no environment, admits no git command wholesale and pushes only where
    the person allowed it."""

    WIDE_ROW = "| D3 | Permission setting | %s, in a throwaway container | \"%s\" | Interview | 2026-10-01 | live |"

    def wide(self, harness):
        return GUIDES[harness].wide_setting()

    def test_every_good_launch_passes(self):
        for name in GOOD:
            text, decisions, framing = FIX[name]
            with self.subTest(fixture=name):
                self.assertEqual(of(lint(text, framing, decisions), "P42"), [])

    def test_the_wide_setting_is_read_from_the_guide(self):
        self.assertEqual(self.wide("claude-code"), "bypass" + "Permissions")
        self.assertEqual(self.wide("codex"), "danger-" + "full-access")
        self.assertIsNone(self.wide("generic"))

    def test_a_the_wide_setting_needs_a_disposable_machine_and_the_person_s_words(self):
        for name, narrow in (("good-alone", "--permission-mode acceptEdits"), ("good-codex", "-s workspace-write")):
            text, decisions, framing = FIX[name]
            wide = self.wide(framing["harness"])
            with self.subTest(fixture=name):
                self.assertEqual(decisions.count(narrow), 2)
                widened = decisions.replace(narrow, narrow.rsplit(" ", 1)[0] + " " + wide)
                found = of(lint(text, framing, widened), "P42")
                self.assertEqual([(f.level, f.allowable) for f in found], [("ERROR", False)] * 2)
                self.assertTrue(any("machine=personal" in f.message for f in found))
                disposable = dict(framing, machine="disposable")
                self.assertEqual(len(of(lint(text, disposable, widened), "P42")), 1)
                header = "| ID | Topic | Decision | Rationale | Source | Date | Status |"
                confirmed = add_row(widened, header, self.WIDE_ROW % (wide, "it is a throwaway container, nothing on it"))
                self.assertEqual(of(lint(text, disposable, confirmed), "P42"), [])
                unquoted = add_row(widened, header, self.WIDE_ROW.replace('\"%s\"', "%s") % (wide, "confirmed"))
                self.assertEqual(len(of(lint(text, disposable, unquoted), "P42")), 1)
                gone = confirmed.replace("| 2026-10-01 | live |\n\n## The person", "| 2026-10-01 | superseded by D4 |"
                                         "\n\n## The person")
                self.assertEqual(len(of(lint(text, disposable, gone), "P42")), 1)

    def allowlist_with(self, rule):
        self.assertEqual(ALONE_DECISIONS.count("Bash(pwd),"), 2)
        return ALONE_DECISIONS.replace("Bash(pwd),", "Bash(pwd),%s," % rule)

    def test_b_no_rule_prints_the_environment(self):
        for rule in ("Bash(env)", "Bash(env *)", "Bash(printenv)", "Bash(printenv *)", "Bash(printenv CLAUDE_CODE_*)",
                     "Bash(export -p)"):
            with self.subTest(rule=rule):
                found = of(lint(ALONE, ALONE_FRAMING, self.allowlist_with(rule)), "P42")
                self.assertEqual([(f.level, f.match) for f in found], [("ERROR", rule)])
        for rule in ("Bash(printenv HOME)", "Bash(env -u X claude -p *)"):
            self.assertEqual(of(lint(ALONE, ALONE_FRAMING, self.allowlist_with(rule)), "P42"), [], rule)

    def test_b_git_one_subcommand_per_rule_and_a_push_the_person_allowed(self):
        for rule in ("Bash(git *)", "Bash(git*)", "Bash(git -C . *)", "Bash(git push *)", "Bash(git push origin *)"):
            with self.subTest(rule=rule):
                found = of(lint(ALONE, ALONE_FRAMING, self.allowlist_with(rule)), "P42")
                self.assertEqual([f.match for f in found], [rule])
        push = "Bash(git push origin config-keys)"
        decisions = self.allowlist_with(push)
        self.assertIn("allowing a push of `config-keys`", of(lint(ALONE, ALONE_FRAMING, decisions), "P42")[0].message)
        header = "| ID | Topic | Decision | Rationale | Source | Date | Status |"
        allowed = add_row(decisions, header, "| D3 | Delivery | the run may push config-keys to origin | \"push it when "
                                             "it passes\" | Stated | 2026-10-01 | live |")
        self.assertEqual(of(lint(ALONE, ALONE_FRAMING, allowed), "P42"), [])
        defaulted = allowed.replace("| Stated | 2026-10-01 | live |\n\n## The person",
                                    "| Default accepted | 2026-10-01 | live |\n\n## The person")
        self.assertEqual(len(of(lint(ALONE, ALONE_FRAMING, defaulted), "P42")), 1)

    def test_it_needs_the_decisions(self):
        self.assertEqual([f.level for f in of(lint(ALONE, ALONE_FRAMING), "P42")], ["SKIPPED"])


class P43(unittest.TestCase):
    """Where the guide's §3 says so, a command the run executes holds no shell variable outside single quotes: a
    headless run refuses what it cannot check before it runs."""

    PIPELINE = ("grep -HnE '^(model|effort):' .claude/agents/*.md \"${CLAUDE_CONFIG_DIR:-$HOME/.claude}\"/agents/*.md "
                "2>/dev/null | sed \"s|^$HOME/|\\$HOME/|\"")
    RUN_DIR = "prompts/invoice-csv-export/run"

    def test_every_good_prompt_passes(self):
        for name in GOOD:
            text, decisions, framing = FIX[name]
            with self.subTest(fixture=name):
                self.assertEqual(of(lint(text, framing, decisions), "P43"), [])

    def test_the_sentence_is_read_from_the_guide(self):
        self.assertTrue(GUIDES["claude-code"].literal_commands())
        for harness in ("codex", "generic"):
            self.assertFalse(GUIDES[harness].literal_commands(), harness)
        old = put(STANDARD, "Seats and models", "Read the agent files:\n   `%s`" % self.PIPELINE)
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, os.path.basename(SKILL))
            shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns("__pycache__"))
            guide = os.path.join(copy, "references", "harness-claude-code.md")
            write(guide, read(guide).replace(lp.LITERAL_COMMANDS[0].upper() + lp.LITERAL_COMMANDS[1:], "A command"))
            self.assertEqual(of(lp.lint_text(old, STANDARD_FRAMING, STANDARD_DECISIONS, copy, PACKS), "P43"), [])
        self.assertTrue(of(lint(old, decisions=STANDARD_DECISIONS), "P43"))

    def test_a_the_inherited_pipeline_errs(self):
        old = put(STANDARD, "Seats and models", "Read the agent files:\n   `%s`" % self.PIPELINE)
        found = of(lint(old, decisions=STANDARD_DECISIONS), "P43")
        self.assertEqual([(f.level, f.allowable, f.match) for f in found],
                         [("ERROR", False, "${CLAUDE_CONFIG_DIR:-$HOME/.claude}")])
        self.assertEqual(found[0].line, old.split("\n").index("   `%s`" % self.PIPELINE) + 1)
        self.assertIn("`$HOME`", found[0].message)          # the sed's, in double quotes; its `\$HOME` is not one

    def test_a_a_headless_line_whose_brief_path_holds_a_variable_errs(self):
        values = {"MODEL_ID": MODEL, "SEAT_BUDGET_USD": "3", "RUN_DIR": self.RUN_DIR,
                  "BENCH_ROOT": "/srv/projects/benches/invoice-csv-export"}
        for folder, expected in (("/srv/projects/billing-web", []), ("$HOME/projects/billing-web", ["$HOME"]),
                                 ("${HOME}/projects/billing-web", ["${HOME}"])):
            with self.subTest(folder=folder):
                line = fill_block("claude-code", "headless-line", STANDARD_FRAMING, dict(values, FOLDER=folder))
                text = STANDARD.replace(lp.FALLBACK_PARAGRAPH, line + "\n\n" + lp.FALLBACK_PARAGRAPH)
                found = of(lint(text, dict(STANDARD_FRAMING, folder=folder), STANDARD_DECISIONS), "P43")
                self.assertEqual([f.match for f in found], expected)
                if expected:
                    self.assertIn('< "%s/' % folder, text.split("\n")[found[0].line - 1])

    def test_a_only_where_the_guide_says_so(self):
        command = "Read the agent files:\n   `grep -Hn model \"${CODEX_HOME:-$HOME/.codex}\"/agents/*.toml`"
        text = put(CODEX, "Seats and models", command)
        self.assertEqual(of(lint(text, CODEX_FRAMING, CODEX_DECISIONS), "P43"), [])   # Codex's guide does not say it

    def test_the_variables_a_shell_would_expand(self):
        for command, expected in (("printenv HOME", []), ('cd "$HOME/x"', ["$HOME"]),
                                  ('mkdir -p "${PWD}/b"', ["${PWD}"]),
                                  ("python3 -c 'print(\"$HOME\")'", []), ("echo \\$HOME", []),
                                  ("echo \"a'$HOME'b\"", ["$HOME"]), ("echo $1 $? $(pwd)", []),
                                  ("grep -q x '$X'\\''$Y'", []), ("echo 'it'\\''s' $Z_1", ["$Z_1"]),
                                  ("cd \"/b/<seat-id>\" && claude --allowed-tools '<the seat's allowlist>' "
                                   "< \"$HOME/b\"", ["$HOME"])):
            with self.subTest(command=command):
                self.assertEqual(lp.shell_variables(command), expected)


class GitLeftToThePerson(unittest.TestCase):
    """Under Codex's workspace-write sandbox `.git` is read-only: a run whose person leaves git to themselves is told to
    commit nothing in RS2 and RS9, and the choice is an accepted default."""

    COMMIT = re.compile(r"\byou commit\b|\bcommit(?:\{? and push\}?)? what exists\b")

    @staticmethod
    def keep(text, names):
        """The template's `{NAME: …}` fragments: those named kept, every other dropped."""
        out, pos = "", 0
        while True:
            found = lp.FRAGMENT_RE.search(text, pos)
            if not found:
                return out + text[pos:]
            end = lp.fragment_end(text, found.start())
            out += text[pos:found.start()]
            if found.group(1) in names:
                inner = text[found.end():end - 1]
                out += inner[1:] if inner.startswith(" ") and out[-1:] == " " else inner
            pos = end

    def test_the_codex_workspace_write_fixture_tells_the_run_to_commit_nothing(self):
        self.assertIn("-s workspace-write", CODEX_DECISIONS)
        self.assertRegex(CODEX_DECISIONS, r"\| AD\d+ \| git left to the person")
        rules = [line for line in CODEX.split("\n") if line.startswith(("- " + lp.RS_LABELS[2], "- " + lp.RS_LABELS[9]))]
        self.assertTrue(rules, "the fixture carries RS9")
        for line in rules:
            self.assertNotRegex(line, self.COMMIT)

    def test_the_template_s_rs2_and_rs9_texts(self):
        template = read(os.path.join(SKILL, "templates", "master-prompt.md"))
        lines = [line for line in template.split("\n") if line.startswith(("- " + lp.RS_LABELS[2], "- " + lp.RS_LABELS[9]))]
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertNotRegex(self.keep(line, ("NO_GIT",)), self.COMMIT, line)
            self.assertRegex(self.keep(line, ("GIT",)), self.COMMIT, line)
        self.assertIn("you leave git to the person, and record each closed piece in the ledger with the files it changed",
                      self.keep(lines[0], ("NO_GIT",)))


class Fragments(unittest.TestCase):
    def test_the_first_space_goes_only_after_a_space_or_a_line_start(self):
        framing = {"effort": "high"}
        self.assertEqual(lp.expand_fragments("`m`{EFFORT: at `{EFFORT}` effort}.", framing)[0], "`m` at `{EFFORT}` effort.")
        self.assertEqual(lp.expand_fragments("x {EFFORT: --flag {EFFORT} }--next", framing)[0], "x --flag {EFFORT} --next")
        self.assertEqual(lp.expand_fragments("{EFFORT: A}", framing)[0], "A")
        self.assertEqual(lp.expand_fragments("x {EFFORT: --flag {EFFORT} }--next", {"effort": "default"})[0], "x --next")
        self.assertEqual(lp.expand_fragments("set.{EFFORT: Effort: {EFFORT}.}", framing)[0], "set. Effort: {EFFORT}.")

    def test_a_dropped_fragment_leaves_no_double_space(self):
        text = "it. {ATTENDED_X: a}{EFFORT: B.}"
        self.assertEqual(lp.expand_fragments("it. {MODEL: A.}{EFFORT: B.}", {"effort": "high", "model": "choose"})[0],
                         "it. B.")
        self.assertEqual(lp.expand_fragments(text, {"effort": "high"})[1], {"ATTENDED_X"})

    def test_the_shell_s_braces_and_slots_are_not_fragments(self):
        text = '"${CODEX_HOME:-$HOME/.x}" {RUN_DIR}/started {MODEL: run}'
        self.assertEqual(lp.expand_fragments(text, {"model": MODEL})[0], '"${CODEX_HOME:-$HOME/.x}" {RUN_DIR}/started run')
        self.assertEqual(lp.expand_fragments(text, {"model": "choose"})[0], '"${CODEX_HOME:-$HOME/.x}" {RUN_DIR}/started ')
        self.assertEqual(lp.expand_fragments(text, {})[1], {"MODEL"})

    def test_the_model_fragments_follow_the_framing(self):
        text = "claude{MODEL: --model {MODEL_ID}}{NO_MODEL: --agent-picks}{EFFORT: --effort {EFFORT}}"
        self.assertEqual(lp.expand_fragments(text, {"model": MODEL, "effort": "high"}),
                         ("claude --model {MODEL_ID} --effort {EFFORT}", set()))
        self.assertEqual(lp.expand_fragments(text, {"model": lp.MODEL_CHOOSE, "effort": "default"}),
                         ("claude --agent-picks", set()))
        self.assertEqual(lp.expand_fragments(text, {"model": lp.MODEL_PLACEHOLDER, "effort": "default"})[0],
                         "claude --model {MODEL_ID}")   # a named model whose id the person must supply
        self.assertEqual(lp.expand_fragments(text, {"effort": "default"})[1], {"MODEL", "NO_MODEL"})

    def test_choose_fills_no_model_slot(self):
        self.assertEqual(lp.slot_values({"model": MODEL})["MODEL_ID"], MODEL)
        self.assertNotIn("MODEL_ID", lp.slot_values({"model": lp.MODEL_CHOOSE}))
        block = lp.FrozenBlock("x", "Seats run on `{MODEL_ID}`.", {"model": lp.MODEL_CHOOSE}, lp.prompt_verbatim)
        self.assertIsNotNone(block.search("Seats run on `example-model-9`."))   # matched by shape, never by `choose`
        named = lp.FrozenBlock("x", "Seats run on `{MODEL_ID}`.", {"model": MODEL}, lp.prompt_verbatim)
        self.assertIsNone(named.search("Seats run on `example-model-9`."))

    def test_bench_fragments_follow_where_the_launch_puts_the_benches(self):
        text = "{BENCH_CLI: cli}{BENCH_OTHER: other}"
        self.assertEqual([lp.expand_fragments(text, {"launch": launch})[0] for launch in lp.ENUM_VALUES["launch"]],
                         ["cli", "cli", "other", "other"])

    def test_the_linter_knows_every_fragment_the_guides_use(self):
        for harness, guide in GUIDES.items():
            for block_id, text in guide.blocks.items():
                names = set(re.findall(r"(?<!\$)\{([A-Z][A-Z0-9_]*):", text))
                with self.subTest(harness=harness, block=block_id):
                    self.assertEqual(names - set(lp.FRAGMENT_NAMES), set())


class NoHarnessToken(unittest.TestCase):
    def test_the_linter_names_no_model_and_no_harness_token(self):
        text = read(LINTER)
        hits = [m.group(0) for regex in check_skill.MODEL_PATTERNS + check_skill.HARNESS_TOKENS
                for m in regex.finditer(check_skill.HOST_RE.sub(" ", text))]
        self.assertEqual(hits, [])


class Causes(unittest.TestCase):
    """Each cause's fixture errs on exactly the rule its cause breaks, with no warning; its good fixture is clean."""

    def run_cause(self, name):
        path = os.path.join(PROMPTS, "causes", name)
        decisions = read(path + ".decisions.md")
        found = lp.lint_text(read(path + ".md"), lp.parse_framing(decisions)[0], decisions, SKILL, PACKS)
        self.assertEqual([f.as_text() for f in found if f.level == "WARN"], [])
        return [(f.rule, branch(f)) for f in found if f.level == "ERROR"], found

    def test_c1_the_review_sentence_and_the_ledger_line_on_a_quick_prompt(self):
        self.assertEqual(self.run_cause("c1-review-sentence")[0], [("P36", "(a)"), ("P36", "(c)")])

    def test_c2_pack_blocks_on_a_size_and_with_no_record(self):
        self.assertEqual(sorted(self.run_cause("c2-unearned-block")[0]), [("P33", "(a)"), ("P33", "(d)")])

    def test_c3_the_seats_models_text_on_a_run_that_works_alone(self):
        errs, found = self.run_cause("c3-alone-ceremony")
        self.assertEqual(errs, [("P37", "(a)")])
        lines = read(os.path.join(PROMPTS, "causes", "c3-alone-ceremony.md")).split("\n")
        first = fill_block("claude-code", "seats-models", {"model": lp.MODEL_CHOOSE}, {}).split("\n")[0]
        self.assertEqual([f.line for f in found if f.rule == "P37"], [lines.index(first) + 1])

    def test_c4_autonomy_assumed(self):
        self.assertEqual(self.run_cause("c4-autonomy-assumed")[0], [("P34", "(a)")])

    def test_c5_a_wish_dropped_and_a_quality_demand_unchecked(self):
        self.assertEqual(sorted(self.run_cause("c5-wish-dropped")[0]), [("P35", "(c)"), ("P35", "(e)")])

    def test_c6_provenance_markers_in_the_delivered_prompt(self):
        errs, found = self.run_cause("c6-markers")
        lines = read(os.path.join(PROMPTS, "causes", "c6-markers.md")).split("\n")
        self.assertEqual({rule for rule, _ in errs}, {"P32"})
        self.assertEqual([f.line for f in found if f.rule == "P32"], [n for n, line in enumerate(lines, 1) if "<!--" in line])

    def test_each_cause_through_the_command_exits_1(self):
        for name in ("c1-review-sentence", "c3-alone-ceremony", "c4-autonomy-assumed", "c5-wish-dropped", "c6-markers"):
            with self.subTest(cause=name):
                path = os.path.join(PROMPTS, "causes", name)
                proc = run_py(LINTER, [path + ".md", "--decisions", path + ".decisions.md", "--json"])
                self.assertEqual((proc.returncode, json.loads(proc.stdout)["warnings"]), (1, 0), proc.stdout)


if __name__ == "__main__":
    unittest.main()
