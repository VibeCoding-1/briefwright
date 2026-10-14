# Hidden brief: a command line for slugger, unattended in Codex

You maintain slugger (slugger/slugger.py and its tests, in the folder this session runs in). You want
a command-line entry point: `python3 -m slugger "Some Text"` prints `some-text`; `--max-length N` cuts
the slug at a word boundary; the exit code is 2 on bad arguments.

What you know, when asked:
- Harness and model: the Codex CLI, started headless with `codex exec` on this laptop (a personal
  machine); model {MODEL} at high reasoning effort (you already said so).
- Unattended: you start it in the evening and read the result in the morning; nobody answers questions.
  A wall-clock cap of four hours if a cap is asked for. Sandbox: workspace-write.
- Three of the four existing tests fail today (unicode). Fixing slugify is in scope too, so that all
  four pass. The existing test file is never edited; the new tests go in slugger/test_cli.py.
- Standard library only (argparse); Python 3.9 or newer.
- Git: commit at the end on the current branch; no push.
- Anything else: you don't know; accept the recommendation.
