"""tools/release_notes.py: the notes cut from the real CHANGELOG.md, and from planted ones, and each refusal."""
import os
import shutil
import tempfile
import unittest

import support

import check_manifests
import release_notes

SCRIPT = os.path.join(support.TOOLS, "release_notes.py")
CHANGELOG = os.path.join(support.ROOT, "CHANGELOG.md")
PLANTED = """# Changelog

Every notable change is recorded here.

## [Unreleased]

- Not released yet.

## [1.10.0] - 2027-03-01

### Added

- The tenth minor release.

## [1.1.0] - 2027-02-01

### Fixed

- A fix, with a [reference link][guide].

[guide]: https://example.com/guide

## [1.0.0]

The first release.

[Unreleased]: https://example.com/compare/v1.10.0...HEAD
[1.10.0]: https://example.com/releases/tag/v1.10.0
[1.1.0]: https://example.com/releases/tag/v1.1.0
[1.0.0]: https://example.com/releases/tag/v1.0.0
"""


def sections_of(text):
    """The version headings of a changelog, in order, as release_notes reads them."""
    return [line.split("]")[0][4:] for line in text.split("\n") if line.startswith("## [")]


class Notes(unittest.TestCase):
    def test_each_version_gets_its_own_section_and_no_other(self):
        self.assertEqual(release_notes.notes(PLANTED, "1.10.0"), "### Added\n\n- The tenth minor release.\n")
        self.assertEqual(release_notes.notes(PLANTED, "1.1.0"),
                         "### Fixed\n\n- A fix, with a [reference link][guide].\n\n[guide]: https://example.com/guide\n")
        self.assertEqual(release_notes.notes(PLANTED, "1.0.0"), "The first release.\n")

    def test_a_tag_names_its_version_with_or_without_the_v(self):
        self.assertEqual(release_notes.version_of("v1.1.0"), "1.1.0")
        self.assertEqual(release_notes.version_of("1.1.0"), "1.1.0")
        self.assertEqual(release_notes.version_of("v2.0.0-rc.1"), "2.0.0-rc.1")
        for tag in ("latest", "Unreleased", "v", "", "vv1.0.0", "v1.0.0 ", "1.0.0/../x"):
            with self.subTest(tag=tag):
                with self.assertRaises(release_notes.Usage):
                    release_notes.version_of(tag)

    def test_line_endings_from_another_platform(self):
        text = PLANTED.replace("\n", "\r\n")
        self.assertEqual(release_notes.notes(text, "1.0.0"), "The first release.\n")

    def test_a_missing_doubled_or_empty_section_is_refused(self):
        doubled = PLANTED.replace("## [1.0.0]\n", "## [1.1.0]\n")
        empty = PLANTED.replace("The first release.\n", "")
        for text, version, reason in ((PLANTED, "2.0.0", "no section for 2.0.0"),
                                      (PLANTED, "1.10", "no section for 1.10,"),
                                      (PLANTED, "1.1", "no section for 1.1,"),
                                      (doubled, "1.1.0", "two sections for 1.1.0, at lines 15 and 23"),
                                      (empty, "1.0.0", "the section for 1.0.0 is empty"),
                                      ("# Changelog\n", "1.0.0", "the headings found: none")):
            with self.subTest(version=version, reason=reason):
                with self.assertRaises(release_notes.NoNotes) as caught:
                    release_notes.notes(text, version)
                self.assertIn(reason, str(caught.exception))

    def test_only_a_level_one_or_two_heading_ends_a_section(self):
        text = "## [1.0.0]\n\n### Added\n\n#### Detail\n\n- One.\n# Elsewhere\n\n- Not this.\n"
        self.assertEqual(release_notes.notes(text, "1.0.0"), "### Added\n\n#### Detail\n\n- One.\n")


class TheRealChangelog(unittest.TestCase):
    def test_every_version_in_it_has_notes_cut_from_its_own_section(self):
        text = support.read(CHANGELOG)
        versions = [name for name in sections_of(text) if name.lower() != "unreleased"]
        self.assertTrue(versions)
        for version in versions:
            with self.subTest(version=version):
                notes = release_notes.notes(text, version)
                self.assertIn(notes.rstrip("\n"), text)
                lines = notes.rstrip("\n").split("\n")
                self.assertTrue(lines[0].strip() and lines[-1].strip())
                self.assertFalse([line for line in lines if line.startswith(("# ", "## "))])
                self.assertFalse([line for line in lines if release_notes.VERSION_LINK.match(line)])

    def test_the_release_workflow_cuts_the_top_version_s_notes(self):
        """The tag the release workflow sees for the version the manifests carry: exit 0 and that section."""
        top = check_manifests.changelog_version(support.ROOT)
        proc = support.run_py(SCRIPT, ["v" + top])
        self.assertEqual((proc.returncode, proc.stderr), (0, ""))
        self.assertEqual(proc.stdout, release_notes.notes(support.read(CHANGELOG), top))
        self.assertIn("### Added", proc.stdout)


class TheCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.changelog = os.path.join(cls.tmp, "CHANGELOG.md")
        support.write(cls.changelog, PLANTED)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def run_notes(self, *args):
        return support.run_py(SCRIPT, list(args))

    def test_it_prints_the_notes_and_exits_0(self):
        proc = self.run_notes("v1.10.0", "--changelog", self.changelog)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr),
                         (0, "### Added\n\n- The tenth minor release.\n", ""))

    def test_a_version_with_no_section_exits_1_and_says_what_to_add(self):
        proc = self.run_notes("v2.0.0", "--changelog", self.changelog)
        self.assertEqual((proc.returncode, proc.stdout), (1, ""))
        self.assertIn("no section for 2.0.0, under a heading `## [2.0.0]`", proc.stderr)
        self.assertIn("the headings found: Unreleased, 1.10.0, 1.1.0, 1.0.0", proc.stderr)
        self.assertIn(self.changelog, proc.stderr)

    def test_usage_and_an_unreadable_file_exit_2(self):
        for args in ((), ("latest", "--changelog", self.changelog),
                     ("v1.0.0", "--changelog", os.path.join(self.tmp, "missing.md"))):
            with self.subTest(args=args):
                proc = self.run_notes(*args)
                self.assertEqual((proc.returncode, proc.stdout), (2, ""))
                self.assertTrue(proc.stderr)


if __name__ == "__main__":
    unittest.main()
