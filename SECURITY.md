# Security policy

## Reporting a vulnerability

Report it privately, through GitHub's private vulnerability reporting: open this repository's **Security** tab and choose **Report a vulnerability**, or go straight to <https://github.com/VibeCoding-1/briefwright/security/advisories/new>. Please do not open a public issue, pull request or discussion about it.

Say what is affected, how to reproduce it, and what an attacker gains. You will get a first reply within 14 days. The fix is developed in a private advisory, released, and then the advisory is published with credit to you unless you ask otherwise.

## Scope

- **The scripts:** the prompt linter inside the skill, the tools in `tools/`, the tests and the eval harness.
- **The workflows** in `.github/workflows/`, the optional Codex review included: a secret reachable from a fork, a write permission where none is needed, or text from a pull request that reaches a shell or a model's instructions.
- **Prompts that could leak secrets:** any text of the skill that, followed as written, would lead a run to print, commit or send a credential, or to run with wider permissions than the person agreed to — a launch command, an allowlist, a permission setting, a run rule that commits or pushes.

Out of scope: the agent harnesses and models themselves (report those to their vendors), and a model that ignores a prompt's instructions without any flaw in the text.

## Supported versions

The latest release. Fixes are not backported.
