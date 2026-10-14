"""Shared paths and helpers for the tests (not a test module).

Every test reads its paths from here. run_tests.py calls set_skill(<the skill folder>) before it discovers the
tests; with no call, SKILL is the only folder under ../skills/ that holds a SKILL.md.
"""
import glob
import json
import os
import subprocess
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
TOOLS = os.path.join(ROOT, "tools")
CHECK_SKILL = os.path.join(TOOLS, "check_skill.py")
EVALS = os.path.join(ROOT, "evals")
HARNESS = os.path.join(EVALS, "harness")
FIXTURES = os.path.join(TESTS, "fixtures")
PROMPTS = os.path.join(FIXTURES, "prompts")
PACKS = os.path.join(FIXTURES, "packs")
FAKE_CLAUDE = os.path.join(FIXTURES, "fake_claude.py")
SKILL = SCRIPTS = LINTER = None


def default_skill():
    """The only folder under ROOT/skills/ that holds a SKILL.md, or None when there is none or several."""
    found = sorted(os.path.dirname(path) for path in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
    return found[0] if len(found) == 1 else None


def _on_path(*folders):
    for folder in folders:
        if folder not in sys.path:
            sys.path.insert(0, folder)


def set_skill(path):
    """Point every skill path at `path` and put its scripts on sys.path."""
    global SKILL, SCRIPTS, LINTER
    SKILL = os.path.abspath(path)
    SCRIPTS = os.path.join(SKILL, "scripts")
    LINTER = os.path.join(SCRIPTS, "lint_prompt.py")
    _on_path(SCRIPTS)


_on_path(TOOLS, HARNESS)
if default_skill():
    set_skill(default_skill())


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_json(path, value):
    write(path, json.dumps(value, indent=1, ensure_ascii=False))


def clean_env(**extra):
    """This process's environment without any CLAUDE_* or FAKE_CLAUDE_* variable, plus extra; no bytecode written."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "FAKE_CLAUDE"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update({k: v for k, v in extra.items() if v is not None})
    return env


def git_env():
    """The environment every test that runs `git commit` uses: a fixed identity and no user or system git setting
    (CI has no git identity). Such a test also passes `-c commit.gpgsign=false`."""
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "author@example.com",
                "GIT_COMMITTER_NAME": "Test Committer", "GIT_COMMITTER_EMAIL": "committer@example.com",
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
    return env


def run_py(script, args, env=None, cwd=None, timeout=120):
    return subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env if env is not None else clean_env(),
                          cwd=cwd, timeout=timeout)


def home_like(*parts):
    """A path under a home folder that names a person, built at run time so no file holds it literally."""
    return "/" + "/".join(["ho" + "me", "alice"] + list(parts))
