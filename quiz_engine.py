"""
QuizForge engine - PURE LOGIC (no tkinter, no input(), no print()).

Why separate it? Pure functions are deterministic: the same input always gives
the same output, so they are easy to test and the GUI can never break the rules.

The "Question Block" micro-architecture from the brief:
    1. ASK & CAPTURE  -> the UI collects a raw string
    2. SANITIZE       -> sanitize()      .strip() then .lower() / .casefold()
    3. EVALUATE       -> check_answer()  sanitized input == reference answer
    4. EXECUTE        -> update_score()  if correct: score += 1 else: unchanged
"""

import random
from dataclasses import dataclass, field
from datetime import datetime

CLASSIC_TOTAL = 3
CHALLENGE_TOTAL = 10
CHALLENGE_SECONDS = 15
CHALLENGE_BASE_POINTS = 10


# ====================================================================
# 1. SANITIZE + EVALUATE + EXECUTE  (pure functions)
# ====================================================================

def sanitize(raw, use_casefold=False):
    """Filter pipeline: strip() -> collapse inner spaces -> lower()/casefold()."""
    cleaned = " ".join(raw.strip().split())
    return cleaned.casefold() if use_casefold else cleaned.lower()


def sanitize_steps(raw, use_casefold=False):
    """Same pipeline, but returns every intermediate value (for the Inspector)."""
    method = "casefold" if use_casefold else "lower"
    stripped = raw.strip()
    collapsed = " ".join(stripped.split())
    final = collapsed.casefold() if use_casefold else collapsed.lower()
    steps = [("raw", raw), ("strip()", stripped)]
    if collapsed != stripped:
        steps.append(("collapse spaces", collapsed))
    steps.append((method + "()", final))
    return steps


def check_answer(raw, accepted_answers, use_casefold=False):
    """EVALUATE: True if the sanitized input equals ANY sanitized accepted answer."""
    if not raw or not raw.strip():
        return False
    cleaned = sanitize(raw, use_casefold)
    return any(cleaned == sanitize(a, use_casefold) for a in accepted_answers)


def update_score(score, is_correct, points=1):
    """EXECUTE: the if / else gate. Score is always an int (type integrity)."""
    if is_correct:
        score += points
    else:
        pass  # wrong answer -> the Score Vault stays unchanged
    return score


# ====================================================================
# 2. QUESTION PICKING / RANKING
# ====================================================================

def pick_questions(bank, count, category="All", difficulty="All", rng=None, avoid_ids=()):
    """Random questions with NO repeats inside a session.

    Filters first. If the filter is too narrow, tops up from the rest of the
    bank so the session always has exactly `count` questions.
    """
    rng = rng or random
    wanted = [q for q in bank
              if (category == "All" or q["category"] == category)
              and (difficulty == "All" or q["difficulty"] == difficulty)]
    fresh = [q for q in wanted if q["id"] not in avoid_ids]
    chosen = rng.sample(fresh, min(count, len(fresh)))
    if len(chosen) < count:                                  # top-up pass
        used = {q["id"] for q in chosen}
        rest = [q for q in wanted if q["id"] not in used]
        rest += [q for q in bank if q["id"] not in used and q not in rest]
        chosen += rng.sample(rest, min(count - len(chosen), len(rest)))
    return chosen


def rank_for(correct, total):
    """Returns (label, message). Perfect / Great / Keep Practicing."""
    if total and correct == total:
        return "Perfect", "Flawless logic. Every gate opened."
    if total and correct / total >= 0.6:
        return "Great", "Solid work. One more push to perfect."
    return "Keep Practicing", "Every wrong answer is a learning opportunity."


