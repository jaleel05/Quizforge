"""
Sanity tests for the pure logic. No GUI needed.

Run:  python -m unittest -v
"""

import builtins
import contextlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import storage
from questions import QUESTIONS
from quiz_engine import (GameSession, check_answer, first_letter_hint, generate_cli_code, multiplier_for,
                         pick_questions, rank_for, run_verification, sanitize, sanitize_steps, update_score)


class SanitizeTests(unittest.TestCase):
    def test_strip_and_lower(self):
        self.assertEqual(sanitize("  PaRiS  "), "paris")

    def test_inner_spaces_collapse(self):
        self.assertEqual(sanitize("  Vatican    City "), "vatican city")

    def test_casefold_vs_lower(self):
        self.assertEqual(sanitize("Straße", use_casefold=False), "straße")
        self.assertEqual(sanitize("Straße", use_casefold=True), "strasse")

    def test_deterministic(self):
        self.assertEqual({sanitize(" X ") for _ in range(100)}, {"x"})

    def test_steps_end_with_final_value(self):
        self.assertEqual(sanitize_steps("  PaRiS  ")[-1], ("lower()", "paris"))


class CheckAnswerTests(unittest.TestCase):
    def test_correct_variants(self):
        for raw in ("paris", "PARIS", "  Paris ", "pArIs"):
            self.assertTrue(check_answer(raw, ["Paris"]), raw)

    def test_wrong_and_blank(self):
        self.assertFalse(check_answer("london", ["Paris"]))
        self.assertFalse(check_answer("   ", ["Paris"]))
        self.assertFalse(check_answer("", ["Paris"]))

    def test_aliases(self):
        for raw in ("USA", "u.s.a", " United States "):
            self.assertTrue(check_answer(raw, ["USA", "U.S.A", "United States"]), raw)

    def test_type_integrity(self):
        self.assertFalse(check_answer("1", ["01"]))


class ScoreTests(unittest.TestCase):
    def test_if_else_gate(self):
        self.assertEqual(update_score(0, True), 1)
        self.assertEqual(update_score(2, False), 2)
        self.assertIsInstance(update_score(0, True), int)

    def test_multiplier(self):
        self.assertEqual([multiplier_for(n) for n in (0, 2, 3, 5, 6, 20)], [1, 1, 2, 2, 3, 3])

    def test_rank(self):
        self.assertEqual(rank_for(3, 3)[0], "Perfect")
        self.assertEqual(rank_for(2, 3)[0], "Great")
        self.assertEqual(rank_for(1, 3)[0], "Keep Practicing")

    def test_hint(self):
        self.assertEqual(first_letter_hint("Paris"), "P _ _ _ _")


class SessionTests(unittest.TestCase):
    def make(self, mode="classic", n=3):
        qs = pick_questions(QUESTIONS, n, rng=random.Random(1))
        s = GameSession(qs, mode)
        s.start()
        return s

    def test_perfect_classic_game(self):
        s = self.make()
        for _ in range(3):
            self.assertTrue(s.submit(s.current["answers"][0].upper()).correct)
            s.next_question()
        self.assertEqual((s.score, s.state), (3, "finished"))

    def test_wrong_keeps_score(self):
        s = self.make()
        s.submit("zzz")
        self.assertEqual(s.score, 0)

    def test_blank_does_not_change_state(self):
        s = self.make()
        self.assertTrue(s.submit("   ").blank)
        self.assertEqual((s.state, s.index, len(s.records)), ("playing", 0, 0))

    def test_cannot_submit_twice(self):
        s = self.make()
        s.submit("x")
        with self.assertRaises(RuntimeError):
            s.submit("y")

    def test_challenge_streak_bonus(self):
        s = self.make("challenge", 10)
        gained = []
        for _ in range(6):
            gained.append(s.submit(s.current["answers"][0]).points)
            s.next_question()
        self.assertEqual(gained, [10, 10, 20, 20, 20, 30])

    def test_skip_and_timeout_count_as_wrong(self):
        s = self.make()
        s.skip(); s.next_question()
        s.timeout(); s.next_question()
        self.assertEqual((s.score, s.correct_count, len(s.wrong_questions)), (0, 0, 2))

    def test_no_repeats(self):
        for seed in range(30):
            ids = [q["id"] for q in pick_questions(QUESTIONS, 10, rng=random.Random(seed))]
            self.assertEqual(len(ids), len(set(ids)))

    def test_narrow_filter_still_returns_enough(self):
        qs = pick_questions(QUESTIONS, 10, "History", "Hard", rng=random.Random(2))
        self.assertEqual(len(qs), 10)


class BankTests(unittest.TestCase):
    def test_bank_size_and_shape(self):
        self.assertGreaterEqual(len(QUESTIONS), 40)
        self.assertEqual(len({q["id"] for q in QUESTIONS}), len(QUESTIONS))
        for q in QUESTIONS:
            self.assertTrue(q["answers"])
            if "choices" in q:
                self.assertIn(q["answers"][0], q["choices"])


class CodeGenTests(unittest.TestCase):
    def test_generated_cli_compiles_and_runs(self):
        qs = [q for q in QUESTIONS if "choices" not in q][:3]
        code = generate_cli_code(qs)
        compile(code, "<generated>", "exec")
        ns = {"__name__": "generated"}
        exec(code, ns)
        answers = iter(["  " + qs[0]["answers"][0].upper() + " ", "wrong", qs[2]["answers"][0]])
        buf = io.StringIO()
        with mock.patch.object(builtins, "input", lambda prompt="": next(answers)), contextlib.redirect_stdout(buf):
            ns["main"]()
        self.assertIn("Final Score:  2/3", buf.getvalue())


class VerificationTests(unittest.TestCase):
    def test_all_checks_pass(self):
        self.assertTrue(all(c["ok"] for c in run_verification(0)))


class StorageTests(unittest.TestCase):
    def test_corrupted_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "stats.json"
            p.write_text("{ this is not json", encoding="utf-8")
            self.assertEqual(storage.load_stats(p)["games_played"], 0)

    def test_wrong_types_are_cleaned(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "stats.json"
            p.write_text(json.dumps({"games_played": "lots", "history": "nope", "best": 5}), encoding="utf-8")
            st = storage.load_stats(p)
            self.assertEqual((st["games_played"], st["history"]), (0, []))

    def test_round_trip_and_history_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "stats.json"
            st = storage.load_stats(p)
            for i in range(14):
                storage.record_game(st, "Jaleel", "classic", i % 4, i % 4, 3, "All")
            storage.save_stats(st, p)
            again = storage.load_stats(p)
            self.assertEqual(len(again["history"]), 10)
            self.assertEqual(again["games_played"], 14)
            self.assertEqual(again["best"]["classic"], 3)


if __name__ == "__main__":
    unittest.main()
