# Example Model One: guidance pack

For runs whose model id matches `MATCHES`. Retrieved 2026-10-01. Every line ends with its source: `[KEY #anchor]` (a page under Sources) or `[skill]` with its reason.

## 1. Facts
| Key | Value | Source |
|---|---|---|
| `MATCHES` | `example-model-1` | [SP #ids] |
| `NAME` | `Example Model One` | [SP #ids] |

## 2. Default behaviour
- It widens a small fix into a tidy-up of the code around it unless the prompt bounds the change. [SP #scope]
- It pauses after a milestone to report, as if someone were waiting for the update. [SP #progress]

## 3. Include
### Scope discipline [SP #scope]
When: the run changes code
Where: Run rules, under the working-on heading
Adapt: nothing
```text
Change only what the task names. Leave every file you were not asked to touch exactly as you found it, and list in the final report anything you chose not to change.
```

### Steady progress [SP #progress]
When: autonomy=unattended
Where: Run rules, under the working-on heading
Adapt: nothing
```text
Keep working through the plan without stopping to report a milestone. Put a status note in the same message as your next tool call, never in a message of its own.
```

### Plain final report [SP #report]
When: autonomy=attended
Where: Definition of done and final report
Adapt: the report's file name
```text
Open the final report with the outcome in one sentence, then the evidence for each check, then what is still open.
```

## 4. Leave out
| Leave out | Why | Source |
|---|---|---|
| A line asking for a recap of every step | it lengthens the report without adding evidence | [SP #report] |

## 5. Failure modes and counters
| Failure | What it looks like in a run | Counter (block or rule) | Source |
|---|---|---|---|
| The fix grows into a refactor | files outside the task change | Scope discipline | [SP #scope] |

## 6. Review checks
- PACK-1 The prompt bounds every change to the files the task names. [SP #scope]

## 7. Sources
| Key | URL | Retrieved |
|---|---|---|
| SP | https://example.com/example-model-one/prompting | 2026-10-01 |