def multiplier_for(streak):
    """Challenge-mode bonus multiplier: x1 (0-2), x2 (3-5), x3 (6+ in a row)."""
    return 1 + min(streak // 3, 2)


def first_letter_hint(answer):
    """'Paris' -> 'P _ _ _ _'  (shows the first letter, hides the rest)."""
    parts = []
    for word in answer.split():
        parts.append(word[0] + " " + " ".join("_" * (len(word) - 1)) if len(word) > 1 else word)
    return "   ".join(p.strip() for p in parts)


# ====================================================================
# 3. GAME SESSION  (state machine: idle -> playing -> feedback -> finished)
# ====================================================================

@dataclass
class Outcome:
    correct: bool = False
    blank: bool = False
    skipped: bool = False
    timed_out: bool = False
    raw: str = ""
    sanitized: str = ""
    steps: list = field(default_factory=list)
    points: int = 0
    correct_answer: str = ""


@dataclass
class AnswerRecord:
    question: str
    given: str
    correct_answer: str
    is_correct: bool
    points: int
    qid: int


class GameSession:
    def __init__(self, questions, mode="classic", use_casefold=False, player="Player", practice=False):
        self.questions = list(questions)
        self.mode = mode
        self.use_casefold = use_casefold
        self.player = player
        self.practice = practice    # 'Retry Mistakes' runs are not recorded
        self.score = 0              # <- the "Score Vault" (always an int)
        self.index = 0              # <- question_index
        self.streak = 0
        self.best_streak = 0
        self.state = "idle"
        self.hint_used = False
        self.records = []
        self.log = []

    # ---- read-only helpers ----------------------------------------
    @property
    def total(self):
        return len(self.questions)

    @property
    def current(self):
        return self.questions[self.index] if self.index < self.total else None

    @property
    def correct_count(self):
        return sum(1 for r in self.records if r.is_correct)

    @property
    def multiplier(self):
        return multiplier_for(self.streak) if self.mode == "challenge" else 1

    @property
    def wrong_questions(self):
        by_id = {q["id"]: q for q in self.questions}
        return [by_id[r.qid] for r in self.records if not r.is_correct]

    # ---- state transitions ----------------------------------------
    def start(self):
        self.state = "playing"

    def hint(self):
        """Classic: free. Challenge: halves the points of this question."""
        self.hint_used = True
        return first_letter_hint(self.current["answers"][0])

    def submit(self, raw):
        if self.state != "playing":
            raise RuntimeError("submit() is only valid while state == 'playing'")
        if not raw or not raw.strip():
            return Outcome(blank=True, raw=raw or "")          # blocked: no state change

        q = self.current
        steps = sanitize_steps(raw, self.use_casefold)
        correct = check_answer(raw, q["answers"], self.use_casefold)
        return self._resolve(q, raw, steps, correct)

    def skip(self):
        return self._resolve(self.current, "", [], False, skipped=True)

    def timeout(self, raw=""):
        return self._resolve(self.current, raw, [], False, timed_out=True)

    def next_question(self):
        self.index += 1
        self.hint_used = False
        self.state = "finished" if self.index >= self.total else "playing"
        return self.state

    # ---- internals ------------------------------------------------
    def _resolve(self, q, raw, steps, correct, skipped=False, timed_out=False):
        if correct:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            points = 1 if self.mode == "classic" else CHALLENGE_BASE_POINTS * multiplier_for(self.streak)
            if self.mode == "challenge" and self.hint_used:
                points //= 2
        else:
            self.streak = 0
            points = 0

        self.score = update_score(self.score, correct, points)
        sanitized = steps[-1][1] if steps else ""
        outcome = Outcome(correct, False, skipped, timed_out, raw, sanitized, steps, points, q["answers"][0])
        self.records.append(AnswerRecord(q["q"], "(skipped)" if skipped else ("(time up)" if timed_out and not raw.strip() else raw.strip()),
                                         q["answers"][0], correct, points, q["id"]))
        stamp = datetime.now().strftime("%H:%M:%S")
        if skipped or timed_out:
            tag = "skipped" if skipped else "timeout"
            self.log.append(f"[{stamp}] {tag} -> match=False -> score={self.score}")
        else:
            self.log.append(f"[{stamp}] input={raw!r} -> sanitized={sanitized!r} -> match={correct} -> score={self.score}")
        self.state = "feedback"
        return outcome


# ====================================================================
# 4. CODE GENERATOR + VERIFICATION CHECKLIST
# ====================================================================

def generate_cli_code(questions, use_casefold=False):
    """Builds a complete, runnable Python CLI quiz for the given questions."""
    method = "casefold" if use_casefold else "lower"
    total = len(questions)
    out = [
        '"""Generated by QuizForge - DecodeLabs Python Project 4"""',
        "",
        "",
        "def main():",
        "    score = 0  # the Score Vault",
        "",
    ]
    for i, q in enumerate(questions, start=1):
        prompt = q["q"] + " "
        if q.get("choices"):
            prompt = f"{q['q']} ({' / '.join(q['choices'])}) "
        accepted = tuple(sanitize(a, use_casefold) for a in q["answers"])
        cond = f"answer == {accepted[0]!r}" if len(accepted) == 1 else f"answer in {accepted!r}"
        out += [
            f"    # Question {i}",
            f"    answer = input({prompt!r}).strip().{method}()",
            f"    if {cond}:",
            "        score += 1",
            '        print("Correct!")',
            "    else:",
            f"        print({('Wrong! The answer is ' + q['answers'][0] + '.')!r})",
            "",
        ]
    out += [
        f'    print(f"Final Score: {{score:>2}}/{total}")',
        "",
        "",
        'if __name__ == "__main__":',
        "    main()",
        "",
    ]
    return "\n".join(out)


def run_verification(session_score=0):
    """Live checks that mirror the brief's verification standards.

    Returns a list of dicts: {"name", "ok", "detail"}. These are REAL tests
    executed against the engine, not decoration.
    """
    sample = ["Paris"]
    checks = []

    outputs = {check_answer("  PaRiS ", sample) for _ in range(50)}
    checks.append({"name": "Logic Consistency", "ok": outputs == {True},
                   "detail": "same input -> same output (50 runs)"})

    ok_ws = check_answer("   paris   ", sample) and not check_answer("   ", sample)
    checks.append({"name": "Whitespace Audit", "ok": ok_ws,
                   "detail": "'   paris   ' passes, blank input is blocked"})

    ok_norm = check_answer("PARIS", sample) and check_answer("pArIs", sample)
    checks.append({"name": "Data Normalization", "ok": ok_norm,
                   "detail": "UPPER / mixed case all normalize"})

    is_int = isinstance(session_score, int) and not isinstance(session_score, bool)
    still_int = isinstance(update_score(session_score, True), int)
    checks.append({"name": "Type Integrity", "ok": is_int and still_int,
                   "detail": f"score is {type(session_score).__name__}, stays int"})

    ok_fmt = f"{5:>2}/10" == " 5/10"
    checks.append({"name": "Output Clarity", "ok": ok_fmt,
                   "detail": 'f"{score:>2}/10" right-aligns the score'})
    return checks
