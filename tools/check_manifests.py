#!/usr/bin/env python3
"""Check the plugin and marketplace manifests against each other, the skill and the changelog.

Usage: python3 tools/check_manifests.py [--root <dir>] [--skill <dir>]

<root> defaults to the folder above tools/. Two layouts are read:
- published: plugin.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json and
  .agents/plugins/marketplace.json, with the plugin named as the skill's frontmatter names it;
- staged: the same four files under packaging/ as plugin.json, claude-plugin.plugin.json,
  claude-plugin.marketplace.json and agents-plugins.marketplace.json, where the plugin name is still the
  release placeholder. The staged layout has no skills/ folder, so it needs --skill.
<skill> defaults to the only folder under <root>/skills/ that holds a SKILL.md.

Checks: every JSON file parses, with no duplicate key; every plugin name is the expected one; both
marketplaces carry the one marketplace name; the version is the same in the three manifests that carry one
and in the top versioned CHANGELOG.md entry; plugin.json has the Agent Plugins 1.0.0 $schema and only
the fields that schema allows; each manifest has its required fields; the two plugin manifests carry the
same keywords, if any, each a lowercase hyphenated tag, none repeated; the skill's agents/openai.yaml allows
implicit invocation, has its short description, and keeps each interface string it has within the length
Codex keeps (a longer one is dropped with a warning). Exit 0 clean, 1 findings, 2 usage. Standard library
only; Python 3.9 or newer.
"""
import argparse
import json
import os
import re
import sys

SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
SCHEMA_FIELDS = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
                 "keywords", "extensions"}
NAME_RULE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
KEYWORD_RULE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The interface strings of agents/openai.yaml, the most characters Codex keeps of each, counted after it folds
# runs of whitespace into one space (codex-rs/skills/src/interface.rs at rust-v0.160.0), and whether one is required.
INTERFACE = (("display_name", 64, False), ("short_description", 1024, True), ("default_prompt", 1024, False))
MARKETPLACE = "vibecoding-1"
PLACEHOLDER = "{{" + "SKILL_NAME" + "}}"

# Each manifest: its published path, its staged name under packaging/, and the fields it must carry (a dotted
# path; "plugins[]." applies to every entry). The Claude Code files also carry what the plugin validator's
# strict mode fails without: the plugin's version, description and author, the marketplace's description.
MANIFESTS = (
    ("plugin.json", "plugin.json", ("$schema", "name")),
    (".claude-plugin/plugin.json", "claude-plugin.plugin.json", ("name", "version", "description", "author.name")),
    (".claude-plugin/marketplace.json", "claude-plugin.marketplace.json",
     ("name", "description", "owner.name", "plugins[].name", "plugins[].source")),
    (".agents/plugins/marketplace.json", "agents-plugins.marketplace.json",
     ("name", "plugins[].name", "plugins[].source")),
)


class Usage(Exception):
    pass


def no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ValueError("duplicate key %s" % ", ".join(duplicates))
    return dict(pairs)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=no_duplicates)


def get(value, dotted):
    """The values at a dotted path; `plugins[]` fans out over a list. A missing step yields nothing."""
    values = [value]
    for step in dotted.split("."):
        fan = step.endswith("[]")
        step = step[:-2] if fan else step
        found = []
        for item in values:
            if isinstance(item, dict) and step in item:
                child = item[step]
                if fan:
                    found.extend(child if isinstance(child, list) else [])
                else:
                    found.append(child)
        values = found
    return values


def frontmatter_name(skill):
    path = os.path.join(skill, "SKILL.md")
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^name:\s*(.*?)\s*$", line)
        if match:
            return match.group(1).strip("\"'")
    return None


def two_level_yaml(path):
    """The `section.key` values of a two-level YAML mapping, as plain strings."""
    values, section = {}, None
    with open(path, encoding="utf-8") as handle:
        for line in handle.read().split("\n"):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            top = re.match(r"^([A-Za-z_][\w-]*):\s*$", line)
            child = re.match(r"^  ([A-Za-z_][\w-]*):\s*(.*?)\s*$", line)
            if top:
                section = top.group(1)
            elif child and section:
                value = child.group(2)
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[section + "." + child.group(1)] = value
    return values


def changelog_version(root):
    path = os.path.join(root, "CHANGELOG.md")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^## \[([^\]]+)\]", line)
            if match and match.group(1).lower() != "unreleased":
                return match.group(1)
    return None


def json_files(*folders):
    seen = []
    for folder in folders:
        for here, dirs, files in os.walk(folder):
            dirs[:] = sorted(d for d in dirs if d != ".git")
            for name in sorted(files):
                path = os.path.realpath(os.path.join(here, name))
                if name.endswith(".json") and path not in seen:
                    seen.append(path)
    return seen


def resolve(root, skill):
    staged = os.path.isdir(os.path.join(root, "packaging"))
    published = any(os.path.exists(os.path.join(root, public)) for public, _, _ in MANIFESTS)
    if staged and published:
        raise Usage("both layouts at once: packaging/ beside published manifests in %s" % root)
    if not staged and not published:
        raise Usage("no manifests in %s (neither packaging/ nor the published paths)" % root)
    if skill is None:
        if staged:
            raise Usage("the staged layout has no skills/ folder: pass --skill")
        found = sorted(os.path.join(root, "skills", name) for name in os.listdir(os.path.join(root, "skills"))
                       if os.path.isfile(os.path.join(root, "skills", name, "SKILL.md"))) \
            if os.path.isdir(os.path.join(root, "skills")) else []
        if len(found) != 1:
            raise Usage("%d skill folders under %s/skills: pass --skill" % (len(found), root))
        skill = found[0]
    if not os.path.isfile(os.path.join(skill, "SKILL.md")):
        raise Usage("no SKILL.md in --skill %s" % skill)
    return ("staged" if staged else "published"), skill


