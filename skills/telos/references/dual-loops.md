# The Dual-Loop Mechanism

## Loop 1: The Verification Gate (Outer Loop)
The Verification Loop answers one question:
> **Does the system satisfy all criteria right now? (Yes/No)**

- **Strictly Boolean**: No partial credit, no soft evaluations.
- **Fail-Closed**: If a command times out or exits non-zero, it fails.
- **Diagnostic Signal**: When an invariant fails, Telos captures the exit code, stdout, and stderr to serve as diagnostic backpressure for the agent.

## Loop 2: The Hill-Climber (Inner Loop)
The Hill-Climber answers:
> **Did this small step bring us closer to the top of the hill?**

For non-trivial engineering tasks (e.g. performance tuning, massive refactoring, fixing a suite of 20 broken tests), jumping directly from initial state to final goal in a single prompt often fails.

The hill-climbing loop breaks the ascent into plateaus:
1. **Hypothesize**: Formulate one atomic change.
2. **Mutate**: Apply the change within `allowed_scope`.
3. **Evaluate**:
   - Check scope violations.
   - Run outer invariants.
   - Run metric command and compute delta.
4. **Decide**:
   - **Progress / Plateau**: Lock the plateau (git commit & tag).
   - **Regression / Invariant Break**: Revert working tree automatically via `git reset --hard` to the prior plateau.
