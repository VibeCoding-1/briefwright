"""tools/check_manifests.py: both layouts pass when consistent, and each broken rule is named.

The fixture trees are written at run time; the release placeholder is built from pieces.
"""
import copy
import json
import os
import shutil
import tempfile
import unittest

import support

import check_manifests

CHECKER = os.path.join(support.TOOLS, "check_manifests.py")
PLACEHOLDER = "{{" + "SKILL_NAME" + "}}"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PUBLISHED = {
    "plugin.json": "plugin.json",
    "claude": ".claude-plugin/plugin.json",
    "claude-market": ".claude-plugin/marketplace.json",
    "agents-market": ".agents/plugins/marketplace.json",
}
STAGED = {
    "plugin.json": "packaging/plugin.json",
    "claude": "packaging/claude-plugin.plugin.json",
    "claude-market": "packaging/claude-plugin.marketplace.json",
    "agents-market": "packaging/agents-plugins.marketplace.json",
}


def manifests(name):
    about = "Turns a task into something useful."
    keywords = ["agent-skills", "example-tag"]
    return {
        "plugin.json": {"$schema": SCHEMA, "name": name, "version": "1.0.0", "description": about,
                        "license": "Apache-2.0", "keywords": list(keywords)},
        "claude": {"name": name, "version": "1.0.0", "description": about, "author": {"name": "Example Org"},
                   "license": "Apache-2.0", "keywords": list(keywords)},
        "claude-market": {"name": "vibecoding-1", "description": "Example Org's plugins.",
                          "owner": {"name": "Example Org"},
                          "plugins": [{"name": name, "source": "./", "description": about, "version": "1.0.0"}]},
        "agents-market": {"name": "vibecoding-1",
                          "plugins": [{"name": name, "source": "./",
                                       "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}}]},
    }


OPENAI_YAML = ("interface:\n  display_name: \"One Thing\"\n  short_description: \"Does one thing well\"\n"
               "  default_prompt: \"Do the one thing for this task.\"\n\n"
               "policy:\n  allow_implicit_invocation: true\n")


class ManifestCase(unittest.TestCase):
    def folder(self):
        path = tempfile.mkdtemp(prefix="manifests-")
        self.addCleanup(shutil.rmtree, path)
        return path

    def skill(self, folder, name):
        support.write(os.path.join(folder, "SKILL.md"),
                      "---\nname: %s\ndescription: Does one thing.\n---\n\n# Body\n" % name)
        support.write(os.path.join(folder, "agents", "openai.yaml"), OPENAI_YAML)

    def published(self, name="example-skill", edit=None):
        root = self.folder()
        self.skill(os.path.join(root, "skills", name), name)
        data = manifests(name)
        if edit:
            edit(data)
        for key, path in PUBLISHED.items():
            support.write(os.path.join(root, path), json.dumps(data[key], indent=2))
        support.write(os.path.join(root, "CHANGELOG.md"), "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n")
        return root, []

    def staged(self, edit=None):
        root, skill = self.folder(), self.folder()
        self.skill(skill, "local-name")
        data = manifests(PLACEHOLDER)
        if edit:
            edit(data)
        for key, path in STAGED.items():
            support.write(os.path.join(root, path), json.dumps(data[key], indent=2))
        support.write(os.path.join(root, "CHANGELOG.md"), "## [1.0.0] - " + "{{" + "RELEASE_DATE" + "}}\n")
        return root, ["--skill", skill]

    def check(self, root, extra):
        return support.run_py(CHECKER, ["--root", root] + extra)

    def assertFinding(self, result, text):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(text, result.stdout)


class Clean(ManifestCase):
    def test_a_consistent_published_tree_passes(self):
        result = self.check(*self.published())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clean (published layout", result.stdout)

    def test_a_consistent_staged_tree_passes(self):
        result = self.check(*self.staged())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clean (staged layout", result.stdout)

    def test_this_repository_manifests_pass(self):
        result = support.run_py(CHECKER, ["--root", support.ROOT, "--skill", support.SKILL])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_this_repository_manifests_carry_keywords_and_codex_s_display_name_and_prompt(self):
        """Optional to the formats and the check, kept here for discovery: the plugin manifests' keywords, and
        the name and starting prompt Codex shows for the skill."""
        layout, skill = check_manifests.resolve(support.ROOT, support.SKILL)
        for public, staged, _ in check_manifests.MANIFESTS[:2]:
            path = os.path.join(support.ROOT, public if layout == "published" else os.path.join("packaging", staged))
            self.assertTrue(check_manifests.load_json(path).get("keywords"), path)
        values = check_manifests.two_level_yaml(os.path.join(skill, "agents", "openai.yaml"))
        for key in ("display_name", "default_prompt"):
            self.assertTrue(values.get("interface." + key), key)


class Findings(ManifestCase):
    def test_json_that_does_not_parse(self):
        root, extra = self.published()
        support.write(os.path.join(root, "evals", "tasks.json"), "{\"a\": 1,}")
        self.assertFinding(self.check(root, extra), "evals/tasks.json: does not parse")

    def test_a_duplicate_key(self):
        root, extra = self.published()
        support.write(os.path.join(root, "plugin.json"),
                      "{\"$schema\": \"%s\", \"name\": \"example-skill\", \"name\": \"other\"}" % SCHEMA)
        self.assertFinding(self.check(root, extra), "duplicate key name")

    def test_a_wrong_plugin_name_in_each_manifest(self):
        for key in PUBLISHED:
            def edit(data, key=key):
                target = data[key]["plugins"][0] if "plugins" in data[key] else data[key]
                target["name"] = "other-skill"
            for layout in (self.published, self.staged):
                with self.subTest(manifest=key, layout=layout.__name__):
                    self.assertFinding(self.check(*layout(edit=edit)), "plugin name is 'other-skill'")

    def test_the_staged_layout_keeps_the_placeholder(self):
        def edit(data):
            data["plugin.json"]["name"] = "example-skill"
        self.assertFinding(self.check(*self.staged(edit=edit)), "plugin name is 'example-skill'")

    def test_a_wrong_marketplace_name(self):
        for key in ("claude-market", "agents-market"):
            def edit(data, key=key):
                data[key]["name"] = "example-skill"
            with self.subTest(manifest=key):
                self.assertFinding(self.check(*self.published(edit=edit)), "marketplace name is 'example-skill'")

    def test_a_marketplace_with_two_plugins(self):
        def edit(data):
            data["agents-market"]["plugins"].append(copy.deepcopy(data["agents-market"]["plugins"][0]))
        self.assertFinding(self.check(*self.published(edit=edit)), "not exactly one")

    def test_versions_that_differ(self):
        edits = {
            "plugin.json": lambda data: data["plugin.json"].update(version="1.0.1"),
            "claude": lambda data: data["claude"].update(version="1.0.1"),
            "claude-market": lambda data: data["claude-market"]["plugins"][0].update(version="1.0.1"),
        }
        for key, edit in edits.items():
            with self.subTest(manifest=key):
                self.assertFinding(self.check(*self.published(edit=edit)), "versions: differ")
        root, extra = self.published()
        support.write(os.path.join(root, "CHANGELOG.md"), "## [1.1.0] - 2026-02-01\n\n## [1.0.0] - 2026-01-01\n")
        self.assertFinding(self.check(root, extra), "versions: differ")

    def test_the_schema_uri_and_its_fields(self):
        def other_schema(data):
            data["plugin.json"]["$schema"] = SCHEMA.replace("1.0.0", "1.1.0")
        self.assertFinding(self.check(*self.published(edit=other_schema)), "$schema is")

        def extra_field(data):
            data["plugin.json"]["category"] = "Productivity"
        self.assertFinding(self.check(*self.published(edit=extra_field)),
                           "field 'category' is not allowed by the Agent Plugins 1.0.0 schema")

    def test_the_name_rule_when_published(self):
        result = self.check(*self.published(name="bad--name"))
        self.assertFinding(result, "breaks the Agent Plugins name rule")

    def test_each_required_field(self):
        cases = (
            ("plugin.json", "$schema", lambda data: data["plugin.json"].pop("$schema")),
            ("plugin.json", "name", lambda data: data["plugin.json"].pop("name")),
            ("claude", "version", lambda data: data["claude"].pop("version")),
            ("claude", "description", lambda data: data["claude"].pop("description")),
            ("claude", "author.name", lambda data: data["claude"].pop("author")),
            ("claude-market", "description", lambda data: data["claude-market"].pop("description")),
            ("claude-market", "owner.name", lambda data: data["claude-market"].pop("owner")),
            ("claude-market", "plugins[].source", lambda data: data["claude-market"]["plugins"][0].pop("source")),
            ("agents-market", "plugins[].name", lambda data: data["agents-market"]["plugins"][0].pop("name")),
            ("agents-market", "plugins[].source", lambda data: data["agents-market"]["plugins"][0].pop("source")),
        )
        for key, field, edit in cases:
            with self.subTest(manifest=key, field=field):
                result = self.check(*self.published(edit=edit))
                self.assertFinding(result, "%s: required field %s is missing" % (PUBLISHED[key], field))

    def test_the_keywords(self):
        cases = (
            (lambda data: data["claude"]["keywords"].append("more"), "keywords: differ between plugin.json and"),
            (lambda data: data["plugin.json"].pop("keywords"), "keywords: differ between plugin.json and"),
            (lambda data: data["plugin.json"]["keywords"].append("Agent Skills"),
             "plugin.json: keyword 'Agent Skills' is not a lowercase hyphenated tag"),
            (lambda data: data["claude"]["keywords"].append("agent-skills"),
             ".claude-plugin/plugin.json: keyword 'agent-skills' is repeated"),
            (lambda data: data["plugin.json"].update(keywords="agent-skills"),
             "plugin.json: keywords is not a list of strings"),
        )
        for edit, message in cases:
            with self.subTest(message=message):
                self.assertFinding(self.check(*self.published(edit=edit)), message)

        def neither(data):
            data["plugin.json"].pop("keywords")
            data["claude"].pop("keywords")
        self.assertEqual(self.check(*self.published(edit=neither)).returncode, 0)

        def staged_edit(data):
            data["plugin.json"]["keywords"] = ["other"]
        self.assertFinding(self.check(*self.staged(edit=staged_edit)), "keywords: differ")

    def test_a_missing_manifest(self):
        root, extra = self.published()
        os.remove(os.path.join(root, ".agents", "plugins", "marketplace.json"))
        self.assertFinding(self.check(root, extra), ".agents/plugins/marketplace.json: missing")

    def test_openai_yaml_keeps_its_keys_within_what_codex_keeps(self):
        def without(key):
            return "".join(line + "\n" for line in OPENAI_YAML.split("\n")[:-1] if not line.startswith("  %s:" % key))

        def with_value(key, value):
            return without(key).replace("interface:\n", "interface:\n  %s: \"%s\"\n" % (key, value), 1)

        cases = (
            (with_value("short_description", ""), "interface.short_description is missing or empty"),
            (without("short_description"), "interface.short_description is missing or empty"),
            (with_value("display_name", ""), "interface.display_name is empty"),
            (with_value("default_prompt", "   "), "interface.default_prompt is empty"),
            (with_value("display_name", "x" * 65),
             "interface.display_name is 65 characters, over the 64 Codex keeps"),
            (with_value("default_prompt", "x" * 1025),
             "interface.default_prompt is 1025 characters, over the 1024 Codex keeps"),
            (OPENAI_YAML.replace("allow_implicit_invocation: true", "allow_implicit_invocation: false"),
             "policy.allow_implicit_invocation is not true"),
        )
        for text, message in cases:
            with self.subTest(message=message):
                root, extra = self.published()
                support.write(os.path.join(root, "skills", "example-skill", "agents", "openai.yaml"), text)
                self.assertFinding(self.check(root, extra), message)
        short_only = "".join(line + "\n" for line in without("display_name").split("\n")[:-1]
                             if not line.startswith("  default_prompt:"))
        # Codex folds runs of whitespace before it counts, and needs neither the name nor the prompt.
        for text in (with_value("display_name", " ".join(["x" * 31, "  ", "x" * 32])), short_only):
            with self.subTest(text=text):
                root, extra = self.published()
                support.write(os.path.join(root, "skills", "example-skill", "agents", "openai.yaml"), text)
                self.assertEqual(self.check(root, extra).returncode, 0)
        root, extra = self.published()
        os.remove(os.path.join(root, "skills", "example-skill", "agents", "openai.yaml"))
        self.assertFinding(self.check(root, extra), "agents/openai.yaml: missing")


class Usage(ManifestCase):
    def test_the_staged_layout_needs_the_skill(self):
        root, _ = self.staged()
        result = self.check(root, [])
        self.assertEqual(result.returncode, 2)
        self.assertIn("--skill", result.stderr)

    def test_two_skill_folders_need_the_skill(self):
        root, _ = self.published()
        self.skill(os.path.join(root, "skills", "second-skill"), "second-skill")
        self.assertEqual(self.check(root, []).returncode, 2)

    def test_both_layouts_at_once(self):
        root, extra = self.published()
        support.write(os.path.join(root, "packaging", "plugin.json"), "{}")
        self.assertEqual(self.check(root, extra).returncode, 2)

    def test_no_manifests(self):
        self.assertEqual(self.check(self.folder(), []).returncode, 2)


if __name__ == "__main__":
    unittest.main()
