#!/usr/bin/env python3
"""run_tests.py: the one test command.

Usage: python3 tests/run_tests.py [--skill <skill dir>] [-v]
The default --skill is the only folder under ../skills/ that holds a SKILL.md. Discovers tests/test_*.py with
unittest, prints the totals, and exits 0 only when every test passes and none is skipped; 1 otherwise; 2 when
the skill folder cannot be found. Makes no model call and needs no network: the harness is tested against a fake
CLI. Writes no bytecode. Standard library only; runs on python3 3.9 or newer.
"""
import argparse
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import support  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run every test of the skill's repository.")
    parser.add_argument("--skill")
    parser.add_argument("-v", action="store_true", dest="verbose")
    args = parser.parse_args(argv)
    skill = args.skill or support.default_skill()
    if skill is None or not os.path.isfile(os.path.join(skill, "SKILL.md")):
        sys.stderr.write("run_tests: no single skill folder under ../skills/; name it with --skill <dir>\n")
        return 2
    support.set_skill(skill)
    suite = unittest.defaultTestLoader.discover(HERE, pattern="test_*.py", top_level_dir=HERE)
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) \
        - len(result.unexpectedSuccesses)
    print("tests: %d run, %d passed, %d failed, %d errors, %d skipped"
          % (result.testsRun, passed, len(result.failures), len(result.errors), len(result.skipped)))
    ok = result.wasSuccessful() and result.testsRun > 0 and not result.skipped and not result.unexpectedSuccesses
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
