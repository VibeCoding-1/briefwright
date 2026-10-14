"""Tests for tools/check_skill.py, the skill's self-check.

Each case copies the skill into a temporary folder named as the skill, plants one fault, and expects the rule that
owns it to report it. Planted model names and harness tokens are built from pieces at run time, so no file of this
repository holds them whole.
"""
import json
import os
import shutil
import tempfile
import unittest

import support
from support import CHECK_SKILL, home_like, read, run_py, write

import check_skill as cs


def joined(*pieces):
    return "".join(pieces)


# One planted line per S16 pattern: (the line, the list it belongs to).
MODEL_PLANTS = [
    joined("Cl", "aude writes it."),
    joined("Run it on ", "op", "us."),
    joined("The id is cla", "ude-", "son", "net-4."),
    joined("Like G", "PT-", "5 did."),
    joined("Call g", "pt-", "4o here."),
    joined("A small o", "3", " run."),
    joined("The old dav", "inci model."),
    joined("Ask Ge", "mini."),
    joined("Or Ll", "ama."),
    joined("Or G", "LM-", "4."),
]
HARNESS_PLANTS = [
    joined("Cl", "aude ", "Code runs it."),
    joined("Open Chat", "GPT."),
    joined("Set CLA", "UDE_", "SETTING."),
    joined("Run cla", "ude -", "p now."),
    joined("Run co", "dex ", "exec now."),
    joined("Run np", "x ", "skills add."),
    joined("Pass --perm", "ission-mode."),
    joined("Set appr", "oval_", "policy."),
    joined("Use accept", "Edits."),
    joined("Use the Ag", "ent tool."),
    joined("Type /mo", "del."),
    joined("Read ", "CLAU", "DE.md."),
    joined("Ask Cur", "sor."),
]


