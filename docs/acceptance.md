# Acceptance steps

The steps the maintainer runs on their own machine before a status line in [install.md](install.md) changes. Each step names what you should see; write down what you actually saw, and file it as a harness report issue at the end of each harness's part. A step that cannot be run is recorded as not run, with the reason, never as passed.

You need a clone of this repository for the linter: `git clone https://github.com/VibeCoding-1/briefwright.git`. Below, `<clone>` is its path.

## 1. Repository settings (once, after the repository is public)

1. **Private vulnerability reporting.** In the repository's Settings, under Security, enable private vulnerability reporting. *Expected:* the Security tab shows **Report a vulnerability**. `SECURITY.md` and `CODE_OF_CONDUCT.md` both send reports there.
2. **Description, topics and social preview.** Set the description and topics in the About panel, and upload the social preview image in Settings, General (a 1280×640 PNG; it never goes in the tree, because the scanners refuse binary files other than the pinned plugin icon). *Expected:* a shared link to the repository shows the image.
3. **Optional: the Codex review workflow.** Add the repository secret `OPENAI_API_KEY`, then set the repository variable `CODEX_REVIEW` to `true`. *Expected:* the next pull request opened from a branch of this repository gets a review comment; a pull request from a fork or from Dependabot does not run the review.
4. **Discussions.** In Settings, General, Features, turn on Discussions. *Expected:* the issue chooser's question link and `CONTRIBUTING.md`'s link to Discussions open the Discussions tab.
5. **Labels.** In the Actions tab, open **Labels** and choose **Run workflow**. *Expected:* the run succeeds, and the Issues tab's **Labels** page lists `bug` and `enhancement` with the descriptions in `.github/workflows/labels.yml`. Run it again whenever that list changes.
6. **Code scanning.** In Settings, Advanced Security, leave CodeQL's default setup off: `.github/workflows/codeql.yml` is this repository's code scanning setup, and GitHub rejects the CodeQL results a workflow uploads while default setup is on. Then, in the Actions tab, run **CodeQL** and **Scorecard** once by hand. *Expected:* the menu next to **CodeQL analysis** offers no **Switch to advanced**, which it shows only while default setup is on; in both runs the analysis job runs instead of being skipped, and the Security tab's **Code scanning** lists results from CodeQL and from Scorecard. The same two runs started by hand while the repository is private should each succeed, with the analysis job skipped and a notice saying the repository is private.
7. **The weekly check.** In the Actions tab, run **Latest tools** by hand. *Expected:* the job **Every check on the newest tools** succeeds, its step **Show the versions under test** lists the versions it installed, and the job **Open or update the issue** is skipped. A scheduled run that fails opens one issue titled "The weekly check on the newest tools fails", or comments on it while it is open; close it once the check passes again.
8. **Scheduled runs stay on.** In a public repository, GitHub turns the scheduled workflows off once nothing has happened in it for 60 days. *Expected:* if that happens, the page of **Latest tools**, **Scorecard** and **CodeQL** in the Actions tab offers **Enable workflow**; choose it on each.
9. **Read-only token by default.** In Settings, Actions, General, under "Workflow permissions", choose the restricted setting, read access for the `contents` and `packages` permissions only, and save. *Expected:* the restricted setting is selected; GitHub gives it to a new repository in a personal account. A job that sets no `permissions:` of its own gets a token that can only read; every workflow here sets its own, so none of them changes.
10. **No pull requests from workflows.** On the same page, leave **Allow GitHub Actions to create and approve pull requests** off, and save. *Expected:* the box is clear, as GitHub leaves it on a new repository in a personal account, so no workflow's token can open or approve a pull request.
11. **Approval for outside contributors.** On the same page, under "Approval for running fork pull request workflows from contributors", choose **Require approval for all external contributors**, and save. *Expected:* a workflow run on a fork's pull request opened by anyone who is not an owner or member of the repository waits until someone with write access approves it. Runs on `pull_request_target`, which run in the base branch's context, never wait: here that is only the welcome, which checks out nothing.
12. **Only admins create version tags.** In Settings, Rules, Rulesets, choose **New ruleset**, then **New tag ruleset**. Name it `version tags`, set it Active, add Repository admin to the bypass list, add the target pattern `v*` under the target tags, select **Restrict creations**, keep the rules already selected, and create it. *Expected:* the ruleset is listed as Active, and only someone on its bypass list can create a tag matching `v*`, so only an admin's tag starts the Release workflow.

