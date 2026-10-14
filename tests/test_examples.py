"""The README's before-and-after against the example it quotes, and the examples themselves.

Every line the README quotes is a line of the example it links; each example's README quotes the request its
decisions record; every link into or inside examples/ resolves; each example folder is complete and linked; and no
example holds a placeholder, which nothing would fill there.
"""
import os
import re
import unittest

from support import ROOT, read

README = os.path.join(ROOT, "README.md")
EXAMPLES = os.path.join(ROOT, "examples")
EXAMPLE_FILES = ("README.md", "master-prompt.md", "decisions.md")
LINK = re.compile(r"\]\(([^)\s]+)\)")
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")


def section(text, heading):
    """The lines under `heading` (a whole line, such as '## Before and after') up to the next heading of its
    level or higher."""
    level = len(heading.split(" ", 1)[0])
    following = re.compile(r"^#{1,%d} " % level)
    lines = text.split("\n")
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if following.match(lines[i])), len(lines))
    return lines[start:end]


def blockquotes(lines):
    """Each blockquote as a list of its lines, the `> ` marker removed."""
    quotes, current = [], None
    for line in lines:
        if line.startswith(">"):
            if current is None:
                current = []
                quotes.append(current)
            current.append(line[2:] if line.startswith("> ") else line[1:])
        else:
            current = None
    return quotes


def first_request(readme, decisions):
    """(the README's first blockquote, its list indentation removed; the first blockquote under the decisions'
    "The person's words"): the request as the example presents it and as its decisions record it."""
    quoted = blockquotes([line.lstrip(" ") for line in readme.split("\n")])
    words = blockquotes(section(decisions, "## The person's words"))
    return (quoted or [None])[0], (words or [None])[0]


def relative_links(text):
    return [target.split("#", 1)[0] for target in LINK.findall(text)
            if not re.match(r"[a-z]+:", target) and not target.startswith("#")]


def example_folders():
    return sorted(name for name in os.listdir(EXAMPLES) if os.path.isdir(os.path.join(EXAMPLES, name)))


class BeforeAndAfter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = section(read(README), "## Before and after")
        folders = [target for target in relative_links("\n".join(cls.lines)) if target.startswith("examples/")]
        cls.folder = os.path.join(ROOT, folders[0].rstrip("/"))
        cls.prompt = read(os.path.join(cls.folder, "master-prompt.md")).split("\n")
        cls.decisions = read(os.path.join(cls.folder, "decisions.md")).split("\n")

    def test_the_readme_holds_no_pending_line(self):
        """A `pending` comment marks a section still to be filled; the marker is split here so that this file
        holds none itself."""
        self.assertNotIn("<!-- " + "pending:", read(README))

    def test_the_request_is_the_example_s_first_message(self):
        words = section("\n".join(self.decisions), "## The person's words")
        self.assertEqual(blockquotes(self.lines)[0], blockquotes(words)[0])

    def test_every_quoted_line_is_a_line_of_the_example(self):
        known = set(self.prompt) | {line[2:] for line in self.decisions if line.startswith("> ")}
        quoted = [line for quote in blockquotes(self.lines) for line in quote if line.strip()]
        self.assertGreater(len(quoted), 5)
        self.assertEqual([line for line in quoted if line not in known], [])


class Examples(unittest.TestCase):
    def test_each_example_folder_is_complete_and_linked_from_the_readme(self):
        readme = read(README)
        self.assertTrue(example_folders())
        for name in example_folders():
            for required in EXAMPLE_FILES:
                self.assertTrue(os.path.isfile(os.path.join(EXAMPLES, name, required)), (name, required))
            self.assertIn("](examples/%s/)" % name, readme)

    def test_links_into_and_inside_examples_resolve(self):
        sources = [(README, target) for target in relative_links(read(README)) if target.startswith("examples/")]
        for folder, _, files in os.walk(EXAMPLES):
            for name in files:
                if name.endswith(".md"):
                    path = os.path.join(folder, name)
                    sources += [(path, target) for target in relative_links(read(path))]
        self.assertTrue(sources)
        broken = [(os.path.relpath(path, ROOT), target) for path, target in sources
                  if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), target)))]
        self.assertEqual(broken, [])

    def test_each_example_quotes_the_request_its_decisions_record(self):
        for name in example_folders():
            with self.subTest(example=name):
                readme, decisions = (read(os.path.join(EXAMPLES, name, file)) for file in ("README.md", "decisions.md"))
                quoted, recorded = first_request(readme, decisions)
                self.assertIsNotNone(quoted)
                self.assertEqual(quoted, recorded)

    def test_a_request_changed_in_either_file_is_caught(self):
        """The check above, run on copies with the request's last word dropped in one file."""
        for name in example_folders():
            texts = {file: read(os.path.join(EXAMPLES, name, file)) for file in ("README.md", "decisions.md")}
            line = first_request(texts["README.md"], texts["decisions.md"])[0][0]
            for changed in texts:
                with self.subTest(example=name, file=changed):
                    drifted = dict(texts)
                    drifted[changed] = texts[changed].replace("> " + line, "> " + line.rsplit(" ", 1)[0], 1)
                    self.assertNotEqual(drifted[changed], texts[changed])
                    quoted, recorded = first_request(drifted["README.md"], drifted["decisions.md"])
                    self.assertNotEqual(quoted, recorded)

    def test_no_example_holds_a_placeholder(self):
        found = []
        for folder, _, files in os.walk(EXAMPLES):
            for name in files:
                path = os.path.join(folder, name)
                found += ["%s: %s" % (os.path.relpath(path, ROOT), match) for match in PLACEHOLDER.findall(read(path))]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
