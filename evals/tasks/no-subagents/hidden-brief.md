# Hidden brief: a length cap for slugger, in a harness with no subagents

Wrenchbox is your company's in-house agent runner: you open a session in a folder, pick a model from a
list, and paste the first message. It loads AGENTS.md as project instructions. It cannot start
subagents: a session is one agent, nothing more.

What you know, when asked:
- Model: {MODEL}, written exactly so; effort: Wrenchbox has no effort setting.
- You are around while it runs (attended); one session, on this laptop (a personal machine).
- The review: you want the change reviewed against the request before it counts as done. If told that
  without subagents the review runs in the same session and is not independent, accept that and keep
  the review.
- The option: slugify(text, max_length=None). When set, the slug is cut at the last hyphen at or before
  max_length characters, never in the middle of a word, and never ends with a hyphen.
- Three of the four existing tests fail today (unicode); fixing that is in scope too, so all four pass.
  The existing tests are never edited; new tests go in slugger/test_max_length.py.
- Standard library only. Git: commit at the end on the current branch; no push.
- Anything else: you don't know; accept the recommendation.
