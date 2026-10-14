# Hidden brief: a command line for slugger, the harness not named

You maintain slugger (slugger/slugger.py and its tests, in the folder this session runs in). You want
a command-line entry point: `python3 -m slugger "Some Text"` prints `some-text`; `--max-length N` cuts
the slug at a word boundary; the exit code is 2 on bad arguments.

What you know, when asked:
- Where it runs: Claude Code, started from the command line on this laptop (a personal machine);
  effort: the harness's default. You name no model; if asked for one, say the run may choose. You
  give this answer once; if asked again, say you already answered.
- You are around while it runs (attended); one session.
- Three of the four existing tests fail today (unicode). Fixing slugify is in scope too, so that all
  four pass. The existing test file is never edited; the new tests go in slugger/test_cli.py.
- Standard library only (argparse); Python 3.9 or newer.
- Git: commit at the end on the current branch; no push.
- Anything else: you don't know; accept the recommendation.
