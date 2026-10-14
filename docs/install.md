# Install

Every way to install briefwright, with its status, and what to know before you do. The [README](../README.md#install) gives the three one-liners; this page gives every route.

## Every route, with its status

| Harness | One line | Status |
|---|---|---|
| Claude Code | `claude plugin marketplace add VibeCoding-1/briefwright && claude plugin install briefwright@vibecoding-1` | tested on 2.1.296, 2026-10-13 (marketplace; `--plugin-dir` tested earlier) |
| Codex | `codex plugin marketplace add VibeCoding-1/briefwright && codex plugin add briefwright@vibecoding-1` | tested on 0.162.1, 2026-10-13 |
| Gemini CLI | `gemini skills install https://github.com/VibeCoding-1/briefwright.git --path skills/briefwright` | installs and removes cleanly from a clone (0.63.0, 2026-10-13) |
| Copilot CLI | `copilot plugin install VibeCoding-1/briefwright` | documented |
| GitHub CLI | `gh skill install VibeCoding-1/briefwright briefwright` (preview; gh 2.90 or newer) | documented |
| Cursor | `npx skills add VibeCoding-1/briefwright --skill briefwright -a cursor` | documented |
| OpenCode | `npx skills add VibeCoding-1/briefwright --skill briefwright -a opencode` | tested on 1.19.0, 2026-10-13 |
| claude.ai | zip `skills/briefwright/` (`zip -r briefwright.zip briefwright/` from `skills/`), then Customize > Skills > Upload, and turn it on | tested on 2026-10-13 |
| Antigravity | `npx skills add VibeCoding-1/briefwright --skill briefwright -a antigravity` | tested on 2.23.0, 2026-10-13 |

"Tested on" means the route was installed and used against this repository with that version on that date; [acceptance.md](acceptance.md) gives the steps. "Documented" means the command comes from the tool's own documentation and has not been run here yet; reports are welcome. A harness without its own guide in the skill (all but Claude Code and Codex) gets the generic guide.

## With the `skills` CLI

`npx skills add VibeCoding-1/briefwright` runs [the `skills` CLI](https://github.com/vercel-labs/skills), which asks which agents to install for, and whether for this project or for your user.

- For a project, it copies the skill to `.agents/skills/briefwright/`, which Codex, Gemini CLI, Copilot, Cursor, OpenCode and Antigravity read.
- For Claude Code, it links that copy from `.claude/skills/briefwright`. With `--copy`, it copies the skill there instead.
- This was read from the README and the source of the `skills` CLI, version 1.7.2, and that version was run for OpenCode and Antigravity on 2026-10-13.
- The CLI counts installs anonymously unless `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` is set.

## Try it in Claude Code without installing

Clone this repository and start `claude --plugin-dir <path to the clone>`. This route is tested, as is the marketplace install.

## The one permission Claude Code may ask for

Claude Code may ask before the skill reads its own files. Claude Code reads only inside the folder it was started in ([its working-folder rule](https://code.claude.com/docs/en/permissions#working-directories), which a plugin cannot lift for itself), and a plugin, a clone loaded with `--plugin-dir` or a copy under `~/.claude/skills/` sits outside it. So Claude Code may ask once in auto mode ("Yes, and keep allowing…" keeps the files readable) or before each read in Manual mode, and refuses the reads in an unattended `claude -p` session. In auto mode on 2.1.296 it asked nothing, because the skill read its files through the shell, which auto mode approved.

- **To allow the reads for good,** add `Read(~/.claude/plugins/cache/vibecoding-1/briefwright/**)` for the plugin, or `Read(~/.claude/skills/briefwright/**)` for a user-level copy, to `permissions.allow` in `~/.claude/settings.json`.
- **For one session,** start with `--add-dir <the skill's folder>`.
- **A copy in the project's `.claude/skills/`** needs nothing.

The refusal and both remedies were observed on the plugin with CLI 2.1.291. On 2.1.296, on 2026-10-13, a `claude -p` run without `--add-dir` was refused its reads, and one with it was not.

## What it needs

Python 3 on the machine the agent runs on, for the prompt linter (standard library only). Subagents are optional: where a harness cannot start them, the skill does their work in sequence and says so.

## claude.ai and the description's length

The upload documentation allows a description of up to 1,024 characters, but one support article says 200, and this skill's is 400. On 2026-10-13 the upload accepted it; if an upload refuses it, shorten the description in your copy.
