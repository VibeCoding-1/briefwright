#!/usr/bin/env python3
"""Print one version's section of CHANGELOG.md: the notes of that version's GitHub release.

Usage: python3 tools/release_notes.py <tag> [--changelog <file>]

<tag> is the release's tag, such as v1.2.0, or the bare version 1.2.0. <file> defaults to the CHANGELOG.md
beside tools/. The section is every line under the version's heading, `## [1.2.0]` with or without the date
Keep a Changelog writes after it, up to the next first- or second-level heading. Blank lines are trimmed at
both ends, and so are the version links Keep a Changelog keeps at the foot of the file, after the last section
(`[1.2.0]: https://...`, `[Unreleased]: https://...`); a section's own link definitions stay. The release
workflow makes the output the release's notes.

Exit 0 with the notes on stdout; 1 when the file has no section for the version, has two, or has an empty
one, saying which on stderr; 2 on usage or a file that cannot be read. Standard library only; Python 3.9 or
newer.
"""
import argparse
import os
import re
import sys

HEADING = re.compile(r"^##\s+\[([^\]]+)\]")
SECTION_END = re.compile(r"^#{1,2}\s")
VERSION_LINK = re.compile(r"^ {0,3}\[(?:[Uu]nreleased|v?[0-9][^\]]*)\]:\s*\S")
VERSION = re.compile(r"^[0-9][0-9A-Za-z.+-]*$")


class Usage(Exception):
    pass


class NoNotes(Exception):
    pass


def version_of(tag):
    """The version a tag names: v1.2.0 and 1.2.0 both name 1.2.0."""
    version = tag[1:] if tag.startswith("v") else tag
    if not VERSION.match(version):
        raise Usage("%r is not a version tag such as v1.2.0" % tag)
    return version


def notes(text, version):
    """The notes for `version` in the changelog `text`; NoNotes, with the reason, when there are none."""
    lines = text.splitlines()
    headings = []
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match:
            headings.append((index, match.group(1)))
    starts = [index for index, name in headings if name == version]
    if not starts:
        found = ", ".join(name for _, name in headings) or "none"
        raise NoNotes("no section for %s, under a heading `## [%s]` (the headings found: %s); add it before the "
                      "release" % (version, version, found))
    if len(starts) > 1:
        raise NoNotes("two sections for %s, at lines %s; keep one"
                      % (version, " and ".join(str(index + 1) for index in starts)))
    body = []
    for line in lines[starts[0] + 1:]:
        if SECTION_END.match(line):
            break
        body.append(line.rstrip())
    while body and (not body[-1] or VERSION_LINK.match(body[-1])):
        body.pop()
    while body and not body[0]:
        body.pop(0)
    if not body:
        raise NoNotes("the section for %s is empty; write its changes before the release" % version)
    return "\n".join(body) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print one version's section of CHANGELOG.md.")
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("tag", help="the release's tag, such as v1.2.0")
    parser.add_argument("--changelog", default=os.path.join(os.path.dirname(here), "CHANGELOG.md"),
                        help="the changelog (default: the CHANGELOG.md beside tools/)")
    args = parser.parse_args(argv)
    try:
        version = version_of(args.tag)
        try:
            with open(args.changelog, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            raise Usage("cannot read %s: %s" % (args.changelog, error))
    except Usage as error:
        print("release_notes: %s" % error, file=sys.stderr)
        return 2
    try:
        result = notes(text, version)
    except NoNotes as error:
        print("release_notes: %s: %s" % (args.changelog, error), file=sys.stderr)
        return 1
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
