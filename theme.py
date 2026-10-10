"""
Emerald Ink + Champagne design system and the custom widgets that give
tkinter a premium look (rounded buttons, pills, cards).
"""

import sys
import tkinter as tk

# ---------------------------------------------------------------- palette
INK = "#064E3B"            # Emerald Ink  - main background
INK_DEEP = "#032F24"       # deeper ink   - panels, inputs
INK_CARD = "#0A6049"       # raised ink   - cards
INK_LINE = "#1F8267"       # hairline borders
CHAMPAGNE = "#F8E7C9"      # Champagne    - primary text
CHAMPAGNE_DIM = "#BFC9B0"  # softer text on ink
GOLD = "#E6C58B"           # warm champagne-gold accent
GOLD_DEEP = "#C79F55"
SUCCESS = "#8CEBBE"
DANGER = "#F4A78C"

# ------------------------------------------------------------------ fonts
if sys.platform == "darwin":
    _UI, _HEAD, _MONO = "Helvetica Neue", "Georgia", "Menlo"
elif sys.platform.startswith("win"):
    _UI, _HEAD, _MONO = "Segoe UI", "Georgia", "Consolas"
else:
    _UI, _HEAD, _MONO = "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono"


def F(kind, size, weight="normal", slant="roman"):
    """F('head', 28, 'bold') -> font tuple. kinds: head | ui | mono"""
    family = {"head": _HEAD, "ui": _UI, "mono": _MONO}[kind]
    return (family, size, weight, slant) if slant != "roman" else (family, size, weight)


# ---------------------------------------------------------------- widgets
def card(parent, bg=INK_CARD, border=INK_LINE, **kw):
    """A flat 'glass' card: raised ink with a 1px hairline border."""
    return tk.Frame(parent, bg=bg, highlightbackground=border, highlightcolor=border,
                    highlightthickness=1, **kw)


class RoundedButton(tk.Canvas):
    """Canvas-drawn rounded button with hover + disabled states."""

    def __init__(self, parent, text, command=None, width=160, height=44, radius=None,
                 bg=GOLD, fg=INK_DEEP, hover=CHAMPAGNE, outline=None, font=None, parent_bg=INK):
        super().__init__(parent, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.text, self.command = text, command
        self.w, self.h = width, height
        self.r = radius if radius is not None else height // 2
        self.bg, self.fg, self.hover_bg, self.outline = bg, fg, hover, outline
        self.font = font or F("ui", 11, "bold")
        self.enabled = True
        self._fill = bg
        self._draw()
        self.bind("<Enter>", lambda e: self._on_hover(True))
        self.bind("<Leave>", lambda e: self._on_hover(False))
        self.bind("<Button-1>", self._on_click)

    def _points(self):
        x1, y1, x2, y2, r = 1, 1, self.w - 1, self.h - 1, self.r
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    def _draw(self):
        self.delete("all")
        fill = self._fill if self.enabled else INK_LINE
        edge = self.outline or fill
        self.create_polygon(self._points(), smooth=True, fill=fill, outline=edge, width=2)
        color = self.fg if self.enabled else CHAMPAGNE_DIM
        self.create_text(self.w / 2, self.h / 2, text=self.text, fill=color, font=self.font)

    def _on_hover(self, inside):
        if not self.enabled:
            return
        self._fill = self.hover_bg if inside else self.bg
        self._draw()

    def _on_click(self, _event):
        if self.enabled and self.command:
            self.command()

    # public helpers
    def set_text(self, text):
        self.text = text
        self._draw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self._fill = self.bg
        self._draw()

    def set_colors(self, bg, fg, hover=None, outline=None):
        self.bg, self.fg = bg, fg
        self.hover_bg = hover or self.hover_bg
        self.outline = outline
        self._fill = bg
        self._draw()


class Pill(RoundedButton):
    """Selectable chip: gold when active, quiet outline when not."""

    def __init__(self, parent, text, command=None, width=110, height=34, parent_bg=INK, **kw):
        super().__init__(parent, text, command, width, height, parent_bg=parent_bg,
                         font=F("ui", 10, "bold"), **kw)
        self.active = False
        self.set_active(False)

    def set_active(self, active):
        self.active = active
        if active:
            self.set_colors(GOLD, INK_DEEP, hover=CHAMPAGNE, outline=GOLD)
        else:
            self.set_colors(INK_DEEP, CHAMPAGNE, hover=INK_CARD, outline=INK_LINE)


def ghost_button(parent, text, command, width=120, height=40, parent_bg=INK_CARD):
    """Outlined secondary button."""
    return RoundedButton(parent, text, command, width, height, bg=parent_bg, fg=CHAMPAGNE,
                         hover=INK_LINE, outline=GOLD_DEEP, parent_bg=parent_bg)
