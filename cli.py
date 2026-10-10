"""
QuizForge - the plain CLI version (the exact structure from the brief).

    score = 0
    for each question:  input -> .strip().lower() -> == -> if / else
    print(f"Final Score: {score:>2}/3")

Run:  python cli.py
"""

from quiz_engine import CLASSIC_TOTAL, check_answer, pick_questions, sanitize, update_score
from questions import QUESTIONS


def main():
    print("=== QuizForge - General Knowledge Quiz ===\n")
    score = 0                                        # the Score Vault
    questions = pick_questions(QUESTIONS, CLASSIC_TOTAL)

    for number, q in enumerate(questions, start=1):
        prompt = f"Q{number}. {q['q']} "
        if q.get("choices"):
            prompt = f"Q{number}. {q['q']} ({' / '.join(q['choices'])}) "

        raw = input(prompt)                          # 1. ASK & CAPTURE
        while not raw.strip():                       # empty-input guard
            raw = input("   Please type an answer: ")

        answer = sanitize(raw)                       # 2. SANITIZE  (.strip().lower())
        correct = check_answer(raw, q["answers"])    # 3. EVALUATE  (==)

        if correct:                                  # 4. EXECUTE   (if / else gate)
            score = update_score(score, True)
            print("   Correct!\n")
        else:
            print(f"   Wrong! You typed {answer!r}. The answer is {q['answers'][0]}.\n")

    print(f"Final Score: {score:>2}/{CLASSIC_TOTAL}")


if __name__ == "__main__":
    main()