## 2. Claude Code: the marketplace install

To keep your own configuration out of the test, run these steps with `CLAUDE_CONFIG_DIR` set to an empty folder: a separate configuration directory keeps no login, so it needs its own login, `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` ([authentication](https://code.claude.com/docs/en/authentication#log-in-with-multiple-accounts), read 2026-10-05). `claude --plugin-dir <clone>` loads the plugin for one session with no install and needs none of this ([plugin CLI reference](https://code.claude.com/docs/en/plugins/cli-reference#flags-that-load-a-plugin-for-one-session), read 2026-10-05).

The guide's unattended launch rests on what the CLI let a `-p` run under `acceptEdits` do. No page documents it; each row was observed once and is a check to repeat on a new CLI.

| Observed, CLI 2.1.291: confirm on a new CLI | What the guide does with it |
|---|---|
| A command holding `${…}` is refused as uncheckable | No command the run executes holds a shell variable outside single quotes |
| `mkdir` and `cd` on a path holding a shell variable are refused, even inside an `--add-dir` folder | Every path in a command the run executes is literal; the bench root defaults to `<the project's parent folder>/benches/<task-id>` |
| grep and sed on a file outside the session's folders are blocked; inside them they run with no rule | grep and sed take no rule |
| `printenv` and `env` run only under a rule | No allowlist rule prints the environment or reads variables by a prefix |

One more observation concerns the install, not the guide (CLI 2.1.291, `-p` runs in the default mode; confirm on a new CLI). Claude Code reads only inside the folder it was started in, and in those runs a skill installed as a plugin, or copied to the configuration's `skills/`, could read none of its own files; for the plugin, `--add-dir` with the skill's folder, or a `Read` rule on its cache folder in the configuration's `settings.json`, let it read them. [install.md](install.md) gives both remedies; step 3 confirms them.

**Run on 2026-10-13** with Claude Code 2.1.296: the install, step 3 as installed and with `--add-dir`, the use and the removal. The status in install.md changed with that run. In step 5, in auto mode, no permission prompt showed: the skill read its files through the shell, which auto mode approved.

1. **Versions.** Record `claude --version`, the operating system and the date.
2. **Install.** Run `claude plugin marketplace add VibeCoding-1/briefwright`, then `claude plugin install briefwright@vibecoding-1`. *Expected:* both exit 0, and `claude plugin list` shows `briefwright`.
3. **Its own files, unattended.** Here `<config>` is the absolute path of the folder `CLAUDE_CONFIG_DIR` names, and `<skill folder>` is `<config>/plugins/cache/vibecoding-1/briefwright/<version>/skills/briefwright`, `<version>` being the one folder the install made there. In an empty scratch folder, run `claude -p "/briefwright:briefwright Prepare a master prompt for adding a CSV export button to a small Flask app that is not in this folder yet." --permission-mode default --max-budget-usd 1 --output-format json` three times: as installed; with `--add-dir <skill folder>` added; and without that flag, with the rule `Read(/<config>/plugins/cache/vibecoding-1/briefwright/**)`, whose path starts with `//`, added to the `permissions.allow` list of `<config>/settings.json`, keeping what the install wrote there; remove the rule after that run, before the next step. *Expected:* the first run's `permission_denials` lists a `Read` of a file in the skill folder; the other two list no such `Read`. A denied write into the scratch folder may appear in any of the three, since nobody answers the default mode's prompt in `-p`; it is not this step's question. Record each outcome from the JSON, not from the session's own account.
4. **Unattended permissions.** In a scratch folder holding a file `inside.txt`, and a file `outside.txt` beside the folder, write a prompt file that asks the session to run each of these commands exactly as written, each in a call of its own, and to report each as RAN or DENIED: `mkdir -p "$PWD/sub-a"`; `mkdir -p "${PWD}/sub-b"`; `printenv LANG`; `sed -n 1p ../outside.txt`; `cat < "$PWD/inside.txt"`; `echo "$(pwd)"`. Run `claude -p --permission-mode acceptEdits --allowed-tools "Bash(mkdir *)" --max-budget-usd 1 --output-format stream-json --verbose < <prompt file>` and keep its output, one JSON event per line. *Expected:* the last line, the result message, lists all six commands in `permission_denials`. The last two, a redirection from a path holding a variable and a `$(…)`, have never been run: the guide assumes both are refused, as `${…}` is, and no command the run executes holds either. Record the outcome of each from that output, not from the session's own account.
5. **Use.** In a new session in a scratch folder, ask for a small master prompt, for example "Prepare a master prompt for adding a `--version` flag to the CLI in this folder; another session will run it." *Expected:* the skill is invoked; before it first reads one of its own files, Claude Code asks before each read in Manual mode; in auto mode no prompt need appear; then its first round of questions arrives in Claude Code's question picker, at most four questions to a call, each with its recommended answer first. Record what was asked, how, and in which mode.
6. **Remove.** Run `claude plugin uninstall briefwright@vibecoding-1`. *Expected:* it exits 0 and `claude plugin list` no longer shows the plugin.
7. **Report.** File a harness report issue. *Then:* the Claude Code status in [install.md](install.md) reads `tested on <version>, <date>`, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` change with them; install.md's note on the skill's own files names the version step 3 confirmed, or changes where step 3 contradicted it; in `references/harness-claude-code.md`, each observation step 4 confirmed is dated with that version, and one it contradicted changes, with the table above.

## 3. Codex

Codex support is written from Codex's documentation and source. The guide states the facts of the first table from the documentation or the source, but nobody has run them: each is a check to confirm. The facts of the second table could not be established at all; each is open until a step settles it, and stays open if no step can.

| Settled from docs or source, not run: confirm | From | Confirmed by |
|---|---|---|
| A resumed call, `codex exec -m … -s … resume <id> "<message>" --json`, takes `--json`, and runs on the model and sandbox its own flags give, not the first call's | source | Launch and resume |
| The `--json` output opens with a `thread.started` event that carries the thread's id as `thread_id` | docs and source | Launch and resume |
| Under `-s workspace-write`, `.git` is read-only and the network off, so a commit and a push fail | docs | Git and network |

| Open fact | Settled by |
|---|---|
| Which branch a cloud task works on, how it picks a model, and whether it loads `AGENTS.md` | Cloud (optional) |
| A documented minimum CLI version for what the guide's blocks use | no step: it stays open until Codex documents one |

**Run on 2026-10-13** with Codex 0.162.1: steps 1 to 4. The status in install.md changed with that run. Steps 5 to 8 have not been run, so the facts in the tables above are still to confirm.

1. **Versions.** Record `codex --version`, the operating system and the date.
2. **Install.** Run `codex plugin marketplace add VibeCoding-1/briefwright`, then `codex plugin add briefwright@vibecoding-1`. *Expected:* both exit 0, and `/skills` in a new `codex` session lists `briefwright`. While this repository is private, install as [its row in §4](#while-the-repository-is-private) says.
3. **A prompt.** In a scratch git repository, start `codex` and ask for a small master prompt for a run you will start with `codex exec` and leave, for example "Prepare a master prompt for adding a `--version` flag to the CLI in this folder; I'll start it with codex exec and walk away." *Expected:* the skill reads `references/harness-codex.md`, and its first round asks where the run executes, or records it from your words; the task stays on the quick lane: one round, a summary to confirm before anything is written, no red team, and a launch with no resume loop; the prompt and `decisions.md` land in `prompts/<task-id>/`.
4. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
5. **Launch and resume.** Run the `codex exec` launch from `decisions.md`, section Launch, as written. *Expected:* `launch-0.jsonl` appears in the run folder the launch names, and `head -n 1` of it is a `thread.started` event with `thread_id`. If the loop resumed, `launch-1.jsonl` holds JSON events; record what shows the sandbox, if anything does.
6. **Git and network.** With git left to you, the prompt's Run rules tell the run to commit nothing and `decisions.md` records the choice under Accepted defaults; check both. Then, in the scratch repository, run `codex exec -s workspace-write "Run git commit --allow-empty -m probe, then curl -sI https://example.com, and report what each printed."`. *Expected:* both fail, the commit on a read-only `.git` and the request on the network. Record what each printed.
7. **No subagents.** Ask again as in **A prompt**, attended this time and large enough that the skill does not take its quick lane, in a session started with `codex -c agents.enabled=false`. *Expected:* the skill's cold read and review run one after the other in the same session; `decisions.md`, section Review, says the seats ran in this session, and the delivery message says so.
8. **Cloud (optional).** Start a Codex cloud task on a repository that holds a produced prompt. *Expected:* record which branch the task works on, whether the task form offers a model, and whether the task follows the repository's `AGENTS.md`.
9. **Report.** File a harness report issue with every observation. *Then:* the Codex status in [install.md](install.md) reads `tested on <version>, <date>`, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` change with them; in `references/harness-codex.md`, each fact a step confirmed loses its "not run" mark, and each open fact a step settled is written in, with its source.

## 4. Before the other routes

Sections 5 to 11 give the steps for the routes that §2 and §3 do not cover, in the shape of those two. In §5 to §10, each *Expected* comes from the tool's own documentation or source, read on 2026-10-11 at the version its section names; where they are silent, the step says what to record instead. §11 follows §9, its *Expected* drawn from the `skills` CLI and from its run. Gemini CLI's install, listing and removal, and OpenCode, claude.ai and Antigravity, were run on 2026-10-13, as each section notes; Copilot CLI, the GitHub CLI and Cursor have not been run against this repository. Wherever a Report step, in §2 and §3 too, changes a status, the expected statuses in `tests/test_acceptance.py` change with those in `tests/test_readme.py`.

### While the repository is private

The steps can run before the repository is public. For each route, the documentation and the source were read for whether its install reaches a private GitHub repository with your own git or `gh` login. Where the table says yes, run the route's line as written. Where it says not documented, run the line once and record what it prints; if it fails, install the same files from `<clone>` with the last column's line. Where it says no, use that line at once. A route installed from `<clone>` is installed again with its own line once the repository is public, and its status changes only after that run. Never paste a token into any of these commands.

| Route | Reaches a private repository? | While private, install with |
|---|---|---|
| Claude Code | Yes: the marketplace is cloned "with the git credentials already on your machine", with no prompt. Over HTTPS a `gh auth login` or the macOS Keychain serves; the `owner/repo` form clones over SSH instead when your SSH key authenticates to github.com, and then the key must work without a passphrase prompt and github.com must be in your `known_hosts` (docs) | the line, §2 step 2 |
| Codex | Not documented. The source (rust-v0.162.1) runs `git clone` with your own git settings and prompts turned off, so a credential helper that holds your GitHub login would serve | the line; if it fails, `codex plugin marketplace add <clone>`, then `codex plugin add briefwright@vibecoding-1` |
| Gemini CLI | No, from the source (v0.63.0): its clone turns off git's credential helpers and your global git settings, and passes on only a `GITHUB_TOKEN` set in the environment | `gemini skills install <clone>/skills/briefwright` |
| Copilot CLI | Not documented: the plugin pages give `OWNER/REPO` and say nothing of private repositories | the line; if it fails, `copilot plugin install <clone>` |
| GitHub CLI | Not documented. The source (v2.102.0) reads the repository through `gh`'s own signed-in API client | the line; if it fails, `gh skill install <clone> briefwright --from-local` |
| Cursor | Yes: the `skills` CLI's README (1.7.2) says "Use the same command for public and private repositories", and tries your git credentials, then `gh repo clone`, then SSH | the line |
| OpenCode | Yes, through the same `skills` CLI as Cursor | the line |
| claude.ai | Nothing is downloaded: the zip is made from `<clone>`, which you clone with your own login | the line |
| Antigravity | Yes, through the same `skills` CLI as Cursor | the line |

### The scratch repository and the request

Unless a step says otherwise, run a section in a new, empty folder made a git repository with `git init`, holding one file, `greet.py`:

```python
import argparse

parser = argparse.ArgumentParser(prog="greet")
parser.add_argument("name")
print("Hello, %s!" % parser.parse_args().name)
```

Each **Use** step asks for a small master prompt, as §2 step 5 does: "Prepare a master prompt for adding a `--version` flag to the CLI in this folder; another session will run it." Answer the question on where the run executes with its recommendation, this harness, and the question on autonomy with "I watch it"; answer any other question with its recommendation, and confirm the summary. None of these harnesses has a guide of its own in the skill, so the skill reads `references/harness-generic.md`, and each Use step expects, besides what its section says:

- its first round of questions asks where the run will execute, and whether you will watch the run, each with a recommendation;
- after you confirm, `prompts/<task-id>/master-prompt.md` and `prompts/<task-id>/decisions.md` are in the folder, and `decisions.md`, section Launch, holds the generic guide's attended launch, which begins "Your harness, attended:";

## 5. Gemini CLI

From Gemini CLI's documentation (`docs/cli/skills.md`, `docs/cli/cli-reference.md`) and its source at v0.63.0.

**Run on 2026-10-13** with Gemini CLI 0.63.0, installed from a clone as §4's table says: the install, the listing and the removal. The status in install.md changed with that run.

1. **Versions.** Record `gemini --version`, the operating system and the date.
2. **Install.** Run `gemini skills install https://github.com/VibeCoding-1/briefwright.git --path skills/briefwright`. *Expected:* a security confirmation prompt, which `--consent` would skip; once you accept, `Successfully installed skill: briefwright (scope: user, location: …)`, the location under `~/.gemini/skills/`.
3. **Listed.** Run `gemini skills list`. *Expected:* `briefwright [Enabled]`, with its description and location. In a session, `/skills list` shows it too.
4. **Use.** In the scratch repository, start `gemini` and ask as §4 says. *Expected:* Gemini calls its `activate_skill` tool, and a confirmation prompt shows the skill's name, its purpose and the folder it will gain access to; once you approve, that folder is added to the agent's allowed file paths, so the skill reads its own files without another prompt; then as §4 says. Record every other prompt Gemini CLI shows, and when.
5. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** Run `gemini skills uninstall briefwright`. *Expected:* `Successfully uninstalled skill: briefwright (scope: user, location: …)`, and `gemini skills list` no longer shows it.
7. **Report.** File a harness report issue. *Then:* the Gemini CLI status in [install.md](install.md) reads `tested on <version>, <date>`, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with them; whatever a step contradicted changes here, with its source.

## 6. Copilot CLI

From GitHub's documentation for Copilot CLI (the plugin reference, finding and installing plugins, adding agent skills, the command reference and "About GitHub Copilot CLI"), current at CLI 1.0.95.

1. **Versions.** Record `copilot version`, the operating system and the date.
2. **Install.** Run `copilot plugin install VibeCoding-1/briefwright`. *Expected:* the documentation gives no output for this command, so record what it prints and its exit code. A direct install goes under `~/.copilot/installed-plugins/_direct/`, and the repository's root `plugin.json` names the Agent Plugins 1.0 schema, under which Copilot loads the skill from `skills/`.
3. **Listed.** Run `copilot plugin list`. *Expected:* it lists `briefwright`. In a session, `/skills list` lists `briefwright`, and `/skills info briefwright` names the plugin it came from.
4. **Use.** In the scratch repository, start `copilot` and ask as §4 says. *Expected:* at start, Copilot asks you to confirm that you trust the folder; it decides to use the skill from your prompt and the skill's description, or uses it when the prompt names `/briefwright`; it asks before the first command that could modify or run a file; then as §4 says. Record whether it asks before reading the skill's own files, which sit outside the folder: the documentation does not say.
5. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** Run `copilot plugin uninstall briefwright`. *Expected:* `copilot plugin list` no longer lists it.
7. **Report.** File a harness report issue. *Then:* the Copilot CLI status in [install.md](install.md) reads `tested on <version>, <date>`, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with them; whatever a step contradicted changes here, with its source.

## 7. GitHub CLI

From the GitHub CLI manual (`gh skill`, `gh skill install`, `gh skill list`) and its source at v2.102.0. The manual says `gh skill` is in preview and may change without notice; the command first appears in the source at v2.90.0.

1. **Versions.** Record `gh --version` (2.90 or newer), the operating system and the date.
2. **Install.** In the scratch repository, run `gh skill install VibeCoding-1/briefwright briefwright`; when it asks, choose GitHub Copilot as the agent and the project scope. *Expected:* `Installed briefwright (from VibeCoding-1/briefwright@<ref>)`, followed by the folder, where `<ref>` is the latest tagged release, or the default branch when there is none; at project scope GitHub Copilot's folder is `.agents/skills/`; then a warning that skills may contain prompt injections or malicious scripts, with a `gh skill preview` command. The install adds source-tracking metadata to the skill's frontmatter: record the first 20 lines of `.agents/skills/briefwright/SKILL.md`.
3. **Listed.** Run `gh skill list --json skillName,scope,path`. *Expected:* it lists `briefwright` at project scope, with its path. In Copilot CLI started in the scratch repository, `/skills list` lists it.
4. **Use.** In Copilot CLI started in the scratch repository, ask as §4 says. *Expected:* as §6's Use step, except that the skill's files sit inside the folder; then as §4 says.
5. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** The manual lists no command that removes a skill, so delete the folder `gh skill list` gives as its path. *Expected:* `gh skill list` no longer shows `briefwright`.
7. **Report.** File a harness report issue. *Then:* the GitHub CLI status in [install.md](install.md) reads `tested on <version>, <date>`, keeping "preview", the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with them; whatever a step contradicted changes here, with its source.

## 8. Cursor

From Cursor's skills page (`cursor.com/docs/skills`) and the `skills` CLI's README and source at 1.7.2.

1. **Versions.** Record Cursor's version from its About window, `npx skills --version`, the operating system and the date.
2. **Install.** In the scratch repository, run `npx skills add VibeCoding-1/briefwright --skill briefwright -a cursor`. *Expected:* it asks for the installation scope: choose Project; then it asks "Proceed with installation?". The skill is copied to `.agents/skills/briefwright/`, Cursor's project folder, and `skills-lock.json` in the scratch repository records it.
3. **Listed.** Run `npx skills list`. *Expected:* it lists `briefwright`. In Cursor, **Customize**, then **Skills**, shows it.
4. **Use.** Open the scratch repository in Cursor and, in Agent chat, ask as §4 says. *Expected:* the agent decides from context to use the skill, or you start it by typing `/` and its name; then as §4 says. Record each approval Cursor asks for, and when: the pages read do not say.
5. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** In the scratch repository, run `npx skills remove briefwright`. *Expected:* it asks you to confirm, then prints `Successfully removed 1 skill(s)`; **Customize**, then **Skills**, no longer shows it.
7. **Report.** File a harness report issue. *Then:* the Cursor status in [install.md](install.md) reads `tested on <version>, <date>`, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with them; whatever a step contradicted changes here, with its source.

## 9. OpenCode

From OpenCode's skills and permissions pages (`opencode.ai/docs/skills`, `opencode.ai/docs/permissions`) and the `skills` CLI's README and source at 1.7.2.

**Run on 2026-10-13** with OpenCode 1.19.0 and the `skills` CLI 1.7.2: steps 1 to 6. The status in install.md changed with that run.

1. **Versions.** Record `opencode --version`, `npx skills --version`, the operating system and the date.
2. **Install.** In the scratch repository, run `npx skills add VibeCoding-1/briefwright --skill briefwright -a opencode`. *Expected:* as §8's Install step: the scope question, answered Project, "Proceed with installation?", the copy in `.agents/skills/briefwright/` and `skills-lock.json`.
3. **Listed.** Run `npx skills list`. *Expected:* it lists `briefwright`. OpenCode documents no command that lists skills: its `skill` tool's description carries them, so ask a session which skills it can load, and record the answer.
4. **Use.** In the scratch repository, start `opencode` and ask as §4 says. *Expected:* OpenCode finds project skills from the working folder up to the git worktree; the agent loads the skill with its `skill` tool; with OpenCode's default permissions nothing is asked before it loads the skill or reads its files, which sit inside the folder; then as §4 says. Record any prompt it shows.
5. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** In the scratch repository, run `npx skills remove briefwright`. *Expected:* it asks you to confirm, then prints `Successfully removed 1 skill(s)`; asked again, a new session no longer names the skill.
7. **Report.** File a harness report issue. *Then:* the OpenCode status in [install.md](install.md) reads `tested on <version>, <date>`, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with them; whatever a step contradicted changes here, with its source.

## 10. claude.ai

From Claude's documentation on creating skills (`claude.com/docs/skills/how-to`) and the help articles "Using Skills in Claude" and "How to create custom skills". claude.ai shows no version.

**Run on 2026-10-13:** the zip, the upload, the listing, the use and the removal. The status in install.md changed with that run, and the upload accepted the description whole.

1. **Versions.** Record your plan, whether you use the browser or the desktop app, and the date. On a Free, Pro or Max plan, **Code execution and file creation** must be on in Settings, Capabilities.
2. **Install.** In `<clone>`, zip `skills/briefwright/` (`zip -r briefwright.zip briefwright/` from `skills/`), then Customize > Skills, "+ Add", then "Upload skill", and turn it on. *Expected:* `unzip -l briefwright.zip` lists every entry under `briefwright/`; after the upload, the skill is in your skills list with a toggle. The documentation allows a description of up to 1,024 characters, one help article says 200, and this skill's is 400: record whether the upload accepts it, and any message word for word.
3. **Listed.** Open Customize > Skills. *Expected:* the skill is listed among your uploaded skills, with when it was uploaded ("now" right after the upload), and its toggle on.
4. **Use.** In a new chat, attach `greet.py` and ask as §4 says, naming the attached file instead of "this folder". *Expected:* Claude decides from your request to use the skill, and its thinking shows the skill being loaded; the skill's folder, scripts included, is copied into the code-execution sandbox; then as §4 says, with two differences: the question on where the run executes recommends no harness, since this chat is not where the run executes (answer that it runs in Claude Code), and the two files, written in that sandbox, are offered to download, with no `cd` into the sandbox. Record whether it ran the linter there.
5. **Lint.** Download the two files into a folder `prompts/<task-id>/` and run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** In Customize > Skills, open the skill, turn its toggle off, then choose "…", then "Remove", and confirm. *Expected:* the skill is no longer listed. Delete the zip from `<clone>/skills/`.
7. **Report.** File a harness report issue. *Then:* the claude.ai status in [install.md](install.md) reads `tested on <date>`, since claude.ai shows no version, the README's line under its install commands says so, and the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with them; install.md's note on the description's length says what the upload did; whatever a step contradicted changes here, with its source.

## 11. Antigravity

These steps follow §9's, with the `skills` CLI's README and source at 1.7.2; each *Expected* beyond them is what the run on Antigravity 2.23.0 showed, not Antigravity's documentation.

**Run on 2026-10-13** with Antigravity 2.23.0 and the `skills` CLI 1.7.2: steps 1 to 6. Its status in install.md comes from that run.

1. **Versions.** Record Antigravity's version (on macOS, `defaults read /Applications/Antigravity.app/Contents/Info.plist CFBundleShortVersionString`), `npx skills --version`, the operating system and the date.
2. **Install.** In the scratch repository, run `npx skills add VibeCoding-1/briefwright --skill briefwright -a antigravity`. *Expected:* as §8's Install step: the scope question, answered Project, "Proceed with installation?", the copy in `.agents/skills/briefwright/` and `skills-lock.json`.
3. **Listed.** Run `npx skills list`. *Expected:* it lists `briefwright`, with Antigravity among its agents. Then open the scratch repository in Antigravity, ask a session which skills it can load, and record the answer.
4. **Use.** In the scratch repository opened in Antigravity, ask as §4 says. *Expected:* the agent loads the skill and reads its files, which sit inside the folder; the two files land in `prompts/<task-id>/`; then as §4 says. Record each prompt Antigravity shows, and when.
5. **Lint.** Run `python3 <clone>/skills/briefwright/scripts/lint_prompt.py prompts/<task-id>/master-prompt.md --decisions prompts/<task-id>/decisions.md`. *Expected:* exit 0, no ERROR finding.
6. **Remove.** In the scratch repository, run `npx skills remove briefwright`. *Expected:* it asks you to confirm, then prints `Successfully removed 1 skill(s)`; asked again, a new session no longer names the skill.
7. **Report.** File a harness report issue. *Then:* whatever a step contradicted changes here, with its source; if the Antigravity status in [install.md](install.md) changes, the expected statuses in `tests/test_readme.py` and `tests/test_acceptance.py` change with it.
