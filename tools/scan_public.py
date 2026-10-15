#!/usr/bin/env python3
"""Refuse a tree, and optionally a commit, that would publish a secret or something personal.

Usage: python3 tools/scan_public.py --tree <dir> [--commit <rev> [--warn-metadata]]

Every file under <dir> is scanned, its `.git` folder aside: each line of its content and its path. A file
that is not UTF-8 text, or holds a NUL byte, is refused whole ("binary"), because its content cannot be
read. One exception: the plugin's directory icon, at exactly `.claude-plugin/icon.png`
(staged as `packaging/claude-plugin.icon.png`), passes when its bytes match the SHA-256 pinned below
(`ICON_SHA256`) and it holds only the PNG chunks IHDR, IDAT and IEND. The pin is what vouches for it: a person
looked at that exact image. Any other PNG, or a changed icon until the pin is updated, stays "binary". Text a reader cannot see is refused too ("hidden-text"): zero-width characters, a soft hyphen,
direction marks and overrides, invisible operators, a byte order mark, tag characters, supplementary
variation selectors. An agent reads every character of a skill file; a reviewer reads only what
renders. With --commit, the commit's author and committer (names and emails), its dates and its message
are scanned too; --warn-metadata prints those findings as WARN and leaves the exit code alone, which
suits CI, where web edits, merges and contributors' own addresses are routine.

A finding names its rule and its place, and shows only the first characters of what matched, with any
hidden or control character written as its code point, so the report never repeats the leak in full and
never carries what it found. Exit 0 clean, 1 findings, 2 usage or a commit that cannot be read.
Standard library only; Python 3.9 or newer.
"""
import argparse
import hashlib
import ipaddress
import os
import re
import struct
import subprocess
import sys

# Rule ids and their patterns. A rule is a regex, optionally with a predicate that decides whether a match
# is really a finding (an allowed email address, an address outside the private ranges, a placeholder).
EMAIL_DOMAINS = ("example.com", "example.org", "example.net", "users.noreply.github.com")
EMAIL_ADDRESSES = ("noreply@github.com", "noreply@anthropic.com")
# Exactly one label before a reserved suffix, so a real address cannot hide in front of one: an address at
# host.example passes; the same name at a real provider's domain with .example appended does not.
RESERVED_HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?\.(example|invalid)$")


def email_allowed(address):
    """True for the reserved example domains, GitHub's no-reply forms and the co-author trailer address."""
    address = address.lower()
    domain = address.rpartition("@")[2]
    return address in EMAIL_ADDRESSES or domain in EMAIL_DOMAINS or bool(RESERVED_HOST.match(domain))


def private_ipv4(match):
    """True for 10/8, 172.16/12, 192.168/16 and 169.254/16; the loopback and documentation ranges pass."""
    octets = [int(part) for part in match.groups()]
    if max(octets) > 255:
        return False
    a, b = octets[0], octets[1]
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168) or (a == 169 and b == 254)


# The unique-local range of RFC 4193, built from its first hextet so that no address is spelled in this file.
UNIQUE_LOCAL = ipaddress.IPv6Network((0xFC00 << 112, 7))


def private_ipv6(match):
    """True for a unique-local address; the loopback, link-local and documentation ranges pass."""
    try:
        return ipaddress.IPv6Address(match.group(0)) in UNIQUE_LOCAL
    except ValueError:
        return False


# A value that stands for a secret rather than being one, or a name in code rather than a value.
PLACEHOLDER = re.compile(r"(?i)example|placeholder|redacted|changeme|your[_-]|dummy|fake|sample|invalid|xxxx"
                         r"|not[_-]?a[_-]?secret")
DOTTED_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+")


def secret_value(match):
    """True when an unquoted value looks like a secret: letters and digits, no placeholder, no dotted name."""
    value = match.group(1)
    return bool(re.search(r"[A-Za-z]", value) and re.search(r"[0-9]", value)
                and not PLACEHOLDER.search(value) and not DOTTED_NAME.fullmatch(value))


# A name that claims the value beside it is a secret: the word alone or inside a longer name (an
# environment variable, a JSON key, a flag).
SECRET_NAME = r"(?i)(?<![A-Za-z0-9])[A-Za-z0-9_-]*(?:api[_-]?key|secret|token|passw(?:or)?d)[A-Za-z0-9_-]*"

# Characters that render as nothing or reorder the text around them, as (first, last) code points: the
# soft hyphen, the Arabic letter mark, the Mongolian vowel separator, zero-width characters and direction
# marks, bidi embeddings and overrides, the word joiner and invisible operators, bidi isolates, the byte
# order mark, the tag block, and the variation-selector supplement, whose 240 selectors attach unseen to
# any character. The sixteen basic variation selectors are left alone, because emoji use them. The class
# is built from the numbers, so this file holds none of the characters.
HIDDEN_RANGES = ((0x00AD, 0x00AD), (0x061C, 0x061C), (0x180E, 0x180E), (0x200B, 0x200F), (0x202A, 0x202E),
                 (0x2060, 0x2064), (0x2066, 0x2069), (0xFEFF, 0xFEFF), (0xE0000, 0xE007F), (0xE0100, 0xE01EF))
