# Writing the master prompt

How to write inside the anatomy of `templates/master-prompt.md`. The reader is a strong model with nothing but the file and the folder: write outcomes, not ceremony, and give it every value it cannot find, once.

## 1. Rules

- **Exact values verbatim.** Paths, numbers, names, strings, versions, resolutions, file names, and the person's own words for things: a paraphrase loses them first.
- **Prohibitions verbatim, each beside its target.** A "never" line the person gave stays word for word. Every fence in `Do not build` carries its reason and the positive target next to it ("no account system — the tool is single-user; state lives in one local file"), because a bare ban makes the banned thing more available, not less.
- **Numbers, not adjectives.** Give the number, or the rule that derives it; a soft adjective the interview did not quantify does not appear.
- **Each thing said once.** Mission, Scope and the bar never restate one another; a constraint stated in one section is cited elsewhere; the wait rule points at the bar's ids; what every seat brief shares is said once in § Subagent contracts.
- **The prompt carries what the executor acts on.** The person's words, the reasons behind choices, rejected options and sources stay in `decisions.md`. A reason goes in the prompt only where it changes a judgment, in the same sentence ("do not implement yourself: your context is the run's memory").
- **Every step ends on a checkable condition.** "Build the graybox covering every zone, then render the preview set" has a bound; "build the graybox" does not.
- **Enumerate where it does work:** the facets to research, the dimensions to test, the states to capture.
- **Independence where self-assessment fails** (visual checks, reviews, anything subjective): name who is independent and what they are denied.
- **Action verbs for builders.** "Change", "build", "run" — never "could you suggest", which a strong model takes literally.
- **No placeholder but `[you fill this in: …]`**, for a fact only the person holds, each listed in `decisions.md` § Placeholders; "TBD", "as needed", "handle edge cases" are plan failures. Every slot in an appendix brief has its value stated in the prompt, or rounds stop being comparable.
- **Every loop carries its exits** (`references/methods.md` §9), the late verification pass included.
- **Formatting follows the output wanted:** numbered steps where order matters, bullets for a set, tables for rubrics, fences for commands, an example for a format easier shown than described.
- **Portable.** No "as discussed", no path relative to this session, no file the executor cannot reach, no mention of this skill or of the conversation.

## 2. What the strongest published prompts add

- **Priorities ranked, and the ranking is the cut order.** Mission lists the outcomes the person ranked and says: "If something must be cut, cut from the bottom of this ranking, never the top item."
- **Settled facts frozen.** Context's `Fixed — do not reopen` list carries each decided choice with its reason, each pinned version with the date it was checked, and each known pitfall exploration found, so the executor spends nothing re-deciding them.
- **Risky choices with a fallback.** Each names its fallback and when to take it: a time, or a number of failed attempts.
- **Criteria numbered and observable.** `T1…Tn`, each a command with its expected exit code or an observation with the artefact that shows it; each seat reports against the ids.
- **The weak result named.** One line starting "A weak result" says what separates a weak result from a strong one; it goes to every critic and the reviewer as well.
- **Cuts are honest and greppable.** Anything stubbed or cut carries `STUB: <what and why>` in the code and in the report, and `grep -rn "STUB:"` runs before done, so a cut is never mistaken for a feature.
- **Done as a user journey** when the deliverable is something a person uses: one paragraph walking through every feature, each step mapped to its `T` id.
- **A branch for each uncertain capability:** "If you can …, do …; if you cannot, …", so the executor adapts instead of stalling or inventing.
- **Closed-world facts.** Factual content (names, dates, figures, quotations) comes from a verified list in the prompt or a named source file; "if in doubt, leave it out". No API, flag, version or function appears unless it was seen to exist.
- **Invented names.** Generated content uses fictional brands and people, and no real logo or trademark the person does not own.
- **A closing sentence for two readers** (what an expert and a newcomer should each see) may frame the Mission; it is never a bar item.

## 3. Grounding, when the deliverable makes claims

For a report, research, documentation, copy or analysis: restrict the executor to the named material; have it extract the exact quotes it will rely on before writing; after writing, have it find a supporting quote for every claim and delete, visibly, any claim it cannot support; and allow it to say it could not verify something.

## 4. Pasted and published text

- The prompt holds no HTML comment outside fences and inline code: no marker, allowance or template comment.
- A guidance pack's §3 block goes in only on a task fact its *When* names, never a size: its fenced text, bare, changed only as *Adapt* allows; its provenance is its § Guidance put in row, not a mark.
- Model-specific wording comes only from a pack: its blocks, and nothing its §4 lists. No line names a ledger or seats the method lacks.

## 5. Order

**Instructions first**, in the template's order, for most prompts. **Documents first** when the prompt must embed long material (a spec, transcripts): the material at the top in tagged documents, the instructions after — a query placed after long documents is answered better. Material in the working folder is named by its path in Context, not embedded, unless the executor cannot otherwise reach it or must not misread it. The wait rule is always the last paragraph before the appendices.

## 6. Self-check

Before Phase 4, read the prompt as the executor, in a fresh session, with only the file and the folder:

- Can I start without asking anything? Is every fact here or at a named path?
- Do I know where to work and what not to touch?
- Do I know when I am done, and what evidence proves it — and can each named checker observe what its criterion asks?
- Do I know what to do on a plateau, at a gate, past the budget?
- Where the prompt has seats, how do I give each its model, and what do I do if I cannot start one?
- Would removing any paragraph change nothing, or is anything said twice? Then it goes.
- Does any sentence only make sense inside the conversation that produced it?

Then, with `decisions.md`: walk § The person's words (each row carried in its section as given, checked by its bar item or stated reason), then reread the request and every answer for a demand with no row; confirm each § Guidance put in fact holds.
