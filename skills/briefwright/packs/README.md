# Guidance packs

A guidance pack adds model-specific wording to the prompts written for runs on one model. It is optional and never needed: with no pack, the prompt is complete. None ships here; `TEMPLATE.md` is the empty format to start one.

## How a pack is chosen

- A pack is a file `packs/<pack-id>.md` in this folder.
- In Phase 0, once decision `D1` records a model the person named, the folder is listed, skipping `README.md` and `TEMPLATE.md`, and the one pack whose `MATCHES` cell names the framing's `model=` is read. An exact id matches, and so does a prefix ending in `*`. With `model=choose`, no pack is read.
- With no match, no pack is read. With two or more, none is read and the person is told; packs are never merged.

## What a pack may add

- **Blocks** (§3), each put in only on the task fact its `When:` names, never a size, a run length or "always": its fenced text, bare, changed only as its `Adapt:` line allows, in the section or brief its `Where:` names, each recorded as a row of `decisions.md` § Guidance put in (`references/writing-rules.md` §4).
- **Text to leave out** (§4): wording the prompt must not carry for that model.
- **Failure modes and their counters** (§5), each counter a block of §3 or a rule this skill already has.
- **Review checks** (§6): lines the reviewer brief pastes as `{PACK_CHECKS}` (`references/review.md` §4).

## What a pack never changes

A pack never changes a rule of this skill. It cannot change the hard rules, the ceremony table (`references/methods.md` §12), the run rules, any frozen text, the model guideline, or the verification wording V1 and V2. It cannot choose a model for any seat, or recommend a vendor or a model. Launch facts, effort and delegation belong to the harness guides and `references/methods.md` §10, not to a pack.

## Writing one

- Copy `TEMPLATE.md` and keep its headings. Every line ends with its source: `[KEY #anchor]`, a page listed under §7 Sources with its URL and retrieval date, or `[skill]` with its reason.
- Each §3 block has exactly one `When:`, one `Where:` and one `Adapt:` line, then one fenced `text` block.
- Write the blocks in your own words. Copy published text only where its source's terms allow redistribution, and name that source.
