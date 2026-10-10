"""
QuizForge - The Decision Engine
DecodeLabs Python Project 4: The General Knowledge Quiz

Run:  python app.py

Architecture (IPOS):
    Input   -> the entry box / choice buttons (this file = VIEW)
    Process -> quiz_engine.py  (sanitize -> evaluate -> execute)   = MODEL
    Output  -> feedback banner, results screen
    Storage -> score vault in GameSession + storage.py (JSON on disk)
"""

import math
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from engine_room import EngineRoom
from questions import CATEGORIES, DIFFICULTIES, QUESTIONS
from quiz_engine import (CHALLENGE_SECONDS, CHALLENGE_TOTAL, CLASSIC_TOTAL, GameSession,
                         pick_questions, rank_for, sanitize, sanitize_steps)
from storage import accuracy, load_stats, record_game, save_stats
from theme import (CHAMPAGNE, CHAMPAGNE_DIM, DANGER, F, GOLD, GOLD_DEEP, INK, INK_CARD, INK_DEEP,
                   INK_LINE, SUCCESS, Pill, RoundedButton, card, ghost_button)


def rounded_points(x1, y1, x2, y2, r):
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


class QuizForgeApp:
    def __init__(self, root):
        self.root = root
        root.title("QuizForge - The Decision Engine")
        root.geometry("1260x820")
        root.minsize(1040, 740)
        root.configure(bg=INK)

        self.stats = load_stats()
        self.session = None
        self.screen = "welcome"
        self.sound_on = True
        self.room_open = False
        self.recent_ids = ()
        self.name_var = tk.StringVar()
        self.setup = {"mode": "classic", "category": "All", "difficulty": "All", "casefold": False}
        self._timer_job = None
        self._toast_job = None
        self.time_left = 0.0
        self._last_tick = 0.0
        self.progress_value = 0.0

        self._setup_styles()
        self._build_shell()
        root.bind("<Return>", self._on_enter)
        root.bind("<Escape>", self._on_escape)
        self.show_welcome()

    # ================================================================ shell
    def _setup_styles(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.layout("Forge.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Forge.Treeview", background=INK_DEEP, fieldbackground=INK_DEEP, foreground=CHAMPAGNE,
                     rowheight=32, borderwidth=0, font=F("ui", 11))
        st.configure("Forge.Treeview.Heading", background=INK_CARD, foreground=GOLD, relief="flat",
                     font=F("ui", 10, "bold"), borderwidth=0, padding=(8, 8))
        st.map("Forge.Treeview", background=[("selected", INK_LINE)], foreground=[("selected", CHAMPAGNE)])
        st.map("Forge.Treeview.Heading", background=[("active", INK_CARD)])
        for orient in ("Vertical", "Horizontal"):
            st.configure(f"{orient}.TScrollbar", background=INK_LINE, troughcolor=INK_DEEP, bordercolor=INK_DEEP,
                         arrowcolor=CHAMPAGNE, lightcolor=INK_LINE, darkcolor=INK_LINE, relief="flat")

    def _build_shell(self):
        header = tk.Frame(self.root, bg=INK_DEEP, height=66)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = tk.Canvas(header, width=36, height=36, bg=INK_DEEP, highlightthickness=0)
        logo.pack(side="left", padx=(26, 12), pady=15)
        logo.create_polygon(18, 2, 34, 18, 18, 34, 2, 18, fill=GOLD, outline=GOLD)
        logo.create_polygon(18, 11, 25, 18, 18, 25, 11, 18, fill=INK_DEEP, outline=INK_DEEP)

        names = tk.Frame(header, bg=INK_DEEP)
        names.pack(side="left", pady=10)
        tk.Label(names, text="QuizForge", font=F("head", 20, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(names, text="THE DECISION ENGINE", font=F("ui", 8, "bold"), fg=GOLD, bg=INK_DEEP).pack(anchor="w")

        right = tk.Frame(header, bg=INK_DEEP)
        right.pack(side="right", padx=22)
        tk.Label(right, text="Powered by DecodeLabs", font=F("ui", 9, "italic"), fg=CHAMPAGNE_DIM,
                 bg=INK_DEEP).pack(side="right", padx=(18, 0))
        self.room_btn = Pill(right, "Engine Room", self.toggle_room, width=124, parent_bg=INK_DEEP)
        self.room_btn.pack(side="right", padx=6)
        self.sound_btn = Pill(right, "Sound: On", self.toggle_sound, width=104, parent_bg=INK_DEEP)
        self.sound_btn.pack(side="right", padx=6)
        self.sound_btn.set_active(True)

        tk.Frame(self.root, bg=GOLD_DEEP, height=1).pack(fill="x")

        self.body = tk.Frame(self.root, bg=INK)
        self.body.pack(fill="both", expand=True)
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)
        self.main = tk.Frame(self.body, bg=INK)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.room = EngineRoom(self.body, self)

        self.toast_label = tk.Label(self.root, text="", font=F("ui", 11, "bold"), fg=INK_DEEP, bg=GOLD, padx=18, pady=9)

    def toggle_room(self):
        self.room_open = not self.room_open
        self.room_btn.set_active(self.room_open)
        if self.room_open:
            self.room.grid(row=0, column=1, sticky="ns")
        else:
            self.room.grid_remove()

    def toggle_sound(self):
        self.sound_on = not self.sound_on
        self.sound_btn.set_active(self.sound_on)
        self.sound_btn.set_text("Sound: On" if self.sound_on else "Sound: Off")

    def toast(self, message):
        if self._toast_job:
            self.root.after_cancel(self._toast_job)
        self.toast_label.config(text=message)
        self.toast_label.place(relx=0.5, rely=0.94, anchor="center")
        self.toast_label.lift()
        self._toast_job = self.root.after(2300, self.toast_label.place_forget)

    def beep(self, kind):
        if not self.sound_on:
            return
        if not sys.platform.startswith("win"):
            self.root.bell()
            return
        tones = {"ok": [(660, 70), (880, 110)], "bad": [(220, 170)], "done": [(523, 90), (659, 90), (784, 170)]}

        def play():
            try:
                import winsound
                for freq, ms in tones[kind]:
                    winsound.Beep(freq, ms)
            except Exception:
                pass
        threading.Thread(target=play, daemon=True).start()

    def _reset_screen(self, name):
        self._cancel_timer()
        for child in self.main.winfo_children():
            child.destroy()
        self.screen = name

    # ========================================================== keyboard
    def _in_room(self, widget):
        return str(widget).startswith(str(self.room))

    def _on_enter(self, event):
        if self._in_room(event.widget):
            return
        if self.screen == "welcome":
            self.start_game()
        elif self.screen == "quiz" and self.session and self.session.state == "feedback":
            self.next_question()

    def _on_escape(self, event):
        if self.screen == "quiz" and self.session and self.session.state == "playing":
            self.skip()

    # =========================================================== WELCOME
    def show_welcome(self):
        self._reset_screen("welcome")
        outer = tk.Frame(self.main, bg=INK)
        outer.pack(fill="both", expand=True, padx=40, pady=22)
        outer.grid_columnconfigure(0, weight=3)
        outer.grid_columnconfigure(1, weight=2)
        outer.grid_rowconfigure(0, weight=1)
        left = tk.Frame(outer, bg=INK)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        right = tk.Frame(outer, bg=INK)
        right.grid(row=0, column=1, sticky="nsew")

        tk.Label(left, text="QuizForge", font=F("head", 44, "bold"), fg=CHAMPAGNE, bg=INK).pack(anchor="w")
        tk.Label(left, text="The Decision Engine", font=F("head", 17, "bold", "italic"), fg=GOLD, bg=INK).pack(anchor="w")
        tk.Label(left, text="You aren't just writing a script. You are architecting decision engines.",
                 font=F("ui", 11), fg=CHAMPAGNE_DIM, bg=INK, wraplength=520, justify="left").pack(anchor="w", pady=(8, 16))

        self._section(left, "YOUR NAME")
        nbox = tk.Frame(left, bg=INK_DEEP, highlightbackground=GOLD_DEEP, highlightcolor=GOLD, highlightthickness=1)
        nbox.pack(anchor="w", fill="x", pady=(0, 12))
        name_entry = tk.Entry(nbox, textvariable=self.name_var, font=F("ui", 14), bg=INK_DEEP, fg=CHAMPAGNE,
                              insertbackground=GOLD, relief="flat", highlightthickness=0, bd=0)
        name_entry.pack(fill="x", padx=12, pady=8)

        self._section(left, "MODE")
        row = tk.Frame(left, bg=INK)
        row.pack(anchor="w")
        self.mode_desc = tk.Label(left, text="", font=F("ui", 10), fg=CHAMPAGNE_DIM, bg=INK, wraplength=520, justify="left")
        self.mode_pills = {}
        for key, text in (("classic", f"Classic  -  {CLASSIC_TOTAL} Questions"), ("challenge", f"Challenge  -  {CHALLENGE_TOTAL} Questions")):
            pill = Pill(row, text, lambda k=key: self._set_mode(k), width=232, height=40)
            pill.pack(side="left", padx=(0, 10))
            self.mode_pills[key] = pill
        self.mode_desc.pack(anchor="w", pady=(6, 12))
        self._set_mode(self.setup["mode"])

        self._section(left, "CATEGORY")
        self._pill_row(left, ["All"] + list(CATEGORIES), "category", 104)
        self._section(left, "DIFFICULTY")
        self._pill_row(left, ["All"] + list(DIFFICULTIES), "difficulty", 96)
        self._section(left, "ANSWER NORMALIZER")
        nrow = tk.Frame(left, bg=INK)
        nrow.pack(anchor="w", pady=(0, 14))
        self.norm_pills = {}
        for key, text in ((False, ".strip().lower()"), (True, ".strip().casefold()")):
            pill = Pill(nrow, text, lambda k=key: self._set_norm(k), width=170)
            pill.pack(side="left", padx=(0, 10))
            self.norm_pills[key] = pill
        self._set_norm(self.setup["casefold"])

        RoundedButton(left, "Start Quiz   \u2192", self.start_game, width=280, height=54,
                      font=F("ui", 13, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(left, text="Press Enter to start", font=F("ui", 9), fg=CHAMPAGNE_DIM, bg=INK).pack(anchor="w", pady=(6, 0))

        # ---- right column
        how = card(right)
        how.pack(fill="x", pady=(0, 16))
        tk.Label(how, text="The Question Block", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_CARD).pack(anchor="w", padx=18, pady=(14, 6))
        steps = [("1  ASK & CAPTURE", "raw = input()"), ("2  SANITIZE", ".strip().lower()"),
                 ("3  EVALUATE", "answer == reference"), ("4  EXECUTE", "if / else -> score")]
        for title, code in steps:
            line = tk.Frame(how, bg=INK_CARD)
            line.pack(fill="x", padx=18, pady=3)
            tk.Label(line, text=title, font=F("ui", 9, "bold"), fg=GOLD, bg=INK_CARD, width=17, anchor="w").pack(side="left")
            tk.Label(line, text=code, font=F("mono", 9), fg=CHAMPAGNE_DIM, bg=INK_CARD).pack(side="left")
        tk.Frame(how, bg=INK_CARD, height=10).pack()

        stats = card(right)
        stats.pack(fill="x", pady=(0, 16))
        tk.Label(stats, text="Your Stats", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_CARD).pack(anchor="w", padx=18, pady=(14, 8))
        grid = tk.Frame(stats, bg=INK_CARD)
        grid.pack(fill="x", padx=18, pady=(0, 14))
        cells = [("Best (Classic)", f"{self.stats['best']['classic']}/{CLASSIC_TOTAL}"),
                 ("Best (Challenge)", str(self.stats["best"]["challenge"])),
                 ("Games played", str(self.stats["games_played"])), ("Accuracy", f"{accuracy(self.stats)}%")]
        for i, (label, value) in enumerate(cells):
            cell = tk.Frame(grid, bg=INK_CARD)
            cell.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 26), pady=4)
            tk.Label(cell, text=value, font=F("head", 20, "bold"), fg=GOLD, bg=INK_CARD).pack(anchor="w")
            tk.Label(cell, text=label, font=F("ui", 9), fg=CHAMPAGNE_DIM, bg=INK_CARD).pack(anchor="w")

        board = card(right)
        board.pack(fill="x")
        tk.Label(board, text="Local Leaderboard", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_CARD).pack(anchor="w", padx=18, pady=(14, 6))
        top = self.stats["leaderboard"][:5]
        if not top:
            tk.Label(board, text="No games yet. Be the first on the board.", font=F("ui", 10),
                     fg=CHAMPAGNE_DIM, bg=INK_CARD).pack(anchor="w", padx=18, pady=(0, 14))
        for i, row_data in enumerate(top, start=1):
            unit = f"{row_data['score']}/{row_data['total']}" if row_data["mode"] == "classic" else f"{row_data['score']} pts"
            line = f"{i}. {str(row_data['name'])[:12]:<12} {unit:>8}  {row_data['mode']}"
            tk.Label(board, text=line, font=F("mono", 10), fg=CHAMPAGNE if i > 1 else GOLD, bg=INK_CARD).pack(anchor="w", padx=18, pady=2)
        tk.Frame(board, bg=INK_CARD, height=12).pack()
        name_entry.focus_set()

    def _section(self, parent, text):
        tk.Label(parent, text=text, font=F("ui", 8, "bold"), fg=GOLD, bg=INK).pack(anchor="w", pady=(0, 5))

    def _pill_row(self, parent, options, key, width):
        row = tk.Frame(parent, bg=INK)
        row.pack(anchor="w", pady=(0, 12))
        pills = {}
        for opt in options:
            def choose(o=opt):
                self.setup[key] = o
                for name, p in pills.items():
                    p.set_active(name == o)
            pill = Pill(row, opt, choose, width=width)
            pill.pack(side="left", padx=(0, 8))
            pill.set_active(self.setup[key] == opt)
            pills[opt] = pill

    def _set_mode(self, mode):
        self.setup["mode"] = mode
        for key, pill in self.mode_pills.items():
            pill.set_active(key == mode)
        self.mode_desc.config(text=(
            f"{CLASSIC_TOTAL} questions. +1 point per correct answer. Pure and faithful to the brief."
            if mode == "classic" else
            f"{CHALLENGE_TOTAL} questions, {CHALLENGE_SECONDS}s timer each, streak bonus x1 / x2 / x3."))

    def _set_norm(self, use_casefold):
        self.setup["casefold"] = use_casefold
        for key, pill in self.norm_pills.items():
            pill.set_active(key == use_casefold)

    # ============================================================== GAME
    def start_game(self, questions=None, practice=False):
        mode = self.setup["mode"]
        name = self.name_var.get().strip() or "Player"
        if questions is None:
            count = CLASSIC_TOTAL if mode == "classic" else CHALLENGE_TOTAL
            questions = pick_questions(QUESTIONS, count, self.setup["category"], self.setup["difficulty"],
                                       avoid_ids=self.recent_ids)
        self.recent_ids = tuple(q["id"] for q in questions)
        self.session = GameSession(questions, mode, self.setup["casefold"], name, practice)
        self.session.start()
        self.room.new_session(self.session)
        self.show_quiz()

    # ---------------------------------------------------------- QUIZ UI
    def show_quiz(self):
        self._reset_screen("quiz")
        wrap = tk.Frame(self.main, bg=INK)
        wrap.pack(fill="both", expand=True, padx=44, pady=(20, 16))

        top = tk.Frame(wrap, bg=INK)
        top.pack(fill="x")
        self.lbl_counter = tk.Label(top, font=F("ui", 13, "bold"), fg=GOLD, bg=INK)
        self.lbl_counter.pack(side="left")
        self.lbl_chips = tk.Label(top, font=F("ui", 10), fg=CHAMPAGNE_DIM, bg=INK)
        self.lbl_chips.pack(side="left", padx=16)
        hud = tk.Frame(top, bg=INK)
        hud.pack(side="right")
        self.lbl_streak = tk.Label(hud, font=F("ui", 10), fg=CHAMPAGNE_DIM, bg=INK)
        self.lbl_streak.pack(side="right", padx=(16, 0))
        self.lbl_score = tk.Label(hud, font=F("mono", 15, "bold"), fg=GOLD, bg=INK)
        self.lbl_score.pack(side="right")

        self.progress = tk.Canvas(wrap, height=10, bg=INK, highlightthickness=0)
        self.progress.pack(fill="x", pady=(12, 16))
        self.progress.bind("<Configure>", lambda e: self._draw_progress())
        self.progress_value = self.session.index / self.session.total

        self.qcard = card(wrap)
        self.qcard.pack(fill="both", expand=True)
        inner = tk.Frame(self.qcard, bg=INK_CARD)
        inner.pack(fill="both", expand=True, padx=36, pady=28)

        self.timer_canvas = tk.Canvas(inner, width=74, height=74, bg=INK_CARD, highlightthickness=0)

        self.bottom = tk.Frame(inner, bg=INK_CARD)
        self.bottom.pack(side="bottom", fill="x")

        self.lbl_question = tk.Label(inner, font=F("head", 26, "bold"), fg=CHAMPAGNE, bg=INK_CARD,
                                     justify="left", anchor="w", wraplength=620)
        self.lbl_question.pack(fill="x", padx=14, pady=(6, 24))

        self.answer_area = tk.Frame(inner, bg=INK_CARD)
        self.answer_area.pack(fill="x", padx=14)
        self.inspector = tk.Label(inner, font=F("mono", 10), fg=CHAMPAGNE_DIM, bg=INK_CARD,
                                  anchor="w", justify="left", wraplength=700)
        self.inspector.pack(fill="x", padx=14, pady=(14, 0))
        self.hint_label = tk.Label(inner, font=F("mono", 12, "bold"), fg=GOLD, bg=INK_CARD, anchor="w")
        self.hint_label.pack(fill="x", padx=14, pady=(10, 0))
        inner.bind("<Configure>", lambda e: (self.lbl_question.config(wraplength=max(320, e.width - 150)),
                                             self.inspector.config(wraplength=max(320, e.width - 60))))

        self.banner = tk.Frame(self.bottom, bg=INK_DEEP)
        self.actions = tk.Frame(self.bottom, bg=INK_CARD)
        self.submit_btn = RoundedButton(self.actions, "Submit", self.submit, width=150, height=46, parent_bg=INK_CARD)
        self.submit_btn.pack(side="left")
        self.hint_btn = ghost_button(self.actions, "Hint", self.hint, width=100, height=46)
        self.hint_btn.pack(side="left", padx=10)
        self.skip_btn = ghost_button(self.actions, "Skip  (Esc)", self.skip, width=130, height=46)
        self.skip_btn.pack(side="left")
        self.next_row = tk.Frame(self.bottom, bg=INK_CARD)
        self.next_btn = RoundedButton(self.next_row, "Next question  \u2192", self.next_question,
                                      width=230, height=46, parent_bg=INK_CARD)
        self.next_btn.pack(side="left")
        tk.Label(self.next_row, text="or press Enter", font=F("ui", 9), fg=CHAMPAGNE_DIM, bg=INK_CARD).pack(side="left", padx=12)

        self.load_question()

    def load_question(self):
        s = self.session
        q = s.current
        self._cancel_timer()
        self.lbl_counter.config(text=f"Question {s.index + 1} of {s.total}")
        self.lbl_chips.config(text=f"{q['category']}   \u00b7   {q['difficulty']}")
        self.lbl_question.config(text=q["q"])
        self._update_hud()
        self._animate_progress(s.index / s.total)

        for w in self.answer_area.winfo_children():
            w.destroy()
        self.answer_area.pack_configure(padx=14)
        self.hint_label.config(text="")
        self.banner.pack_forget()
        self.next_row.pack_forget()
        self.actions.pack(fill="x", padx=14, pady=(18, 0))
        self.submit_btn.set_enabled(True)
        self.hint_btn.set_enabled(True)
        self.skip_btn.set_enabled(True)

        self.choice_buttons = {}
        self.entry = None
        if q.get("choices"):
            self.inspector.config(text="Multiple choice - pick one option.", fg=CHAMPAGNE_DIM)
            self.submit_btn.set_enabled(False)
            self._build_choices(q)
        else:
            self.inspector.config(text="Type an answer to watch the sanitization pipeline run.", fg=CHAMPAGNE_DIM)
            self._build_entry()
        if s.mode == "challenge":
            self._start_timer()
        self.room.refresh(s)

    def _build_entry(self):
        box = tk.Frame(self.answer_area, bg=INK_DEEP, highlightbackground=GOLD_DEEP, highlightcolor=GOLD, highlightthickness=2)
        box.pack(fill="x")
        self.answer_var = tk.StringVar()
        self.entry = tk.Entry(box, textvariable=self.answer_var, font=F("ui", 19), bg=INK_DEEP, fg=CHAMPAGNE,
                              insertbackground=GOLD, relief="flat", disabledbackground=INK_DEEP,
                              disabledforeground=CHAMPAGNE_DIM, highlightthickness=0, bd=0)
        self.entry.pack(fill="x", padx=16, pady=13)
        self.entry.bind("<Return>", self._entry_return)
        self.answer_var.trace_add("write", lambda *_: self._update_inspector())
        self.entry.focus_set()

    def _entry_return(self, _event):
        self.submit()
        return "break"

    def _build_choices(self, q):
        choices = list(q["choices"])
        random.shuffle(choices)
        grid = tk.Frame(self.answer_area, bg=INK_CARD)
        grid.pack(fill="x")
        for i, text in enumerate(choices):
            btn = RoundedButton(grid, f"{'ABCD'[i]}    {text}", lambda t=text: self.submit(t), width=310, height=52,
                                radius=16, bg=INK_DEEP, fg=CHAMPAGNE, hover=INK_LINE, outline=INK_LINE,
                                parent_bg=INK_CARD, font=F("ui", 12, "bold"))
            btn.grid(row=i // 2, column=i % 2, padx=(0, 14), pady=7, sticky="w")
            self.choice_buttons[text] = btn

    def _update_inspector(self):
        raw = self.answer_var.get()
        if not raw:
            self.inspector.config(text="Type an answer to watch the sanitization pipeline run.", fg=CHAMPAGNE_DIM)
        elif not raw.strip():
            self.inspector.config(text=f"raw {raw!r}  \u2192  blank input is blocked", fg=DANGER)
        else:
            steps = sanitize_steps(raw, self.session.use_casefold)
            self.inspector.config(text="  \u2192  ".join(f"{label} {val!r}" for label, val in steps), fg=CHAMPAGNE_DIM)

    # ------------------------------------------------------ player actions
    def submit(self, choice=None):
        s = self.session
        if not s or s.state != "playing":
            return
        raw = choice if choice is not None else (self.answer_var.get() if self.entry else "")
        outcome = s.submit(raw)
        if outcome.blank:
            self.inspector.config(text="Blank answers are blocked. Type something first.", fg=DANGER)
            self._shake(self.answer_area)
            self.beep("bad")
            return
        self._finish_question(outcome)

    def skip(self):
        s = self.session
        if s and s.state == "playing":
            self._finish_question(s.skip())

    def hint(self):
        s = self.session
        if s and s.state == "playing":
            extra = "   (points halved)" if s.mode == "challenge" else ""
            self.hint_label.config(text=f"Hint:  {s.hint()}{extra}")

    def _finish_question(self, outcome):
        s = self.session
        self._cancel_timer()
        self.timer_canvas.place_forget()
        if self.entry:
            self.entry.config(state="disabled")
        for text, btn in self.choice_buttons.items():
            is_right = sanitize(text) == sanitize(outcome.correct_answer)
            if is_right:
                btn.set_colors(SUCCESS, INK_DEEP, hover=SUCCESS, outline=SUCCESS)
            elif sanitize(text) == sanitize(outcome.raw) and not outcome.correct:
                btn.set_colors(DANGER, INK_DEEP, hover=DANGER, outline=DANGER)
            btn.command = None
            btn.config(cursor="arrow")
            btn.hover_bg = btn.bg

        if outcome.steps:
            chain = "  \u2192  ".join(f"{label} {val!r}" for label, val in outcome.steps)
            verdict = "matched \u2713" if outcome.correct else "no match \u2717"
            self.inspector.config(text=f"{chain}  \u2192  {verdict}", fg=SUCCESS if outcome.correct else DANGER)

        self._show_banner(outcome)
        self._update_hud()
        self._animate_progress((s.index + 1) / s.total)
        self.next_btn.set_text("Next question  \u2192" if s.index + 1 < s.total else "See results  \u2192")
        self.actions.pack_forget()
        self.next_row.pack(fill="x", padx=14)
        if outcome.correct:
            self._flash(self.qcard, SUCCESS)
            self.beep("ok")
        else:
            self._shake(self.answer_area)
            self._flash(self.qcard, DANGER)
            self.beep("bad")
        self.room.on_outcome(outcome, s)

    def _show_banner(self, o):
        for w in self.banner.winfo_children():
            w.destroy()
        s = self.session
        if o.correct:
            color, title = SUCCESS, "Correct!"
            detail = f"+{o.points} point{'s' if o.points != 1 else ''}"
            if s.mode == "challenge" and s.streak >= 3:
                detail += f"   \u00b7   streak x{s.streak}, bonus multiplier x{s.multiplier}"
        elif o.skipped:
            color, title, detail = GOLD, "Skipped", f"The answer was:  {o.correct_answer}"
        elif o.timed_out:
            color, title, detail = DANGER, "Time's up!", f"The answer was:  {o.correct_answer}"
        else:
            color, title, detail = DANGER, "Not quite.", f"The correct answer is:  {o.correct_answer}"
        tk.Frame(self.banner, bg=color, width=6).pack(side="left", fill="y")
        col = tk.Frame(self.banner, bg=INK_DEEP)
        col.pack(side="left", padx=16, pady=10)
        tk.Label(col, text=title, font=F("head", 16, "bold"), fg=color, bg=INK_DEEP).pack(anchor="w")
        tk.Label(col, text=detail, font=F("ui", 11), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        self.banner.pack(fill="x", padx=14, pady=(18, 14))

    def next_question(self):
        s = self.session
        if not s or s.state != "feedback":
            return
        if s.next_question() == "finished":
            self.finish_game()
        else:
            self.load_question()

    def _update_hud(self):
        s = self.session
        if s.mode == "classic":
            self.lbl_score.config(text=f"Score  {s.score}")
            self.lbl_streak.config(text="")
        else:
            self.lbl_score.config(text=f"{s.score} pts")
            self.lbl_streak.config(text=f"Streak {s.streak}   x{s.multiplier}")

    # ------------------------------------------------------------ timer
    def _start_timer(self):
        self.time_left = float(CHALLENGE_SECONDS)
        self._last_tick = time.monotonic()
        self.timer_canvas.place(relx=1.0, y=0, anchor="ne")
        tk.Misc.tkraise(self.timer_canvas)   # Canvas.tkraise means "raise items", so call the widget version
        self._tick()

    def _cancel_timer(self):
        if self._timer_job:
            try:
                self.root.after_cancel(self._timer_job)
            except ValueError:
                pass
            self._timer_job = None

    def _tick(self):
        s = self.session
        if not s or s.state != "playing" or self.screen != "quiz":
            return
        now = time.monotonic()
        dt, self._last_tick = now - self._last_tick, now
        focused = self.root.focus_displayof() is not None     # pause while the window is in the background
        if focused:
            self.time_left -= dt
        self._draw_timer(paused=not focused)
        if self.time_left <= 0:
            raw = self.answer_var.get() if self.entry else ""
            self._finish_question(s.timeout(raw))
            return
        self._timer_job = self.root.after(50, self._tick)

    def _draw_timer(self, paused=False):
        c = self.timer_canvas
        c.delete("all")
        frac = max(self.time_left, 0) / CHALLENGE_SECONDS
        color = DANGER if self.time_left <= 5 else GOLD
        c.create_arc(7, 7, 67, 67, start=90, extent=359.9, style="arc", outline=INK_LINE, width=6)
        c.create_arc(7, 7, 67, 67, start=90, extent=-359.9 * frac, style="arc", outline=color, width=6)
        label = "paused" if paused else str(math.ceil(max(self.time_left, 0)))
        c.create_text(37, 37, text=label, fill=color, font=F("mono", 9 if paused else 17, "bold"))

    # --------------------------------------------------------- animations
    def _draw_progress(self):
        c = self.progress
        if not c.winfo_exists():
            return
        c.delete("all")
        w = max(c.winfo_width(), 10)
        c.create_polygon(rounded_points(0, 1, w, 9, 4), smooth=True, fill=INK_DEEP, outline=INK_DEEP)
        fill_w = w * self.progress_value
        if fill_w > 8:
            c.create_polygon(rounded_points(0, 1, fill_w, 9, 4), smooth=True, fill=GOLD, outline=GOLD)

    def _animate_progress(self, target):
        def step():
            if self.screen != "quiz" or not self.progress.winfo_exists():
                return
            diff = target - self.progress_value
            if abs(diff) < 0.004:
                self.progress_value = target
                self._draw_progress()
                return
            self.progress_value += diff * 0.22
            self._draw_progress()
            self.root.after(16, step)
        step()

    def _shake(self, widget):
        offsets = [12, -12, 9, -9, 6, -6, 3, 0]

        def step(i=0):
            if i >= len(offsets) or not widget.winfo_exists():
                return
            o = offsets[i]
            widget.pack_configure(padx=(14 + o, 14 - o))
            self.root.after(32, lambda: step(i + 1))
        step()

    def _flash(self, widget, color, times=3):
        def step(i=0):
            if not widget.winfo_exists():
                return
            if i >= times * 2:
                widget.config(highlightbackground=INK_LINE, highlightcolor=INK_LINE, highlightthickness=1)
                return
            on = i % 2 == 0
            widget.config(highlightbackground=color if on else INK_LINE, highlightcolor=color if on else INK_LINE,
                          highlightthickness=3 if on else 1)
            self.root.after(130, lambda: step(i + 1))
        step()

    # ========================================================== RESULTS
    def finish_game(self):
        s = self.session
        is_best = False
        if not s.practice:
            is_best = record_game(self.stats, s.player, s.mode, s.score, s.correct_count, s.total, self.setup["category"])
            save_stats(self.stats)
        self.room.refresh(s)
        self.show_results(is_best)

    def show_results(self, is_best):
        self._reset_screen("results")
        s = self.session
        label, message = rank_for(s.correct_count, s.total)
        wrap = tk.Frame(self.main, bg=INK)
        wrap.pack(fill="both", expand=True, padx=44, pady=(8, 18))

        self.hero = tk.Canvas(wrap, height=262, bg=INK, highlightthickness=0)
        self.hero.pack(fill="x")
        self._hero_state = {"value": 0, "label": label, "message": message, "best": is_best}
        self.hero.bind("<Configure>", lambda e: self._draw_hero())
        self.root.update_idletasks()
        self._draw_hero()

        target = s.score
        step = max(1, target // 22)

        def count(v=0):
            if self.screen != "results" or not self.hero.winfo_exists():
                return
            v = min(v + step, target)
            self._hero_state["value"] = v
            self._draw_hero()
            if v < target:
                self.root.after(35, lambda: count(v))
        if target > 0:
            count(0)
        else:
            self._draw_hero()

        if label == "Perfect":
            self._confetti(self.hero)
        self.beep("done")

        table_wrap = tk.Frame(wrap, bg=INK_DEEP, highlightbackground=INK_LINE, highlightthickness=1)
        table_wrap.pack(fill="both", expand=True, pady=(8, 14))
        cols = ("n", "q", "given", "answer", "res")
        tree = ttk.Treeview(table_wrap, columns=cols, show="headings", style="Forge.Treeview",
                            height=min(max(s.total, 3), 6), selectmode="none")
        for col, text, width, anchor in (("n", "#", 36, "center"), ("q", "Question", 300, "w"),
                                         ("given", "Your answer", 150, "w"), ("answer", "Correct answer", 170, "w"),
                                         ("res", "Result", 64, "center")):
            tree.heading(col, text=text, anchor=anchor)
            tree.column(col, width=width, anchor=anchor, stretch=(col == "q"))
        tree.tag_configure("ok", foreground=SUCCESS)
        tree.tag_configure("bad", foreground=DANGER)
        for i, r in enumerate(s.records, start=1):
            tree.insert("", "end", values=(i, r.question, r.given or "-", r.correct_answer, "\u2713" if r.is_correct else "\u2717"),
                        tags=("ok" if r.is_correct else "bad",))
        sb = ttk.Scrollbar(table_wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        if s.total > 6:
            sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        row = tk.Frame(wrap, bg=INK)
        row.pack(fill="x")
        RoundedButton(row, "Play Again", self.start_game, width=160, height=48, parent_bg=INK).pack(side="left")
        if s.wrong_questions:
            ghost_button(row, "Retry Mistakes", self.retry_mistakes, width=170, height=48, parent_bg=INK).pack(side="left", padx=(10, 0))
        ghost_button(row, "Share Score", self.share_score, width=150, height=48, parent_bg=INK).pack(side="left", padx=(10, 0))
        ghost_button(row, "Main Menu", self.show_welcome, width=140, height=48, parent_bg=INK).pack(side="right")

    def _draw_hero(self):
        c = self.hero
        if not c.winfo_exists():
            return
        s, st = self.session, self._hero_state
        c.delete("hero")
        w = max(c.winfo_width(), 700)
        cx = w / 2
        c.create_text(cx, 24, text="QUIZ COMPLETE", fill=GOLD, font=F("ui", 11, "bold"), tags="hero")
        if s.mode == "classic":
            big = f"{st['value']} / {s.total}"
            line = f"You scored {s.score} out of {s.total}"
        else:
            big = f"{st['value']}"
            line = f"You scored {s.score} points  \u00b7  {s.correct_count} of {s.total} correct  \u00b7  best streak {s.best_streak}"
        c.create_text(cx, 98, text=big, fill=CHAMPAGNE, font=F("head", 66, "bold"), tags="hero")
        c.create_text(cx, 160, text=line, fill=CHAMPAGNE, font=F("ui", 14), tags="hero")

        colors = {"Perfect": GOLD, "Great": SUCCESS, "Keep Practicing": DANGER}
        col = colors[st["label"]]
        bw = 190
        c.create_polygon(rounded_points(cx - bw / 2, 182, cx + bw / 2, 214, 16), smooth=True, fill=col, outline=col, tags="hero")
        c.create_text(cx, 198, text=st["label"].upper(), fill=INK_DEEP, font=F("ui", 11, "bold"), tags="hero")
        note = st["message"] + ("   \u2605 New personal best!" if st["best"] else "")
        c.create_text(cx, 240, text=note, fill=CHAMPAGNE_DIM, font=F("ui", 11, "italic"), tags="hero")
        c.tag_raise("hero")

    def _confetti(self, canvas):
        w = max(canvas.winfo_width(), 700)
        palette = [GOLD, CHAMPAGNE, SUCCESS, GOLD_DEEP]
        parts = []
        for _ in range(80):
            size = random.randint(6, 11)
            x, y = random.uniform(0, w), random.uniform(-260, 0)
            item = canvas.create_rectangle(x, y, x + size, y + size * 0.6, fill=random.choice(palette), outline="", tags="confetti")
            parts.append((item, random.uniform(-1.4, 1.4), random.uniform(2.6, 6.0)))

        def step(n=0):
            if n > 110 or self.screen != "results" or not canvas.winfo_exists():
                if canvas.winfo_exists():
                    canvas.delete("confetti")
                return
            for item, dx, dy in parts:
                canvas.move(item, dx, dy)
            canvas.tag_lower("confetti")
            self.root.after(30, lambda: step(n + 1))
        step()

    def retry_mistakes(self):
        wrong = self.session.wrong_questions
        if wrong:
            self.start_game(questions=wrong, practice=True)

    def share_score(self):
        s = self.session
        label, _ = rank_for(s.correct_count, s.total)
        if s.mode == "classic":
            text = f"I scored {s.score}/{s.total} ({label}) on QuizForge - architecting decision engines with Python! #DecodeLabs"
        else:
            text = f"I scored {s.score} points ({s.correct_count}/{s.total}, best streak {s.best_streak}) in QuizForge Challenge Mode! #DecodeLabs"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.toast("Score copied to clipboard")


def main():
    root = tk.Tk()
    QuizForgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
