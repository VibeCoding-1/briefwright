# Hidden brief: a length cap for slugger, asked in Spanish

Your opening, in English: "prepare the prompt so another Claude Code session on {MODEL} adds to
slugger an option to cap the slug's length, with its tests". You wrote it in Spanish and you keep
writing to the assistant in Spanish.

What you know, when asked:
- Harness and model: Claude Code, {MODEL} (you already said so); you would be surprised to be
  asked again. Effort: the harness's default.
- The option: slugify(text, max_length=None). When set, the slug is cut at the last hyphen at or before
  max_length characters, never in the middle of a word, and never ends with a hyphen.
- Three of the four existing tests fail today (unicode); fixing that is in scope too, so all four pass.
  The existing tests are never edited; new tests go in slugger/test_max_length.py.
- Standard library only. Launch on this laptop from the command line (a personal machine); you watch it
  (attended); one session. No git commits.
- Anything else: you don't know; accept the recommendation.
