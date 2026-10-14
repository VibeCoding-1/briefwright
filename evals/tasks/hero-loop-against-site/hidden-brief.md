# Hidden brief: a critic loop on the Slugger Cloud hero section

hero.html, in the working folder, is the hero section of Slugger Cloud, your slug-as-a-service
product. You want a builder/critic loop that improves it until three fresh critics, judging
screenshots side by side with linear.app's hero, agree yours is at least as good.

What you know, when asked:
- You want a prompt for another session to run the loop; you do not want the loop run now.
- Where it runs: Claude Code, started from the command line on this laptop (a personal machine);
  effort: the harness's default. You name no model; if asked for one, say the run may choose.
- Scope: hero.html only (inline CSS allowed), no framework; the copy may be rewritten, but the product
  name and the sign-up button stay.
- What "better" is judged on: visual hierarchy, typography, spacing and the clarity of the call to
  action; not animation.
- The reference: the homepage hero of https://linear.app, rendered at 1440x900 on the day of the run;
  screenshots with headless Chromium (Playwright is installed).
- Stop: when three fresh critics agree, or on a plateau (two rounds with no improvement), with an
  honest report.
- You are around while it runs (attended); one session. Git: commit each round's version on the current
  branch; no push.
- Anything else: you don't know; accept the recommendation.
