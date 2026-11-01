# Box Score Fact Check

A `nanoagent.plugin/v0001` plugin with the structure of NanoAgent's reference
plugin, [arxiv-source](https://github.com/zeyuyang8/arxiv-source). Its task,
`check-claims`, gives an agent a bundled game of a fictional league: a box
score and ten one-sentence claims about it ("Mara Okafor scored at least 31
points.", "The Bayou Herons scored fewer than 100 points."). The agent must
label each claim `supported`, `contradicted` or `not_found` and cite the
number the box score gives. The answer key pins the box score and each claim's
exact meaning, and a rule-based verifier re-derives every label: 7 constraints,
every one of which must hold. Nothing leaves the machine: the data is bundled
and the plugin declares no network host.

## Tools

| Tool | Does | Code |
|---|---|---|
| `pin_claims` | The answer key. Pins the box score (with the game's sha256) and every claim's meaning (subject, stat, comparator, number) with the label and number the rules give | `src/plugin/factcheck.py`, `src/plugin/rules.py` |
| `read_game` | The box score and the claims' texts. Writes a receipt of what it read to `factcheck/<game>.json` | `src/plugin/factcheck.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `check-claims` | Labels every claim from the box score and submits the verdicts in claim order | `agent`, with `read_game`; reference `pin_claims` |
| `read-game` | Reads a game's box score and claims, so a person can check them | `tool` (`read_game`) |

## The task

Before the agent starts, NanoAgent runs `pin_claims` with the task input in a
scratch workspace the agent never sees, and pins its output. The agent then
has `read_game` and `submit`, and two steps: `read_game` once with the task's
game, then `submit`.

The tool shows; the agent reads and judges. Each claim names one subject (a
player, or "The <team>"), one stat (points, rebounds, assists, minutes) and one
comparison ("at least", "more than", "exactly", "at most", "fewer than") with a
number. A player's number is on their line; a team's number is its points, the
only team stat the box score gives. `supported` when the number satisfies the
comparison, `contradicted` when it does not, `not_found` when there is no
number: the player did not appear, the team did not play, or the claim asks for
a team's rebounds, assists or minutes. `observed` is the number looked up, or
null for a `not_found` claim.

## Ground truth

The ground truth is the pinned game, never a stored label. The rules in
`src/plugin/rules.py` (`verifier/rules.py` is a byte-for-byte copy, enforced
by a test) define everything the verifier re-derives:

- Every claim's **text** is rendered from its meaning by one template
  (`render`), and the data rules refuse a claim whose text differs from its
  rendering, so the meaning the answer key holds is exactly what the agent
  reads.
- **Lookup** and **comparison** are the five comparators on the player's
  line or the team's score; **labels** follow from them.
- A **box score** must be between two different league teams, list every
  player once with non-negative numbers, give at least five players per team
  with the team's score equal to their points, and have a winner.
- Each bundled game's canonical-JSON sha256 is recorded in the rules, so a
  pinned or received game that is not the bundled one is refused.
- **This run's receipt.** The answer key records when it was pinned and
  `read_game` records when it wrote its receipt, both UTC times; a receipt
  written before the answer key was pinned is an earlier run's and fails
  `agent-read`.

The three games (`src/plugin/data.py`) are fictional. Their thirty claims sit
on the boundaries on purpose: the same number under `at_least` (supported)
and `more_than` (contradicted), a team at exactly its score under `at_least`
and `more_than`, `fewer_than` and `at_most` at the number itself, a player
from another game, and a team's rebounds.

## Constraints

`verifier/task.py` judges the submission against 7 constraints, in order.
Every entry of the verdict's `details.constraints` has the keys
`{id, constraint, ok, expected, actual, message}`; `ok` is `true`, `false`, or
`null` when a check it needs did not hold.

| # | id | What it checks |
|---|---|---|
| 1 | `answer-key` | The answer key is pinned for this task's game |
| 2 | `answer-key-data` | The pinned box score and claims are the bundled game (sha256), every text says its meaning, and the pinned labels follow the rules |
| 3 | `task-echo` | The submission names the task's game |
| 4 | `agent-read` | `read_game` was called in this run for this game: its receipt holds the pinned box score and claims and was written after the answer key was pinned |
| 5 | `claims-complete` | Every claim has exactly one verdict, in id order, and no other claim is judged |
| 6 | `labels-exact` | Each label is what the box score gives (the message states the number and the comparison) |
| 7 | `observed-exact` | Each observed number is the box score's, and null exactly for `not_found` |

Valid only when all 7 hold, with score 1.0. Any failure among 1 to 4 scores
0; malformed verdicts (5) score 0; otherwise the score is the share of claims
judged exactly right (label and number), at most 0.99. Every tool call is
checked as well: `verify_output` holds `read_game` to its own receipt and the
bundled hash, and the answer key to the rules applied to the pinned data.

## Limitations

- **Fixed games and claims.** Only the three bundled games and their claims
  can be judged; claims the person writes would need a meaning the verifier
  knows, as the template gives here.
- **The receipt is tied to the run by the clock, not by a run id.** A receipt
  written before the answer key was pinned is refused, so a receipt an earlier
  task left in the workspace no longer passes; two runs of the same game in
  the same second could still share one. A host-given run id would close that.
- **The plan is guidance.** The verdict judges the submission and the receipt,
  not how many tool calls were made.
- **One sentence shape.** Claims follow one template; a claim phrased another
  way ("a double-double", "led all scorers") is outside the task.
- **Exact names.** A player is matched by the exact spelling the box score
  uses; the claims use that spelling, so no fuzzy matching is needed or done.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions (no hosts), tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server (__main__.py), the tools (factcheck.py), the rules (rules.py) and the games (data.py)
├── tests/           # the rules, the tools, the data's hashes, and the verifier on gold, broken, malformed and boundary runs
├── ui/              # how the page draws the outputs: renderers.js and renderers.css (the schema drawing)
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: one module per tool, the task's 7 constraints in task.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

NanoAgent passes the folder the plugin may write to as `NANOAGENT_WORKSPACE`.
`read_game` writes its receipt there, under `factcheck/`, so a run that went
wrong can be read back. Run the tool task from NanoAgent with a config naming
`task: read-game` and a JSON file `{"game": "lynx-herons"}` as its
`arguments`; run the agent task with `nanoagent plugin agent` and the same
input.
