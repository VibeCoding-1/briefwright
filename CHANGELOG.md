# Changelog

Every notable change to this project is recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-14

The first public release. The skill names no model, recommends none, and reads a guide for the harness the run executes in. Its install routes were tested on Claude Code, Codex, OpenCode, Antigravity and claude.ai in October 2026, and it also installs on Gemini CLI, Copilot CLI, Cursor and the GitHub CLI; `docs/install.md` gives each route's status.

### Added

- The skill, `skills/briefwright/`: framing, an interview in rounds until nothing is assumed, method design, writing, and review before delivery, with a quick lane for small tasks. In Claude Code, with a person answering, each round of questions goes through its question picker; elsewhere, or if the picker is refused, as numbered text.
- Short prompts, with a word target per size (quick under about 700, standard about 1,500–2,000, deep about 4,000–5,000) that the linter warns past.
- Harness guides for Claude Code and Codex, and a generic guide for every other harness that reads the open Agent Skills format. Every vendor fact carries its source and retrieval date; the Codex facts that could not be established are marked open.
- A model guideline in every prompt with subagents: the strongest model available for planning, hard building and review, a faster one for searches, simple edits and mechanical checks, chosen per seat where the harness allows; a model the person names is used, set at launch.
- A sequential fallback where a harness cannot start subagents, for the run's seats and for the skill's own helper seats.
- The guidance pack format, with an empty template. No pack ships.
- The prompt linter (`scripts/lint_prompt.py`), Python standard library only.
- The self-check (`tools/check_skill.py`), the manifest check (`tools/check_manifests.py`), the public leak scanner (`tools/scan_public.py`), the unit tests and the end-to-end evals with their Claude Code runner.
- Packaging: an Agent Plugins `plugin.json`, a Claude Code plugin and marketplace, a Codex marketplace, and `agents/openai.yaml`.
- CI on every push and pull request, and an optional Codex review workflow, off until the maintainer turns it on.
- Automations: a release from this changelog for each version tag, a weekly run of every check on the newest tools that opens an issue when it fails, a welcome on a first issue or pull request, the issue labels, and OpenSSF Scorecard and CodeQL code scanning once the repository is public.
- `docs/acceptance.md`, the maintainer's acceptance steps for every install route in `docs/install.md`.

[1.0.0]: https://github.com/VibeCoding-1/briefwright/releases/tag/v1.0.0
