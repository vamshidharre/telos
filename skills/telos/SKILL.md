---
name: telos
description: >
  Autonomous Dual-Loop Engineering Runtime for coding agents. Replaces procedural
  prompting with End-State Invariant specifications. Features an Inner Loop
  (Hill-Climbing Plateau Engine) for step-wise progress and an Outer Loop
  (Binary Verification Gate) for zero-hallucination validation with automatic
  git-backed rollback on regressions.
license: MIT
---

# TELOS — Autonomous Dual-Loop Engineering Runtime

> *"Your attention is the bottleneck. When working with agents everything is a loop. The more you're involved in that loop the more of a bottleneck you become... Avoid over-describing what you want in prompts; focus only on the end state or goal, and along with your verification loops let the model get there by itself."*  
> — **Daisy Hollman**, Anthropic (Claude Founder House)

---

## THE CORE PREMISE

Frontier LLMs excel at planning paths when provided with **crisp, testable end-states**. Micromanaging every line of code or step in a prompt slows down execution and degrades model reasoning. 

**Telos** flips the paradigm:
1. **Specify the End-State (Telos)**: Define non-negotiable invariants and objective metrics in `telos.yaml`.
2. **Execute via Dual Loops**:
   - **Outer Loop (The Verifier)**: A strict binary gate (PASS / FAIL). Does the code meet all criteria?
   - **Inner Loop (The Hill-Climber)**: Atomic plateau-to-plateau ascent. Propose small improvements, measure score deltas, lock plateaus, and automatically revert regressions.
3. **Preserve Human Attention**: The agent operates fully autonomously within its cycle budget until the goal is proven with hard evidence.

---

## THE 5 INVARIANTS OF TELOS

1. **End-State Over Procedure**: Focus entirely on the destination (`telos.yaml`). Never dictate line-by-line procedural steps if an invariant or test can verify it.
2. **Binary Verification Gate**: Verification is strictly boolean. Output is either `VERDICT: PASS` or `VERDICT: FAIL` with concrete stdout/stderr diagnostic traces. Self-review or prose assurances are never accepted as proof.
3. **Plateau-to-Plateau Ascent**: Break non-trivial goals into atomic, measurable gradients. Each improvement is locked as a git-backed plateau (`telos-plateau-<n>`).
4. **Zero-Cost Rollback on Regression**: If an exploratory step breaks an invariant or regresses the objective metric, the runtime immediately reverts the working tree to the latest confirmed plateau.
5. **Fail-Closed Truthfulness**: Never claim completion without a fresh passing run of all invariants after the last mutation. If an invariant cannot be run, report it as unverifiable.

---

## WORKFLOW: HOW TO OPERATE TELOS

### 1. Initialize or Load Contract
Examine `telos.yaml` in the repository root:

```yaml
goal: "Refactor data parser to zero-copy streaming and achieve < 25ms p99 latency"

invariants:
  - "pytest tests/ -k test_parser"
  - "ruff check src/"

metric:
  command: "python benchmarks/parse_benchmark.py"
  direction: "minimize"
  target: 25.0

allowed_scope:
  - "src/parser/**"
  - "tests/parser/**"

budget:
  max_cycles: 10
  timeout_sec: 60
```

### 2. The Verification Loop (Outer Gate)
Run the verifier before and after work:
```bash
telos check
```
- If all invariants pass: returns `VERDICT: PASS` (exit code 0).
- If any invariant fails: outputs diagnostic trace with failed commands, exit codes, and stderr. Feed this trace directly into your next reasoning step.

### 3. The Hill-Climbing Loop (Inner Ascent)
Make an atomic mutation within `allowed_scope`, then evaluate the step:
```bash
telos climb -m "optimize buffer allocation in parser stream"
```
The runtime automatically:
1. Verifies that no files outside `allowed_scope` were touched.
2. Runs all acceptance invariants.
3. Measures the objective metric and computes the delta against the previous plateau.
4. **If improved or held**: Automatically commits and tags `telos-plateau-<N>`.
5. **If regressed or broke invariants**: Automatically executes `git reset --hard` back to the last good plateau, keeping your repository clean.

### 4. Manual Rollback
If you ever hit a dead end or unwanted experimental drift:
```bash
telos rollback
```

### 5. Check Status & History
```bash
telos status
telos history
```

---

## PROMPT GUIDELINES FOR AGENTS

When assigned a task under Telos:
- **Do not ask the user for routine confirmation.** Your cycle budget is your permission.
- **Formulate one atomic hypothesis per cycle.** Do not rewrite the entire repository in one shot.
- **Inspect failures as signals.** When `telos check` or `telos climb` fails, use the stdout/stderr diagnostic to adjust your next hypothesis.
- **Terminate cleanly.** When all invariants pass and metric targets are satisfied, present the final plateau evidence summary to the user.
