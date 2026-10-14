# Hidden brief: quick slugger fix, the harness and the model stated

You maintain a tiny Python utility, slugger, in the folder this session runs in; the prompt is for
that same folder. You want another session to fix it; you start that session yourself in Claude Code,
from the command line on this machine, your personal laptop, and you watch it.

What you know, when asked:
- Harness and model: Claude Code, {MODEL} (you already said so); effort: the harness's default.
- The four tests in slugger/test_slugger.py are the oracle. The session must not edit them. If it
  believes a test is wrong, it stops and tells you instead of changing it.
- slugify keeps its name and signature; standard library only (unicodedata is fine); it may add a
  helper inside slugger.py but no new files.
- Done means: `python3 -m unittest discover -s slugger` passes with all four tests, and
  slugger/test_slugger.py is unchanged.
- Run size: one short session.
- No git commits: you review the diff yourself.
- Anything else (CI, packaging, other Python versions): you don't know; accept the recommendation.
