"""The skill folder stands alone: copied by itself into an empty folder, it passes its self-check and lints a prompt."""
import json
import os
import shutil
import tempfile
import unittest

from support import CHECK_SKILL, PROMPTS, SKILL, clean_env, read, run_py

import check_skill

SKILL_MD_MAX_LINES = 500


class LoneCopy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        fields, _ = check_skill.frontmatter(read(os.path.join(SKILL, "SKILL.md")))
        cls.copy = os.path.join(cls.tmp, fields["name"])
        shutil.copytree(SKILL, cls.copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_the_copy_is_alone(self):
        self.assertEqual(os.listdir(self.tmp), [os.path.basename(self.copy)])

    def test_the_self_check_passes_on_the_copy(self):
        proc = run_py(CHECK_SKILL, ["--skill", self.copy, "--json"], env=clean_env())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual((result["errors"], result["warnings"]), (0, 0), result["findings"])

    def test_the_copy_s_linter_lints_a_prompt(self):
        proc = run_py(os.path.join(self.copy, "scripts", "lint_prompt.py"),
                      [os.path.join(PROMPTS, "good-standard.md"), "--decisions",
                       os.path.join(PROMPTS, "good-standard.decisions.md"), "--json"], env=clean_env())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["errors"], 0)

    def test_running_the_copy_leaves_no_bytecode(self):
        """Without PYTHONDONTWRITEBYTECODE, which every other run here sets: the scripts themselves write no cache."""
        env = clean_env()
        del env["PYTHONDONTWRITEBYTECODE"]
        for script, args in ((CHECK_SKILL, ["--skill", self.copy]),
                             (os.path.join(self.copy, "scripts", "lint_prompt.py"),
                              [os.path.join(PROMPTS, "good-standard.md"), "--decisions",
                               os.path.join(PROMPTS, "good-standard.decisions.md")])):
            proc = run_py(script, args, env=env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        left = [os.path.join(folder, name) for folder, dirs, files in os.walk(self.copy) for name in dirs + files
                if name == "__pycache__" or name.endswith(".pyc")]
        self.assertEqual(left, [])

    def test_skill_md_is_at_most_500_lines(self):
        lines = read(os.path.join(self.copy, "SKILL.md")).split("\n")
        self.assertLessEqual(len(lines), SKILL_MD_MAX_LINES)


if __name__ == "__main__":
    unittest.main()