HIDDEN_CLASS = "[" + "".join("%s-%s" % (chr(first), chr(last)) for first, last in HIDDEN_RANGES) + "]"

RULES = (
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY( BLOCK)?-----"), None),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), None),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), None),
    ("github-pat", re.compile(r"\bgithub_pat_\w{60,}"), None),
    ("sk-key", re.compile(r"\bsk-(ant-|proj-)?[A-Za-z0-9_-]{20,}"), None),
    ("stripe-live-key", re.compile(r"(?<![A-Za-z0-9])sk_live_[A-Za-z0-9]{20,}"), None),
    ("huggingface-token", re.compile(r"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{20,}"), None),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), None),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), None),
    ("jwt", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), None),
    ("chat-webhook", re.compile(r"https://hooks\.slack\.com/services/\S+"), None),
    ("chat-webhook", re.compile(r"https://(discord|discordapp)\.com/api/webhooks/\S+"), None),
    ("chat-webhook", re.compile(r"https://[A-Za-z0-9.-]*webhook\.office\.com/\S+"), None),
    ("chat-webhook", re.compile(r"https://api\.telegram\.org/bot[0-9]{6,}:\S+"), None),
    ("secret-assignment", re.compile(SECRET_NAME + r"[\"']?\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"), None),
    ("secret-assignment", re.compile(SECRET_NAME + r"\s*[:=]\s*([A-Za-z0-9_./+=~-]{12,})(?![^\s,;)\]}])"),
     secret_value),
    ("url-credentials", re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"), None),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"),
     lambda m: not email_allowed(m.group(0))),
    ("home-path", re.compile(r"(/home|/Users)/(?!(?:user|runner)(?:/|$|[^\w.-]))[\w.-]+"), None),
    ("home-path", re.compile(r"[A-Za-z]:\\Users\\"), None),
    ("session-link", re.compile(r"claude\.ai/(code/session_|chat/|share/)"), None),
    ("session-link", re.compile(r"chatgpt\.com/(c|share|codex/tasks)/"), None),
    ("private-ipv4", re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?!\w|\.\d)"), private_ipv4),
    ("private-ipv6", re.compile(r"(?<![0-9A-Za-z:])(?=(?:[0-9A-Fa-f]*:){2})[0-9A-Fa-f:]{3,}(?![0-9A-Za-z:])"),
     private_ipv6),
    ("hidden-text", re.compile(HIDDEN_CLASS + "+"), None),
)

# A file whose name says it holds a credential has no place in a public tree, whatever it holds now: the
# same names the pre-commit guards of most repositories refuse.
CREDENTIAL_NAME = re.compile(
    r"^(\.env(\..*)?|.*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.token|id_rsa.*|id_ed25519.*|credentials\.json"
    r"|secrets\..*)$", re.IGNORECASE)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
UNSEEN = re.compile(HIDDEN_CLASS + r"|[\x00-\x1f\x7f]")


def visible(text):
    """Text with every hidden or control character written as its code point."""
    return UNSEEN.sub(lambda m: "<U+%04X>" % ord(m.group(0)), text)


def preview(text):
    """The first characters of a match, enough to find it and too few to reuse it."""
    return visible(text[:4]) + ("..." if len(text) > 4 else "")


def scan_text(text):
    """Yield (column, rule, matched text) for every finding in one line of text."""
    for rule, pattern, keep in RULES:
        for match in pattern.finditer(text):
            if keep is None or keep(match):
                yield match.start() + 1, rule, match.group(0)


def scan_path(relpath):
    """Findings in a file's path: every content rule, a credential-shaped name, a control character."""
    found = [(rule, text) for _, rule, text in scan_text(relpath)]
    name = relpath.rsplit("/", 1)[-1]
    if CREDENTIAL_NAME.match(name):
        found.append(("credential-file-name", name))
    if CONTROL.search(relpath):
        found.append(("control-character-in-name", ""))
    try:
        relpath.encode("utf-8")
    except UnicodeEncodeError:
        found.append(("name-not-utf-8", ""))
    return found


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ICON_PATHS = (".claude-plugin/icon.png", "packaging/claude-plugin.icon.png")
# The icon a person looked at (1024x1024, a white "b" and a mint block). Change it, then update this pin.
ICON_SHA256 = "6cdce8412199a08d0e39edaf5b2dcf4c4a3081928471a9de0acd6c9934201eaf"


def pinned_icon(rel, data):
    """True only for the pinned icon at its own path: the digest matches and the chunks are IHDR, IDAT, IEND."""
    if rel not in ICON_PATHS or hashlib.sha256(data).hexdigest() != ICON_SHA256:
        return False
    at, kinds = len(PNG_SIGNATURE), []
    while data.startswith(PNG_SIGNATURE) and at + 12 <= len(data):
        length, kind = struct.unpack(">I4s", data[at:at + 8])
        kinds.append(kind)
        at += 12 + length
    return at == len(data) and set(kinds) <= {b"IHDR", b"IDAT", b"IEND"} and kinds[:1] == [b"IHDR"] \
        and kinds[-1:] == [b"IEND"]


