"""
The ENGINE ROOM - the educational side panel.

It makes the invisible visible: the Score Vault, the if/else gate, the generated
Python code, the difference between lower() and casefold(), a live event log
and a verification checklist that runs real tests against the engine.
"""

import re
import tkinter as tk
from tkinter import ttk

from quiz_engine import generate_cli_code, run_verification
from theme import (CHAMPAGNE, CHAMPAGNE_DIM, DANGER, F, GOLD, GOLD_DEEP, INK, INK_CARD,
                   INK_DEEP, INK_LINE, SUCCESS, RoundedButton)

TABS = [("state", "State"), ("logic", "Logic"), ("code", "Code"),
        ("text", "Text"), ("log", "Log"), ("checks", "Checks")]

PY_KEYWORDS = r"\b(def|if|else|elif|for|in|return|print|input|while|import|from|True|False|None)\b"


class EngineRoom(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=INK_DEEP, width=390, highlightbackground=INK_LINE,
                         highlightcolor=INK_LINE, highlightthickness=1)
        self.pack_propagate(False)
        self.app = app
        self._last = {}
        self._anim_jobs = []

        head = tk.Frame(self, bg=INK_DEEP)
        head.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(head, text="ENGINE ROOM", font=F("mono", 12, "bold"), fg=GOLD, bg=INK_DEEP).pack(anchor="w")
        tk.Label(head, text="See the logic behind every answer", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w")

        self.tabbar = tk.Frame(self, bg=INK_DEEP)
        self.tabbar.pack(fill="x", padx=12, pady=(8, 0))
        self.tab_labels = {}
        for key, title in TABS:
            lbl = tk.Label(self.tabbar, text=title, font=F("ui", 9, "bold"), fg=CHAMPAGNE_DIM,
                           bg=INK_DEEP, padx=9, pady=5, cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, k=key: self.show(k))
            self.tab_labels[key] = lbl
        tk.Frame(self, bg=INK_LINE, height=1).pack(fill="x", padx=12)

        self.body = tk.Frame(self, bg=INK_DEEP)
        self.body.pack(fill="both", expand=True, padx=12, pady=10)
        self.pages = {}
        self._build_state()
        self._build_logic()
        self._build_code()
        self._build_text()
        self._build_log()
        self._build_checks()
        self.show("state")
        self.refresh(None)
        self.set_code(None)

    # ----------------------------------------------------------- tabs
    def show(self, key):
        for k, page in self.pages.items():
            page.pack_forget()
            self.tab_labels[k].config(fg=CHAMPAGNE_DIM, bg=INK_DEEP)
        self.pages[key].pack(fill="both", expand=True)
        self.tab_labels[key].config(fg=INK_DEEP, bg=GOLD)

    def _page(self, key):
        page = tk.Frame(self.body, bg=INK_DEEP)
        self.pages[key] = page
        return page

    # ------------------------------------------------- 1. STATE VAULT
    def _build_state(self):
        p = self._page("state")
        tk.Label(p, text="Live State Vault", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(p, text="System state, updated in real time.", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w", pady=(0, 10))
        box = tk.Frame(p, bg=INK, highlightbackground=INK_LINE, highlightthickness=1)
        box.pack(fill="x")
        self.state_vars = {}
        rows = [("score", 26), ("question_index", 13), ("streak", 13), ("state", 13), ("type(score)", 13)]
        for name, size in rows:
            lbl = tk.Label(box, text="", font=F("mono", size, "bold"), fg=GOLD, bg=INK, anchor="w")
            lbl.pack(fill="x", padx=14, pady=(10 if name == "score" else 3, 3))
            self.state_vars[name] = lbl
        note = ("score = 0  # the Score Vault\n"
                "A wrong answer never touches it.\n"
                "A right answer runs: score += 1")
        tk.Label(p, text=note, font=F("mono", 9), fg=CHAMPAGNE_DIM, bg=INK_DEEP, justify="left").pack(anchor="w", pady=12)

    def _set_state_label(self, name, text):
        lbl = self.state_vars[name]
        if self._last.get(name) is not None and self._last[name] != text:
            lbl.config(fg=SUCCESS)
            lbl.after(700, lambda: lbl.config(fg=GOLD))
        self._last[name] = text
        lbl.config(text=text)

    # ------------------------------------------------- 2. LOGIC GATES
    def _build_logic(self):
        p = self._page("logic")
        tk.Label(p, text="Logic Gate Visualizer", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(p, text="Lights up the path your last answer took.", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w", pady=(0, 6))
        c = tk.Canvas(p, width=360, height=470, bg=INK_DEEP, highlightthickness=0)
        c.pack()
        self.gate = c
        self.nodes, self.arrows, self.captions = {}, {}, {}

        def box(name, x1, y1, x2, y2, label):
            rect = c.create_rectangle(x1, y1, x2, y2, outline=INK_LINE, fill=INK, width=2)
            txt = c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label, fill=CHAMPAGNE_DIM, font=F("mono", 10, "bold"))
            self.nodes[name] = (rect, txt)

        def arrow(name, x1, y1, x2, y2):
            self.arrows[name] = c.create_line(x1, y1, x2, y2, fill=INK_LINE, width=2, arrow="last", arrowshape=(9, 11, 4))

        def caption(name, x, y):
            self.captions[name] = c.create_text(x, y, text="", fill=CHAMPAGNE_DIM, font=F("mono", 8), width=330)

        box("input", 80, 8, 280, 44, "1 . INPUT")
        caption("input", 180, 58)
        arrow("a1", 180, 70, 180, 90)
        box("sanitize", 80, 90, 280, 126, "2 . SANITIZE")
        caption("sanitize", 180, 140)
        arrow("a2", 180, 152, 180, 172)
        box("evaluate", 80, 172, 280, 208, "3 . EVALUATE  ==")
        caption("evaluate", 180, 222)
        arrow("a3", 180, 234, 180, 254)
        diamond = c.create_polygon(180, 254, 262, 292, 180, 330, 98, 292, outline=INK_LINE, fill=INK, width=2)
        dtxt = c.create_text(180, 292, text="if / else", fill=CHAMPAGNE_DIM, font=F("mono", 10, "bold"))
        self.nodes["gate"] = (diamond, dtxt)
        arrow("a_ok", 98, 292, 62, 292)
        arrow("a_ok2", 62, 292, 62, 362)
        arrow("a_bad", 262, 292, 298, 292)
        arrow("a_bad2", 298, 292, 298, 362)
        box("success", 6, 362, 120, 414, "SUCCESS\nscore += 1")
        box("failure", 240, 362, 354, 414, "FAILURE\nunchanged")
        caption("result", 180, 442)

    def _light(self, name, color):
        if name in self.nodes:
            rect, txt = self.nodes[name]
            self.gate.itemconfig(rect, outline=color)
            self.gate.itemconfig(txt, fill=color)
        if name in self.arrows:
            self.gate.itemconfig(self.arrows[name], fill=color)

    def _reset_gate(self):
        for job in self._anim_jobs:
            try:
                self.after_cancel(job)
            except ValueError:
                pass
        self._anim_jobs.clear()
        for name in list(self.nodes) + list(self.arrows):
            self._light(name, INK_LINE)
        for name in list(self.nodes):
            self.gate.itemconfig(self.nodes[name][1], fill=CHAMPAGNE_DIM)
        for cap in self.captions.values():
            self.gate.itemconfig(cap, text="")

    def play_gate(self, outcome):
        """Animate the path: input -> sanitize -> evaluate -> gate -> branch."""
        self._reset_gate()
        ok = outcome.correct
        end = "success" if ok else "failure"
        color_end = SUCCESS if ok else DANGER
        branch = ["a_ok", "a_ok2", "success"] if ok else ["a_bad", "a_bad2", "failure"]
        path = ["input", "a1", "sanitize", "a2", "evaluate", "a3", "gate"] + branch

        if outcome.skipped or outcome.timed_out:
            raw_txt = "skipped" if outcome.skipped else "time ran out"
            self.gate.itemconfig(self.captions["input"], text=raw_txt)
        else:
            self.gate.itemconfig(self.captions["input"], text=f"raw = {outcome.raw!r}")
            self.gate.itemconfig(self.captions["sanitize"], text=f".strip().lower() -> {outcome.sanitized!r}")
            self.gate.itemconfig(self.captions["evaluate"], text=f"{outcome.sanitized!r} == {outcome.correct_answer.lower()!r} -> {ok}")
        verdict = f"score += {outcome.points}" if ok else "score unchanged"
        self.gate.itemconfig(self.captions["result"], text=verdict, fill=color_end)

        for i, name in enumerate(path):
            color = color_end if name in branch or name == end else GOLD
            self._anim_jobs.append(self.after(i * 140, lambda n=name, col=color: self._light(n, col)))

    # ------------------------------------------------- 3. CODE
    def _build_code(self):
        p = self._page("code")
        tk.Label(p, text="Python Code Generator", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(p, text="A runnable CLI version of this exact quiz.", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w", pady=(0, 6))
        wrap = tk.Frame(p, bg=INK)
        wrap.pack(fill="both", expand=True)
        self.code_text = tk.Text(wrap, bg=INK, fg=CHAMPAGNE, font=F("mono", 9), wrap="none", relief="flat",
                                 padx=10, pady=8, insertbackground=GOLD, highlightthickness=0, height=18)
        ys = ttk.Scrollbar(wrap, orient="vertical", command=self.code_text.yview)
        xs = ttk.Scrollbar(wrap, orient="horizontal", command=self.code_text.xview)
        self.code_text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        self.code_text.pack(side="left", fill="both", expand=True)
        for tag, color in (("kw", GOLD), ("str", SUCCESS), ("com", "#7FA997")):
            self.code_text.tag_configure(tag, foreground=color)
        self.copy_btn = RoundedButton(p, "Copy code", self._copy_code, width=130, height=34,
                                      parent_bg=INK_DEEP, font=F("ui", 10, "bold"))
        self.copy_btn.pack(anchor="w", pady=(8, 0))

    def set_code(self, session):
        if session is None:
            from questions import QUESTIONS
            qs = [q for q in QUESTIONS if "choices" not in q][:3]
            code = generate_cli_code(qs)
        else:
            code = generate_cli_code(session.questions[:session.total], session.use_casefold)
        self.code = code
        t = self.code_text
        t.config(state="normal")
        t.delete("1.0", "end")
        t.insert("1.0", code)
        for tag in ("kw", "str", "com"):
            t.tag_remove(tag, "1.0", "end")
        for m in re.finditer(PY_KEYWORDS, code):
            t.tag_add("kw", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r"(f?'[^'\n]*'|f?\"[^\"\n]*\")", code):
            t.tag_add("str", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r"#[^\n]*", code):
            t.tag_add("com", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        t.config(state="disabled")

    def _copy_code(self):
        self.clipboard_clear()
        self.clipboard_append(self.code)
        self.app.toast("Python code copied to clipboard")

    # ------------------------------------------------- 4. NORMALIZATION
    def _build_text(self):
        p = self._page("text")
        tk.Label(p, text="Normalization Matrix", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(p, text="Type anything. Compare the methods.", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w", pady=(0, 8))
        self.norm_var = tk.StringVar(value="  Straße  ")
        ebox = tk.Frame(p, bg=INK, highlightbackground=GOLD_DEEP, highlightthickness=1)
        ebox.pack(fill="x")
        tk.Entry(ebox, textvariable=self.norm_var, font=F("mono", 12), bg=INK, fg=CHAMPAGNE, relief="flat",
                 insertbackground=GOLD, highlightthickness=0, bd=0).pack(fill="x", padx=10, pady=8)
        grid = tk.Frame(p, bg=INK_DEEP)
        grid.pack(fill="x", pady=10)
        self.norm_rows = {}
        for r, name in enumerate(["raw", ".strip()", ".lower()", ".casefold()", ".strip().lower()", ".strip().casefold()"]):
            tk.Label(grid, text=name, font=F("mono", 9, "bold"), fg=GOLD, bg=INK_DEEP, anchor="w", width=18).grid(row=r, column=0, sticky="w", pady=3)
            val = tk.Label(grid, text="", font=F("mono", 9), fg=CHAMPAGNE, bg=INK_DEEP, anchor="w")
            val.grid(row=r, column=1, sticky="w")
            self.norm_rows[name] = val
        self.norm_note = tk.Label(p, text="", font=F("ui", 9), fg=CHAMPAGNE_DIM, bg=INK_DEEP, wraplength=350, justify="left")
        self.norm_note.pack(anchor="w", pady=6)
        self.norm_var.trace_add("write", lambda *_: self._update_norm())
        self._update_norm()

    def _update_norm(self):
        s = self.norm_var.get()
        vals = {"raw": s, ".strip()": s.strip(), ".lower()": s.lower(), ".casefold()": s.casefold(),
                ".strip().lower()": s.strip().lower(), ".strip().casefold()": s.strip().casefold()}
        for name, v in vals.items():
            self.norm_rows[name].config(text=repr(v))
        if s.lower() != s.casefold():
            self.norm_note.config(fg=GOLD, text="lower() and casefold() DIFFER here. casefold() is the aggressive, "
                                  "international-safe choice (German ß becomes 'ss').")
        else:
            self.norm_note.config(fg=CHAMPAGNE_DIM, text="Try 'Straße' - lower() keeps ß, casefold() turns it into 'ss'.")

    # ------------------------------------------------- 5. LOG
    def _build_log(self):
        p = self._page("log")
        tk.Label(p, text="Event Log", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(p, text="Every answer, as the engine saw it.", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w", pady=(0, 6))
        wrap = tk.Frame(p, bg=INK)
        wrap.pack(fill="both", expand=True)
        self.log_text = tk.Text(wrap, bg=INK, fg=CHAMPAGNE, font=F("mono", 9), wrap="word", relief="flat",
                                padx=10, pady=8, highlightthickness=0, state="disabled")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_text.tag_configure("ok", foreground=SUCCESS)
        self.log_text.tag_configure("bad", foreground=DANGER)
        self.log_text.tag_configure("dim", foreground=CHAMPAGNE_DIM)

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "$ session started\n", "dim")
        self.log_text.config(state="disabled")

    def add_log(self, line):
        self.log_text.config(state="normal")
        tag = "ok" if "match=True" in line else ("bad" if "match=False" in line else "dim")
        self.log_text.insert("end", line + "\n\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ------------------------------------------------- 6. CHECKLIST
    def _build_checks(self):
        p = self._page("checks")
        tk.Label(p, text="Verification Checklist", font=F("head", 15, "bold"), fg=CHAMPAGNE, bg=INK_DEEP).pack(anchor="w")
        tk.Label(p, text="Real tests, run live against the engine.", font=F("ui", 9),
                 fg=CHAMPAGNE_DIM, bg=INK_DEEP).pack(anchor="w", pady=(0, 10))
        self.check_rows = {}
        for name in ("Logic Consistency", "Whitespace Audit", "Data Normalization", "Type Integrity", "Output Clarity"):
            row = tk.Frame(p, bg=INK, highlightbackground=INK_LINE, highlightthickness=1)
            row.pack(fill="x", pady=4)
            tick = tk.Label(row, text="...", font=F("ui", 14, "bold"), fg=CHAMPAGNE_DIM, bg=INK, width=3)
            tick.pack(side="left", pady=8)
            col = tk.Frame(row, bg=INK)
            col.pack(side="left", fill="x", expand=True, pady=6)
            tk.Label(col, text=name, font=F("ui", 10, "bold"), fg=CHAMPAGNE, bg=INK, anchor="w").pack(fill="x")
            detail = tk.Label(col, text="", font=F("mono", 8), fg=CHAMPAGNE_DIM, bg=INK, anchor="w")
            detail.pack(fill="x")
            self.check_rows[name] = (tick, detail)

    # ------------------------------------------------- public API
    def refresh(self, session):
        score = session.score if session else 0
        self._set_state_label("score", f"score = {score}")
        self._set_state_label("question_index", f"question_index = {session.index if session else 0}")
        self._set_state_label("streak", f"streak = {session.streak if session else 0}")
        self._set_state_label("state", f"state = {(session.state if session else 'idle')!r}")
        self._set_state_label("type(score)", f"type(score) = {type(score).__name__}")
        for result in run_verification(score):
            tick, detail = self.check_rows[result["name"]]
            tick.config(text="\u2713" if result["ok"] else "\u2717", fg=SUCCESS if result["ok"] else DANGER)
            detail.config(text=result["detail"])

    def new_session(self, session):
        self._reset_gate()
        self.set_code(session)
        self.clear_log()
        self.refresh(session)

    def on_outcome(self, outcome, session):
        self.play_gate(outcome)
        if session.log:
            self.add_log(session.log[-1])
        self.refresh(session)
