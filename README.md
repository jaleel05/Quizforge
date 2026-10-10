# QuizForge - The Decision Engine

> DecodeLabs Python Programming - **Project 4: The General Knowledge Quiz**
> Complete Python. Zero dependencies. Emerald Ink + Champagne design.



## What it teaches (the brief)

Every question runs the same **Question Block**:

| Step | What happens | Python |
|------|--------------|--------|
| 1. Ask & Capture | read the raw string | `raw = input(...)` |
| 2. Sanitize | filter pipeline | `.strip().lower()` (or `.casefold()`) |
| 3. Evaluate | compare to the reference | `answer == "paris"` |
| 4. Execute | the `if / elif / else` gate | `score += 1` or leave unchanged |

The score is an `int` initialised as `score = 0` (the **Score Vault**).
Architecture follows **IPOS**: Input -> Process -> Output, plus Storage.

## Run it

```bash
python app.py        # the full GUI
python cli.py        # the plain terminal version (exact structure of the brief)