def walk(tree):
    """Every entry under tree, its top-level .git aside, as (relative path, absolute path), sorted."""
    entries = []
    for folder, dirs, files in os.walk(tree):
        if folder == tree and ".git" in dirs:
            dirs.remove(".git")
        dirs.sort()
        for name in sorted(files) + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
            full = os.path.join(folder, name)
            entries.append((os.path.relpath(full, tree).replace(os.sep, "/"), full))
    return entries


def scan_tree(tree):
    """Return (findings, files scanned); a finding is (place, rule, preview)."""
    findings = []
    entries = walk(tree)
    for rel, full in entries:
        for rule, text in scan_path(rel):
            findings.append((rel + " (name)", rule, preview(text)))
        if os.path.islink(full) or not os.path.isfile(full):
            findings.append((rel, "not-a-regular-file", ""))
            continue
        with open(full, "rb") as handle:
            data = handle.read()
        if pinned_icon(rel, data):
            continue
        try:
            if b"\0" in data:
                raise UnicodeDecodeError("utf-8", data, 0, 1, "NUL byte")
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append((rel, "binary", ""))
            continue
        for number, line in enumerate(text.split("\n"), 1):
            for column, rule, matched in scan_text(line):
                findings.append(("%s:%d:%d" % (rel, number, column), rule, preview(matched)))
    return findings, len(entries)


IDENTITY = re.compile(r"^(author|committer) (.*) <(.*)> (\d+) ([+-]\d{4})$")


class Unreadable(Exception):
    """The commit could not be read, so nothing can be said about it."""


def read_commit(tree, rev):
    """Return (hash, [(role, name, email, offset)], message) from the raw commit object."""
    if rev.startswith("-"):
        raise Unreadable("a revision may not start with '-': %r" % rev)
    def git(*args):
        result = subprocess.run(["git", "-C", tree] + list(args), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip() or "no such commit: %s" % rev
            raise Unreadable("git %s: %s" % (args[0], detail))
        return result.stdout
    commit = git("rev-parse", "--verify", "--quiet", rev + "^{commit}").decode("ascii").strip()
    raw = git("cat-file", "commit", commit)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Unreadable("commit %s is not UTF-8" % commit)
    head, _, message = text.partition("\n\n")
    people = []
    for line in head.split("\n"):
        match = IDENTITY.match(line)
        if match:
            people.append((match.group(1), match.group(2), match.group(3), match.group(5)))
    if sorted(role for role, _, _, _ in people) != ["author", "committer"]:
        raise Unreadable("commit %s has no single author and committer" % commit)
    return commit, people, message


def scan_commit(tree, rev):
    """Return (hash, findings) for the commit's metadata; a finding is (place, rule, preview)."""
    commit, people, message = read_commit(tree, rev)
    place = "commit " + commit[:12]
    findings = []
    for role, name, email, offset in people:
        for _, rule, text in scan_text(name):
            findings.append(("%s %s name" % (place, role), rule, preview(text)))
        if not email_allowed(email) or "@" not in email:
            findings.append(("%s %s email" % (place, role), "email", preview(email)))
        if offset != "+0000":
            findings.append(("%s %s date" % (place, role), "date-not-utc", offset))
    for number, line in enumerate(message.split("\n"), 1):
        for column, rule, text in scan_text(line):
            findings.append(("%s message:%d:%d" % (place, number, column), rule, preview(text)))
    return commit, findings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refuse a tree or commit that would publish a secret.")
    parser.add_argument("--tree", required=True, help="the folder to scan")
    parser.add_argument("--commit", help="also scan this commit's author, committer, dates and message")
    parser.add_argument("--warn-metadata", action="store_true",
                        help="report the commit's findings as WARN without failing (CI)")
    args = parser.parse_args(argv)
    if args.warn_metadata and not args.commit:
        parser.error("--warn-metadata needs --commit")
    if not os.path.isdir(args.tree):
        parser.error("--tree is not a folder: %s" % args.tree)
    tree = os.path.abspath(args.tree)

    findings, files = scan_tree(tree)
    warnings = []
    if args.commit:
        try:
            _, metadata = scan_commit(tree, args.commit)
        except Unreadable as error:
            print("scan_public: cannot read the commit: %s" % error, file=sys.stderr)
            return 2
        (warnings if args.warn_metadata else findings).extend(metadata)

    def show(place, rule, text):
        return visible("%s: %s%s" % (place, rule, " (%s)" % text if text else ""))
    for finding in findings:
        print(show(*finding))
    for finding in warnings:
        print("WARN " + show(*finding))
    if findings:
        print("scan_public: %d finding(s) in %d file(s) scanned, %d warning(s)" % (len(findings), files, len(warnings)))
        return 1
    print("scan_public: clean, %d file(s) scanned, %d warning(s)" % (files, len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
