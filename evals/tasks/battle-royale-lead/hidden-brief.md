# Hidden brief: browser battle royale, attended

You want a browser game in the battle royale genre: one playable round, the player against bots, the
zone shrinking until one survivor is left. Original name and art (call it Stormfall if asked); other
games of the genre are a reference for mechanics only.

What you know, when asked:
- Machine: your Linux desktop, no GPU; Claude Code from the command line; you launch it yourself and stay
  around to answer (attended); one session.
- Model: {MODEL} (you already said so); effort: the harness's default.
- Stack: TypeScript with Three.js, served by Vite; Node 22 is installed. Installing npm packages is
  fine, with pinned versions.
- Scope of this prompt: the first playable round only; building, multiplayer and progression are later
  increments.
- Bots: 15, with simple behaviour (wander, shoot on sight, flee the zone).
- Done means: a playtest where a round starts, the zone shrinks, bots fight, and the round ends with a
  winner screen, at 30 frames per second or more in Chrome on your machine.
- Parallel seats: at most three at a time.
- Git: the working folder is a fresh repository; the lead commits after each piece; there is no remote.
- Anything else: you don't know; accept the recommendation.