class SkillCopy(unittest.TestCase):
    """A copy of the skill under test in a temporary folder of the same name."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skill = os.path.join(self.tmp, os.path.basename(support.SKILL))
        shutil.copytree(support.SKILL, self.skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def path(self, rel):
        return os.path.join(self.skill, *rel.split("/"))

    def text(self, rel):
        return read(self.path(rel))

    def edit(self, rel, old, new, count=1):
        text = self.text(rel)
        self.assertIn(old, text, rel)
        write(self.path(rel), text.replace(old, new, count))

    def append(self, rel, line):
        write(self.path(rel), self.text(rel).rstrip("\n") + "\n\n" + line + "\n")

    def check(self, *only):
        return cs.Checker(self.skill).run(set(only or cs.RULES))

    def rules(self, *only):
        return sorted({f.rule for f in self.check(*only)})

    def found(self, rule):
        return [f for f in self.check(rule) if f.rule == rule]

    def assert_finds(self, rule, words=None, count=None):
        found = self.found(rule)
        self.assertTrue(found, "%s found nothing" % rule)
        if words is not None:
            self.assertTrue(any(words in f.message for f in found), [f.as_text() for f in found])
        if count is not None:
            self.assertEqual(len(found), count, [f.as_text() for f in found])
        return found


class RealSkill(unittest.TestCase):
    def test_the_skill_passes_every_rule(self):
        proc = run_py(CHECK_SKILL, ["--skill", support.SKILL])
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, "errors: 0, warnings: 0, allowed: 0"), proc.stdout)

    def test_the_skill_folder_holds_no_cache(self):
        for folder, dirs, _ in os.walk(support.SKILL):
            self.assertNotIn("__pycache__", dirs, folder)


class Conforming(SkillCopy):
    def test_a_copy_passes_every_rule(self):
        self.assertEqual([f.as_text() for f in self.check()], [])

    def test_the_lists_are_the_design_s(self):
        self.assertEqual(len(cs.MODEL_PATTERNS), 10)
        self.assertEqual(len(cs.HARNESS_TOKENS), 13)
        self.assertEqual(cs.RULES, ("S04", "S06", "S07", "S08", "S09", "S13", "S14", "S15", "S16", "S17", "S18", "S19"))
        self.assertEqual(len(cs.GUIDE_SLOTS), 15)
        self.assertEqual(cs.HARNESS_FOLDERS, ())
        self.assertEqual(cs.GUIDE_BLOCKS, ("seats-models", "reviewer-facts", "launch-attended", "launch-headless",
                                           "launch-cloud"))
        self.assertEqual(cs.GUIDE_EXTRA_BLOCKS, {"references/harness-claude-code.md": ("headless-line",)})


class S16(SkillCopy):
    def test_a_planted_tree_holds_one_hit_of_each_list(self):
        write(self.path("references/planted.md"), "\n".join(MODEL_PLANTS + HARNESS_PLANTS) + "\n")
        found = [f for f in self.found("S16") if f.file == "references/planted.md"]
        self.assertEqual(sorted({f.line for f in found}), list(range(1, len(MODEL_PLANTS) + len(HARNESS_PLANTS) + 1)))

    def test_harness_tokens_are_allowed_in_each_harness_file(self):
        for rel in ("references/harness-claude-code.md", "references/harness-codex.md", "agents/openai.yaml"):
            with self.subTest(rel=rel):
                if not os.path.exists(self.path(rel)):
                    write(self.path(rel), "notes\n")
                self.append(rel, "\n".join(HARNESS_PLANTS[1:]))
                self.assertEqual([f.as_text() for f in self.found("S16")], [])

    def test_the_harness_name_is_refused_outside_the_harness_files(self):
        self.append("references/harness-generic.md", HARNESS_PLANTS[0])
        found = self.assert_finds("S16", "harness token", 1)
        self.assertEqual(found[0].file, "references/harness-generic.md")

    def test_a_model_name_is_refused_inside_the_harness_files_too(self):
        self.append("references/harness-codex.md", MODEL_PLANTS[1])
        found = self.assert_finds("S16", "names a model", 1)
        self.assertEqual(found[0].file, "references/harness-codex.md")

    def test_a_vendor_host_in_a_source_key_and_the_placeholders_pass(self):
        host = joined("learn.chat", "gpt.com")
        self.append("references/harness-codex.md", "- A fact [CX-X #page]\n\n| CX-X | https://%s/docs/x | 2026-10-01 |" % host)
        self.append("references/methods.md", "The model is `{MODEL_ID}`, `<model-id>` or [you fill this in: the model id].")
        self.assertEqual(self.found("S16"), [])
        named = joined("op", "us")
        self.append("references/methods.md", "See https://%s.example.dev/docs." % named)   # a host is blanked
        self.assertEqual(self.found("S16"), [])
        self.append("references/methods.md", "See https://example.dev/%s/docs." % named)   # its path is not
        self.assert_finds("S16", "names a model", 1)
        self.append("references/methods.md", "See https://%s/docs." % host)   # harness tokens read the host too
        self.assertEqual(len([f for f in self.found("S16") if "harness token" in f.message]), 2)

    def test_license_is_not_read(self):
        self.append("LICENSE", MODEL_PLANTS[0])
        self.assertEqual(self.found("S16"), [])


class S17(SkillCopy):
    def test_a_a_skill_path_that_does_not_resolve(self):
        self.append("references/methods.md", "Read `references/missing.md` and `templates/<name>.md`.")
        found = self.assert_finds("S17", "references/missing.md", 1)
        self.assertIn("(a)", found[0].message)

    def test_a_a_path_inside_a_command_and_a_link_target(self):
        self.append("references/review.md", "Run `python3 \"<this skill's directory>/scripts/nope.py\" x`.")
        self.assert_finds("S17", "scripts/nope.py", 1)
        self.edit("references/review.md", "scripts/nope.py", "scripts/lint_prompt.py")
        self.append("references/review.md", "See [the pack format](packs/README.md) and [a file](packs/none.md).")
        self.assert_finds("S17", "packs/none.md", 1)

    def test_a_wildcards_match_at_least_one_file(self):
        self.append("references/review.md", "Read `references/harness-<harness>.md`, `packs/{PACK}.md` and `templates/*`.")
        self.assertEqual(self.found("S17"), [])
        self.append("references/review.md", "And `agents/<x>.json`.")
        self.assert_finds("S17", "agents/<x>.json", 1)

    def test_b_an_outside_path_outside_the_harness_files(self):
        self.append("references/interview.md", "Look in ../other for it.")
        self.assert_finds("S17", "(b) names `../`", 1)
        for token in ("/etc/hosts", "~/notes", "$HOME/x", "${HOME}/x"):
            with self.subTest(token=token):
                self.setUp()
                self.append("references/interview.md", "Read `%s`." % token)
                self.assert_finds("S17", "(b) names an absolute path", 1)
        self.setUp()
        self.append("references/harness-codex.md", "Config lives in `~/.config-x` [skill]")
        self.assertEqual(self.found("S17"), [])

    def test_c_imports_only_the_standard_library_and_the_folder(self):
        write(self.path("scripts/helper.py"), "import json\n")
        write(self.path("scripts/extra.py"), "import os\nimport helper\nfrom collections import Counter\n")
        self.assertEqual(self.found("S17"), [])
        write(self.path("scripts/extra.py"), "import os\nimport requests\nfrom yaml import safe_load\n")
        found = self.assert_finds("S17", "(c)", 2)
        self.assertEqual(sorted(f.match for f in found), ["requests", "yaml"])
        write(self.path("scripts/extra.py"), "def broken(:\n")
        self.assert_finds("S17", "does not parse", 1)

    def test_d_a_url_only_in_a_guide_s_sources_and_notice(self):
        url = "https://" + "example.com/page"
        self.append("NOTICE", url)
        self.append("references/harness-codex.md", "| CX-Y | %s | 2026-10-01 |" % url)
        self.assertEqual(self.found("S17"), [])
        self.append("references/methods.md", "See %s." % url)
        self.assert_finds("S17", "(d)", 1)
        self.setUp()
        write(self.path("scripts/link.py"), "# %s\n" % url)
        self.assert_finds("S17", "(d)", 1)


class S18(SkillCopy):
    def test_the_name_is_only_on_its_frontmatter_line(self):
        name = cs.frontmatter(self.text("SKILL.md"))[0]["name"]
        self.append("references/interview.md", "This is the %s skill." % name.upper())
        found = self.assert_finds("S18", "names the skill", 1)
        self.assertEqual(found[0].file, "references/interview.md")
        self.setUp()
        self.append("scripts/lint_prompt.py", "# %s" % name)
        self.assert_finds("S18", count=1)
        self.setUp()
        self.append("references/interview.md", "The %sian and %s_x tokens are other words." % (name, name))
        self.assertEqual([f.match for f in self.found("S18")], [name])   # `_` is not a letter: name_x names it

    def test_openai_yaml_s_display_name_may_be_the_name(self):
        name = cs.frontmatter(self.text("SKILL.md"))[0]["name"]
        yaml = "agents/openai.yaml"
        line = next(line for line in self.text(yaml).split("\n") if line.lstrip().startswith("display_name:"))
        for value in ('"%s"' % name, name):
            with self.subTest(value=value):
                self.edit(yaml, line, "  display_name: " + value)
                self.assertEqual(self.found("S18"), [])
                self.setUp()

    def test_the_name_anywhere_else_in_openai_yaml_names_the_skill(self):
        name = cs.frontmatter(self.text("SKILL.md"))[0]["name"]
        yaml = "agents/openai.yaml"
        line = next(line for line in self.text(yaml).split("\n") if line.lstrip().startswith("display_name:"))
        self.edit(yaml, line, '  display_name: "%s helper"' % name)
        self.assertEqual([f.line for f in self.assert_finds("S18", "names the skill", 1)], [2])
        for field in ("short_description", "default_prompt"):
            with self.subTest(field=field):
                self.setUp()
                self.edit(yaml, "  %s: \"" % field, "  %s: \"Use %s to " % (field, name))
                self.assertEqual([f.file for f in self.assert_finds("S18", "names the skill", 1)], [yaml])


class S19(SkillCopy):
    def test_a_missing_block_id(self):
        self.edit("references/harness-claude-code.md", "### headless-line", "### headless")
        self.assert_finds("S19", "`### headless-line` is missing")
        self.setUp()
        self.edit("references/harness-codex.md", "### seats-models", "### seats")
        self.assert_finds("S19", "`### seats-models` is missing")
        self.setUp()
        self.edit("references/harness-generic.md", "### launch-cloud", "### launch-web")
        self.assert_finds("S19", "`### launch-cloud` is missing")

    def test_a_block_with_two_fences_or_none(self):
        self.edit("references/harness-generic.md", "### reviewer-facts\n", "### reviewer-facts\n\n```text\nmore\n```\n")
        self.assert_finds("S19", "not exactly one ```text fence", 1)

    def test_an_unsourced_line_and_an_unlisted_key(self):
        self.edit("references/harness-generic.md", "- **Keep-going command:** none [skill]", "- **Keep-going command:** none")
        self.assert_finds("S19", "does not end with a source key", 1)
        self.setUp()
        self.edit("references/harness-codex.md", "[CX-SKILLS #where-codex-loads-local-skills]", "[CX-NEW #page]")
        self.assert_finds("S19", "CX-NEW is not listed", 1)

    def test_the_headings_in_order(self):
        self.edit("references/harness-generic.md", "## 4. The launch", "## 4. Launching")
        self.assert_finds("S19", "five, in order")

    def test_slots_and_fragments_in_the_fences(self):
        self.edit("references/harness-generic.md", "prompts/{TASK_ID}/master-prompt.md as its first message",
                  "prompts/{TASK}/master-prompt.md as its first message")
        self.assert_finds("S19", "{TASK} is not one of", 1)
        self.setUp()
        self.edit("references/harness-generic.md", "{EFFORT: at `{EFFORT}` effort} by its own",
                  "{SPEED: at `{EFFORT}` effort} by its own")
        self.assert_finds("S19", "{SPEED: …} is not one the linter expands", 1)
        self.setUp()
        self.append("references/harness-generic.md", "")   # prose may name any placeholder: the check reads fences only
        self.assertIn("{INSTRUCTION_FILES}", self.text("references/harness-generic.md"))
        self.assertEqual(self.found("S19"), [])

    def test_the_generic_guide_is_required(self):
        os.remove(self.path("references/harness-generic.md"))
        self.assert_finds("S19", "missing")


class S13(SkillCopy):
    def test_the_template_is_a_pack(self):
        self.assertEqual(self.found("S13"), [])
        self.edit("packs/TEMPLATE.md", "## 4. Leave out", "## 4. Avoid")
        self.assert_finds("S13", "headings")

    def test_each_block_has_one_of_each_line_and_one_text_fence(self):
        self.edit("packs/TEMPLATE.md", "Where: <the prompt section, or a brief>", "When: again")
        found = self.found("S13")
        self.assertEqual(sorted(f.match for f in found), ["When", "Where"])
        self.setUp()
        self.edit("packs/TEMPLATE.md", "```text\n<the block", "```markdown\n<the block")
        self.assert_finds("S13", "not exactly one ```text fence", 1)

    def test_a_when_never_names_a_size_or_always_its_placeholders_removed(self):
        self.assertIn("When: <a fact of the task; never a size, a run length or \"always\">", self.text("packs/TEMPLATE.md"))
        for when in ("standard and deep prompts", "always", "every run", "long runs", "<placeholder> deep tasks"):
            with self.subTest(when=when):
                self.setUp()
                self.edit("packs/TEMPLATE.md", "When: <a fact of the task; never a size, a run length or \"always\">",
                          "When: " + when)
                self.assert_finds("S13", "a fact of the task", 1)

    def test_readme_is_not_a_pack_and_a_pack_is_read(self):
        self.append("packs/README.md", "### Not a block\nWhen: always")
        self.assertEqual(self.found("S13"), [])
        sample = read(os.path.join(support.PACKS, "sample-pack.md"))
        write(self.path("packs/sample.md"), sample)
        self.assertEqual(self.found("S13"), [])
        write(self.path("packs/sample.md"), sample.replace("When: autonomy=unattended", "When: always"))
        self.assert_finds("S13", count=1)


class S06(SkillCopy):
    def test_skill_md_s_frozen_texts(self):
        for old, new in (("Where will the run execute?**", "Where will it run?**"),
                         ("the launch, and how each seat gets its model, depend on it", "the launch depends on it"),
                         ("(d) I leave it, started another way", "(d) other"),
                         ("`helper seat: `", "`helper: `"),
                         ('/scripts/lint_prompt.py" "<folder>', '/scripts/lint.py" "<folder>'),
                         ('"start it and walk away", ', ""),
                         ("so the cold read was not cold, and say so in delivery", "and go on")):
            with self.subTest(old=old):
                self.setUp()
                self.edit("SKILL.md", old, new)
                self.assertTrue(self.found("S06"))

    def test_the_autonomy_lists_must_parse(self):
        self.edit("SKILL.md", "Words that they will watch", "Words that they will see")
        self.assert_finds("S06", "phrase lists cannot be parsed")

    def test_the_master_template_s_frozen_texts(self):
        cases = (("{SEATS_BLOCK}", "{SEATS}"),
                 ("so its review was not independent", "so it was weak"),
                 ("critic, judge or cold read as a seat", "critic as a seat"),
                 ("ask about it.}{OTHER:", "go on.}{OTHER:"), ("these pushes are authorised in advance",
                                                                             "pushes are fine"),
                 ("**Usage limits.**", "**Limits.**"), ("**Wait rule.**", "**Wait.**"), ("Goal: {GOAL}", "Goal:"),
                 ("## Progress and recoverability", "## Progress"))
        for old, new in cases:
            with self.subTest(old=old):
                self.setUp()
                self.edit("templates/master-prompt.md", old, new, count=2)
                self.assertTrue(self.found("S06"))

    def test_the_decisions_template_s_frozen_texts(self):
        cases = (("model=<model id|choose>; effort=<level|default>", "model=<model id>; effort=<level|default>"),
                 ("| D1 | Harness |", "| D1 | Model |"), ("| D2 | Autonomy |", "| D2 | Watching |"),
                 ("| Block | Pack | Task fact", "| Block | Sheet | Task fact"),
                 ("| ID | Words | Kind |", "| ID | Text | Kind |"), ("Pnn lint-allow: <reason> | at:", "Pnn allow:"),
                 ("## Launch", "## Start"))
        for old, new in cases:
            with self.subTest(old=old):
                self.setUp()
                self.edit("templates/decisions.md", old, new)
                self.assertTrue(self.found("S06"))

    def test_the_quick_template_s_frozen_texts_and_skeleton(self):
        cases = (("Work alone: dispatch no subagent.", "Work alone."), ("after two different approaches", "after two tries"),
                 ("**Evidence from commands.**", "**Evidence.**"), ("commit and push on", "commit on"),
                 ("reread this prompt and the files you changed", "reread this prompt"),
                 ("harness=<claude-code|codex|generic>; launch", "launch"), ("## Launch\n\n<!-- The harness", "## Start\n\n<!-- The"),
                 ("## Guidance put in\n\n| Block", "## Zzz\n\n| Block"))
        for old, new in cases:
            with self.subTest(old=old):
                self.setUp()
                self.edit("templates/quick-prompt.md", old, new)
                self.assertTrue(self.found("S06"), old)


class OtherRules(SkillCopy):
    def test_s04_a_backticked_path_that_does_not_exist(self):
        self.append("references/methods.md", "Read `templates/missing.md` and `scripts/*.sh`.")
        found = self.found("S04")
        self.assertEqual(sorted(f.match for f in found), ["scripts/*.sh", "templates/missing.md"])

    def test_s07_ceilings_and_skill_lines(self):
        self.append("references/review.md", "word " * 400)
        self.assert_finds("S07", "over the ceiling", 1)
        self.setUp()
        text = self.text("SKILL.md")
        write(self.path("SKILL.md"), text + "\n" * 120)
        self.assert_finds("S07", "lines, over 200", 1)

    def test_s08_frontmatter(self):
        cases = (("license: Apache-2.0\n", "license: Apache-2.0\nversion: 1\n", "not one of"),
                 ("license: Apache-2.0", "license: MIT", "license"),
                 ("Not for doing the task now", "Not for doing the work now", "frozen text"),
                 ('compatibility: "', 'compatibility: "' + "x" * 500, "compatibility"))
        for old, new, words in cases:
            with self.subTest(old=old):
                self.setUp()
                self.edit("SKILL.md", old, new)
                self.assert_finds("S08", words)
        renamed = os.path.join(self.tmp, "another-name")
        os.rename(self.skill, renamed)
        found = [f for f in cs.Checker(renamed).run({"S08"})]
        self.assertTrue(any("is not the folder's name" in f.message for f in found))

    def test_s08_the_description_is_ascii_without_angle_brackets(self):
        self.edit("SKILL.md", "a one-line prompt.", "a one-line <prompt> — here.")
        found = self.assert_finds("S08", "ASCII")
        self.assertTrue(any("over 400" in f.message for f in found))

    def test_s09_a_home_path_anywhere(self):
        self.append("scripts/lint_prompt.py", "# " + home_like("work"))
        self.assert_finds("S09", "home path", 1)

    def test_s14_a_marker(self):
        self.append("references/review.md", "<!-- " + "verbatim BP -->")
        self.assert_finds("S14", "provenance marker", 1)

    def test_s15_the_four_sentences_and_the_fused_form(self):
        self.edit("references/methods.md", "Name every problem you see", "Name the problems you see")
        self.assert_finds("S15", "the review sentence", 1)
        self.setUp()
        self.append("templates/master-prompt.md", "Put its output in the report; independent review is fine.")
        self.assert_finds("S15", "fused", 1)

    def test_a_missing_or_broken_linter_is_reported_by_the_rules_that_read_it(self):
        write(self.path("scripts/lint_prompt.py"), "raise SystemExit(3)\n")
        found = self.check()
        self.assertEqual(sorted({f.rule for f in found if "does not import" in f.message}), ["S06", "S15", "S19"])
        os.remove(self.path("scripts/lint_prompt.py"))
        self.assertTrue(any("does not import" in f.message for f in self.check("S06")))


class Cli(SkillCopy):
    def test_usage_and_only(self):
        self.assertEqual(run_py(CHECK_SKILL, ["--skill", self.skill, "--only", "S99"]).returncode, 2)
        self.assertEqual(run_py(CHECK_SKILL, ["--skill", os.path.join(self.tmp, "nowhere")]).returncode, 2)
        self.append("references/review.md", "<!-- " + "verbatim BP -->")
        proc = run_py(CHECK_SKILL, ["--skill", self.skill, "--only", "S14"])
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, r"(?m)^S14 ERROR line \d+: references/review.md: a provenance marker ")
        self.assertEqual(proc.stdout.strip().split("\n")[-1], "errors: 1, warnings: 0, allowed: 0")
        self.assertEqual(run_py(CHECK_SKILL, ["--skill", self.skill, "--only", "S16,S17"]).returncode, 0)

    def test_json_shape(self):
        self.append("references/review.md", "<!-- " + "verbatim BP -->")
        data = json.loads(run_py(CHECK_SKILL, ["--skill", self.skill, "--json"]).stdout)
        self.assertEqual(sorted(data), ["allowed", "errors", "findings", "skill", "warnings"])
        self.assertEqual(sorted(data["findings"][0]), ["file", "level", "line", "match", "message", "reason", "rule"])
        self.assertEqual(data["errors"], 1)

    def test_the_default_skill_is_the_only_one_under_skills(self):
        root = os.path.join(self.tmp, "root")
        os.makedirs(os.path.join(root, "tools"))
        shutil.copy(CHECK_SKILL, os.path.join(root, "tools", "check_skill.py"))
        script = os.path.join(root, "tools", "check_skill.py")
        self.assertEqual(run_py(script, []).returncode, 2)
        shutil.copytree(self.skill, os.path.join(root, "skills", os.path.basename(self.skill)))
        proc = run_py(script, [])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        shutil.copytree(self.skill, os.path.join(root, "skills", "second"))
        proc = run_py(script, [])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--skill", proc.stderr)

    def test_the_check_leaves_no_cache_in_the_skill(self):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
        self.assertEqual(run_py(CHECK_SKILL, ["--skill", self.skill], env=env).returncode, 0)
        for folder, dirs, _ in os.walk(self.skill):
            self.assertNotIn("__pycache__", dirs, folder)


if __name__ == "__main__":
    unittest.main()