def check(root, skill, layout):
    findings = []
    def find(where, message):
        findings.append("%s: %s" % (where, message))

    parsed = {}
    for path in json_files(root, skill):
        try:
            parsed[path] = load_json(path)
        except (ValueError, UnicodeDecodeError) as error:
            find(os.path.relpath(path, root), "does not parse: %s" % error)

    expected = PLACEHOLDER if layout == "staged" else frontmatter_name(skill)
    if not expected:
        find(os.path.relpath(os.path.join(skill, "SKILL.md"), root), "no frontmatter name")
    manifests = {}
    for public, staged, required in MANIFESTS:
        label = public if layout == "published" else "packaging/" + staged
        path = os.path.realpath(os.path.join(root, label))
        if not os.path.isfile(path):
            find(label, "missing")
            continue
        if path not in parsed:
            continue
        data = manifests[public] = parsed[path]
        if not isinstance(data, dict):
            find(label, "is not a JSON object")
            continue
        for field in required:
            values = get(data, field)
            if not values or any(value in (None, "", [], {}) for value in values):
                find(label, "required field %s is missing or empty" % field)
        names = [data.get("name")] if "plugins" not in data else get(data, "plugins[].name")
        if "plugins" in data:
            if not isinstance(data["plugins"], list) or len(data["plugins"]) != 1:
                find(label, "lists %s plugins, not exactly one" % (
                    len(data["plugins"]) if isinstance(data["plugins"], list) else "no list of"))
            if data.get("name") != MARKETPLACE:
                find(label, "marketplace name is %r, not %r" % (data.get("name"), MARKETPLACE))
        for name in names:
            if expected and name != expected:
                find(label, "plugin name is %r, not %r" % (name, expected))
    if "plugin.json" in manifests and isinstance(manifests["plugin.json"], dict):
        data = manifests["plugin.json"]
        label = "plugin.json" if layout == "published" else "packaging/plugin.json"
        if data.get("$schema") != SCHEMA:
            find(label, "$schema is %r, not %r" % (data.get("$schema"), SCHEMA))
        for field in sorted(set(data) - SCHEMA_FIELDS):
            find(label, "field %r is not allowed by the Agent Plugins 1.0.0 schema" % field)
        if layout == "published" and isinstance(data.get("name"), str) and not NAME_RULE.match(data["name"]):
            find(label, "name %r breaks the Agent Plugins name rule" % data["name"])

    labels = {public: public if layout == "published" else "packaging/" + staged for public, staged, _ in MANIFESTS}
    keywords = {}
    for public in ("plugin.json", ".claude-plugin/plugin.json"):
        data, label = manifests.get(public), labels[public]
        if not isinstance(data, dict):
            continue
        value = data.get("keywords", [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            find(label, "keywords is not a list of strings")
            continue
        for item in value:
            if not KEYWORD_RULE.match(item):
                find(label, "keyword %r is not a lowercase hyphenated tag" % item)
        for item in sorted({item for item in value if value.count(item) > 1}):
            find(label, "keyword %r is repeated" % item)
        keywords[public] = value
    if len(keywords) == 2 and keywords["plugin.json"] != keywords[".claude-plugin/plugin.json"]:
        find("keywords", "differ between plugin.json and .claude-plugin/plugin.json")

    versions = {}
    for public, field in (("plugin.json", "version"), (".claude-plugin/plugin.json", "version"),
                          (".claude-plugin/marketplace.json", "plugins[].version")):
        if isinstance(manifests.get(public), dict):
            for value in get(manifests[public], field) or [None]:
                versions["%s %s" % (public, field)] = value
    try:
        versions["CHANGELOG.md top entry"] = changelog_version(root)
    except OSError:
        find("CHANGELOG.md", "missing")
    if len(set(versions.values())) > 1 or None in versions.values():
        find("versions", "differ: " + ", ".join("%s=%s" % item for item in sorted(versions.items())))

    yaml_path = os.path.join(skill, "agents", "openai.yaml")
    if not os.path.isfile(yaml_path):
        find(os.path.relpath(yaml_path, root), "missing")
    else:
        values, label = two_level_yaml(yaml_path), os.path.relpath(yaml_path, root)
        for key, most, required in INTERFACE:
            value = " ".join(values.get("interface." + key, "").split())
            if not value and (required or "interface." + key in values):
                find(label, "interface.%s is %s" % (key, "missing or empty" if required else "empty"))
            elif len(value) > most:
                find(label, "interface.%s is %d characters, over the %d Codex keeps" % (key, len(value), most))
        if values.get("policy.allow_implicit_invocation") != "true":
            find(label, "policy.allow_implicit_invocation is not true")
    return findings, len(parsed)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the plugin and marketplace manifests.")
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--root", default=os.path.dirname(here), help="the repository root (default: above tools/)")
    parser.add_argument("--skill", help="the skill folder (default: the only skills/*/SKILL.md)")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    try:
        if not os.path.isdir(root):
            raise Usage("--root is not a folder: %s" % root)
        layout, skill = resolve(root, os.path.abspath(args.skill) if args.skill else None)
    except Usage as error:
        print("check_manifests: %s" % error, file=sys.stderr)
        return 2
    findings, parsed = check(root, skill, layout)
    for finding in findings:
        print(finding)
    if findings:
        print("check_manifests: %d finding(s) (%s layout)" % (len(findings), layout))
        return 1
    print("check_manifests: clean (%s layout, %d JSON file(s) parsed)" % (layout, parsed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
