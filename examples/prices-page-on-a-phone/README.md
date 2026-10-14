# The prices page on a phone

A shop's prices page scrolls sideways on a phone. This folder holds a real prompt this skill wrote for that request, in a test run with a model answering its questions, exactly as it was delivered, apart from the edits listed at the end.

- **The request**, the person's whole first message:

  > Hi, can you write me a prompt for Opus 5.5 to fix the prices page on my shop's website? The files are all in this folder. On my phone the price table runs off the right-hand side and you have to scroll sideways to see the prices. It must never scroll sideways on a phone. On the laptop it looks fine and I want it to stay like that. And please don't change any of the prices or the wording. I'll be sat at my desk while it works, so it can just ask me if it needs anything.

- **Size:** quick. One CSS fix to a static site of four files, in one attended session of about half an hour. The skill asked one round of three questions and started no subagent; the prompt has the run work alone.
- **The files:**
  - [`master-prompt.md`](master-prompt.md) is what the person pastes into a new session.
  - [`decisions.md`](decisions.md) holds every decision with its source, the person's words and the check that covers each of them, the launch command, and the review.
- **What to look at:**
  - The cause the person had not noticed. Before asking anything, the skill read the CSS and found that the opening-hours box is too wide as well (the prompt's "The causes"; D3 in the decisions).
  - Each of the person's three demands becomes a check. T1 measures every width from 320 to 1920 px and every element on the page. T2 compares the laptop view, pixel for pixel, with a copy taken before the first edit. T3 compares the words and prices.
  - The wrong fixes are ruled out in advance, each with its reason. The check has to be seen failing before the first edit ("prove it first").
  - The person is at the desk, so the look on a phone is theirs to approve (T5). So is any question about the look that Scope does not settle.
  - The person's words and the reasons behind each choice are in the decisions, not the prompt, which is 698 words (`wc -w`).
- **Made with:** Claude Code. The person named a model, so the launch command in the decisions sets it. The skill itself names no model.
- **The test machine's tools:** `py`, the Python with Playwright that the prompt names, and `env-check` were tools of the test machine. A run on your machine uses your own Python.
- **Edits:** in three places, the working folder's path is replaced by `$HOME/shop-website`. The original path was a scratch folder on the test machine. The three places are line 7 of the prompt, and the framing line and the launch block of the decisions. Each is marked "(edited: …)", the framing line's on the line below it. The example was trimmed to match the current skill: its model text (the opening line's model sentence, the closing check of which model had served the session, the launch's subagent-model setting), then the prompt itself, from 1,614 words to 698, with the matching rows of the decisions and the launch's wording, as the decisions' Review section records. Nothing else is changed.
