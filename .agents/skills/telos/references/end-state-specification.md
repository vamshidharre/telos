# End-State Specification (Telos)

## Why Procedural Prompting Fails Frontier Models
Older prompt engineering patterns relied heavily on procedural hand-holding:
- *"Step 1: Open file X and find class Y..."*
- *"Step 2: Add an if-statement on line 42..."*
- *"Step 3: Update import Z..."*

With modern frontier LLMs (Claude 3.7/Opus, Gemini 1.5/2.0 Pro, GPT-4o), procedural prompting creates significant drawbacks:
1. **Model blindness**: The model blindly follows instructions even when edge cases or better architectural approaches exist.
2. **Fragile workflows**: A small discrepancy in file state breaks the entire procedural prompt.
3. **Maintenance overhead**: The prompt must be constantly rewritten as code evolves.

## The Telos Paradigm: Declarative Invariants
Instead of dictating the journey, declare the **destination**:
- What must be true when the task is complete?
- What invariants must remain unbroken?
- What metric defines progress?

### Structure of a Telos Contract (`telos.yaml`)

```yaml
goal: "Describe the observable end-state in unambiguous natural language"

invariants:
  - "Command 1 that must exit with returncode 0"
  - "Command 2 that enforces types / lints / format"

metric:
  command: "Command that prints a numeric score"
  direction: "minimize" # or "maximize"
  target: 10.0 # threshold that defines completion

allowed_scope:
  - "src/relevant_module/**"
  - "tests/**"

budget:
  max_cycles: 10
  timeout_sec: 60
```
