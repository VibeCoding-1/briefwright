# <Model name>: guidance pack

For runs whose model id matches `MATCHES`. Retrieved <YYYY-MM-DD>. Every line ends with its source: `[KEY #anchor]` (a page under Sources) or `[skill]` with its reason.

## 1. Facts
| Key | Value | Source |
|---|---|---|
| `MATCHES` | `<model-id>` (a list, comma-separated; a trailing `*` matches a prefix) | |
| `NAME` | `<the model's name as its maker writes it>` | |

## 2. Default behaviour
- <what the model does unprompted that a prompt must allow for> [KEY #anchor]

## 3. Include
### <Block name> [KEY #anchor]
When: <a fact of the task; never a size, a run length or "always">
Where: <the prompt section, or a brief>
Adapt: <the only change allowed, or "nothing">
```text
<the block, in words its source licenses for reuse, or the pack author's own>
```

## 4. Leave out
| Leave out | Why | Source |
|---|---|---|

## 5. Failure modes and counters
| Failure | What it looks like in a run | Counter (block or rule) | Source |
|---|---|---|---|

## 6. Review checks
- PACK-1 <a line the reviewer checks> [KEY #anchor]

## 7. Sources
| Key | URL | Retrieved |
|---|---|---|
