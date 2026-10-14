# A "premium" landing page, for an overnight cloud run

The founder of a small supplement brand wants a landing page "at the level of the best in the sector", made tonight by a cloud session working alone. This folder holds a real prompt this skill wrote for that request, in a test run with a model answering its questions: the plan it delivered, trimmed to 3,812 words to match the current skill, with every edit listed at the end.

- **The request**, the person's whole first message, in Spanish:

  > Prepárame el prompt: quiero una landing page para mi marca de suplementos que se vea premium, al nivel de las mejores del sector. Que la haga una sesión en la nube, ella sola, esta noche.

  In English: "Prepare the prompt for me: I want a landing page for my supplement brand that looks premium, at the level of the best in the sector. Have a cloud session build it, on its own, tonight."
- **Size:** standard, unattended. One overnight session of at most eight hours, on a disposable cloud machine, with nobody watching. The skill asked three rounds of numbered questions. A red-team seat found 18 problems in the design, 4 of them critical, and the person approved the changes. A cold read and a review followed. The person's answers are in Spanish in the decisions.
- **The files:**
  - [`master-prompt.md`](master-prompt.md) is what the run reads.
  - [`decisions.md`](decisions.md) holds every decision with its source, the person's words and the check that covers each of them, the red team's findings, the method, the launch steps, and the review.
  - The run also needs a permissions file, which the decisions describe under Launch. It is not copied here.
- **What to look at:**
  - **"Premium" made checkable.** The run captures three reference sites and measures them. Each round, a fresh critic compares the page against them on eight named dimensions. Nineteen scripted checks cover the rest, among them valid HTML, accessibility, no sideways scroll at six widths, a performance score, and a form journey. See the prompt's "The bar".
  - **"Que no prometa que cura nada"** ("it must not promise to cure anything"). The page may state only a closed list of facts. Word lists are enforced by a script, every sentence that names the brand, a product or a number is traced to its source, and a final claims audit reads every sentence. See "Context" and T3–T5 and T21.
  - **Unknowns become visible gaps, never inventions.**
    - The email service: the form posts to a reserved address that never resolves.
    - The company's legal data: marked `[pendiente: …]`.
    - The photos: placeholders at the exact sizes, with a shot list for the photographer.
  - **A night with nobody watching.** A lead delegates and keeps a ledger. It pushes at every close and resumes from files if the cloud machine pauses. A time box and an eight-hour cap end the run. See "Method", "Stop rules and interrupt policy", "Progress and recoverability" and "Run rules".
- **Length:** 3,812 words (`wc -w`), with its seven seat roles in one section. The person's words and the reasons behind each choice are in the decisions.
- **Made with:** Claude Code. Asked which model, the person named one, so the launch steps in the decisions set it. The skill itself names no model.
- **If you reuse it:**
  - Network "Full" and `playwright@latest` in the decisions' launch steps were defaults the test's scripted person accepted for a throwaway machine. A Custom network allowlist and an exact Playwright version are narrower.
  - After the run, remove `.claude/settings.json` from the default branch: its allow rules apply to every later session on that repository.
  - `env-check`, which the decisions' review names, was a tool of the test machine.
- **Names:** the brands the prompt uses as visual references are public sites the skill chose in the test, with no affiliation or endorsement either way. Ardeta, the brand the page is for, comes from the test task.
- **Edits:** in three places, the repository's address is replaced by `https://github.com/<owner>/ardeta-web`. The original address was made up for the test and never contacted, and the GitHub account it named may belong to someone else. The three places are line 7 of the prompt, and the "Coverage" and "Launch" sections of the decisions. Each is marked "(edited: …)". The example was trimmed to match the current skill: first its model section (the one-model setup, its check of which model served each seat and the script that check ran, cut from the prompt, and the same settings from the decisions' launch and review); then the prompt itself, from 10,793 words to 3,812, with the matching rows of the decisions and the current guide's launch block, as the decisions' Review section records. Nothing else is changed.
