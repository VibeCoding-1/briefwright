"""Tests for evals/trigger-set.json: queries that should and should not invoke the skill."""
import json
import os
import re
import unittest

from support import EVALS, SKILL, read

import check_skill
import run_skill

TRIGGERS = json.loads(read(os.path.join(EVALS, "trigger-set.json")))
BRANCHES = ("branch 1: a task into a prompt for another session", "branch 2: a draft prompt completed or audited",
            "branch 3: a loop prompt for an existing artefact")
CLASSES = ("not for: doing the task now", "not for: a one-line chat or image prompt",
           "not for: this session's own approach or task list", "not for: splitting this session's work across agents",
           "not for: reviewing a diff now", "not for: a question about prompting in general")


class TriggerSet(unittest.TestCase):
    def test_schema(self):
        self.assertIsInstance(TRIGGERS, list)
        for entry in TRIGGERS:
            self.assertEqual(sorted(entry), ["note", "query", "should_trigger"], entry)
            self.assertIsInstance(entry["query"], str)
            self.assertTrue(entry["query"].strip())
            self.assertIsInstance(entry["should_trigger"], bool)
            self.assertIn(entry["note"], BRANCHES if entry["should_trigger"] else CLASSES, entry)

    def test_counts(self):
        self.assertEqual(sum(1 for e in TRIGGERS if e["should_trigger"]), 24)
        self.assertEqual(sum(1 for e in TRIGGERS if not e["should_trigger"]), 16)

    def test_no_duplicate_queries(self):
        seen = [re.sub(r"\s+", " ", e["query"].strip().lower()) for e in TRIGGERS]
        self.assertEqual(len(seen), len(set(seen)))

    def test_english_only(self):
        for entry in TRIGGERS:
            self.assertTrue(all(ord(char) < 128 for char in entry["query"]), entry["query"])

    def test_no_query_names_a_skill(self):
        name = run_skill.skill_name(SKILL)
        self.assertTrue(name)
        for entry in TRIGGERS:
            query = entry["query"]
            self.assertNotIn(name.lower(), query.lower())
            self.assertIsNone(re.search(r"(?:^|\s)/[a-z][\w-]*", query), query)   # no slash command
            self.assertIsNone(re.search(r"(?i)\bskills?\b", query), query)

    def test_no_query_names_a_model(self):
        for entry in TRIGGERS:
            for pattern in check_skill.MODEL_PATTERNS:
                self.assertIsNone(pattern.search(entry["query"]), (entry["query"], pattern.pattern))

    def test_every_branch_and_at_least_two_negatives_per_class(self):
        for branch in BRANCHES:
            self.assertGreaterEqual(sum(1 for e in TRIGGERS if e["note"] == branch), 2, branch)
        for kind in CLASSES:
            self.assertGreaterEqual(sum(1 for e in TRIGGERS if e["note"] == kind), 2, kind)

    def test_the_description_names_what_the_negatives_test(self):
        """The two exclusions the description states are among the negative classes."""
        description = check_skill.frontmatter(read(os.path.join(SKILL, "SKILL.md")))[0]["description"]
        self.assertIn("Not for doing the task now or a one-line prompt.", description)
        self.assertIn("not for: doing the task now", CLASSES)
        self.assertIn("not for: a one-line chat or image prompt", CLASSES)


if __name__ == "__main__":
    unittest.main()
