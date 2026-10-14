# Contributing

Thank you for helping. Issues and pull requests are both welcome; for anything larger than a fix, open an issue first so the change can be agreed before you build it.

## Set up and check

You need Python 3.9 or newer, git and a POSIX shell; no package: the skill, its scripts, the tools and the tests use the standard library only.

```sh
python3 tests/run_tests.py              # every unit test; 0 failed and 0 skipped is the bar
python3 tools/check_skill.py            # the skill's self-check; 0 findings
python3 tools/check_manifests.py        # the manifests agree with each other and with CHANGELOG.md
python3 tools/scan_public.py --tree .   # no credential, email address, home path or binary file
```

CI runs the same commands on Python 3.9 and 3.14 on every push and pull request. Set `PYTHONDONTWRITEBYTECODE=1` if you would rather not leave `__pycache__/` behind; `.gitignore` ignores it either way.

To lint a prompt the skill wrote: `python3 skills/briefwright/scripts/lint_prompt.py <folder>/prompts/<task-id>/master-prompt.md --decisions <folder>/prompts/<task-id>/decisions.md`.

## The rules a change keeps

- **No model named, and harness tokens only in the guides.** Nothing under `skills/briefwright/` names a model family, version or id, the guides included; a model appears only as a placeholder such as `{MODEL_ID}`. A harness's own commands, flags, settings and file names appear only in `references/harness-claude-code.md`, `references/harness-codex.md` and `agents/openai.yaml`. The self-check enforces both.
- **The skill never names itself.** Its name lives in the frontmatter's `name:` line and nowhere else in the folder.
- **Frozen texts change only with their tests.** The question blocks, the run rules, the templates' fixed lines and the guides' blocks are checked word for word by the tests and the self-check. Change the text and its test in the same pull request, and say why.
- **Vendor facts are sourced.** Every factual line of a guide ends with a source key, and the guide's Sources section gives each key its URL and the date it was read. A fact you could not establish is marked open; it is never filled by a guess.
- **No published text without its licence.** Ideas may come from anywhere and are credited in `NOTICE`; text is copied only where its source's licence allows redistribution, with that licence named.
- **Standard library only**, in the skill and in every script and tool.
- **The scanners are never weakened** to let a change through. If one is wrong, fix the scanner in its own pull request, with a test.
- **No secrets**, in any file or commit. `LICENSE` is never edited.
- **Every change gets a line in `CHANGELOG.md`**, under an `## [Unreleased]` heading at the top (add the heading if it is missing). The maintainer turns it into a version at release.

## Add a guidance pack

A pack adds wording written for one model to the prompts that run on it. Copy `skills/briefwright/packs/TEMPLATE.md` to `packs/<pack-id>.md` and keep its headings. List the model ids it matches in `MATCHES` (a trailing `*` matches a prefix). Give each block one `When:` that names a fact of the task — never a size or "always" — one `Where:`, one `Adapt:` and one `text` fence. End every line with its source. A pack adds wording, text to leave out and review checks; it never changes a rule of the skill. The self-check reads every pack against the format in `packs/README.md`.

## Add a harness guide

A harness with no guide uses `references/harness-generic.md`. A guide of its own is `references/harness-<id>.md`, with the five headings and the block ids the generic guide has, each block one `text` fence, every line outside the fences sourced, and only the slots the self-check allows. Then add the new id where `SKILL.md` and `templates/decisions.md` list the guides; both are frozen texts, so their tests change in the same pull request. Add the guide to `HARNESS_FILES` in `tools/check_skill.py` too, with its test, or the self-check's S16 refuses the guide's own harness tokens; that is the one change to the self-check a new guide needs, and it is not a weakening. Commands, flags and settings come from the vendor's own documentation, never from memory.

## Reviews

A pull request gets CI, and a maintainer's review. The repository also carries an optional Codex review workflow that the maintainer can turn on with their own API key; it never runs for a fork. The alternative that keeps no secret in the repository is Codex's own code review on GitHub: once the maintainer connects it, a comment `@codex review` on a pull request asks for a review.

## Reporting

Questions and ideas to talk through: [Discussions](https://github.com/VibeCoding-1/briefwright/discussions). Bugs and feature requests: the issue templates. A harness you tried the skill in: the harness report template, with the version and the date. Vulnerabilities: privately, as [SECURITY.md](SECURITY.md) says. Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
