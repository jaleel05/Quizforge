"""
Persistence: RAM -> Disk (JSON serialization), exactly the idea from the brief:
data in variables dies with the process, data in a file survives.

Saved: best score per mode, last 10 games, total stats, local leaderboard.
Corrupted / missing files never crash the app - we fall back to defaults.
"""

import copy
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
STATS_FILE = DATA_DIR / "stats.json"

DEFAULT_STATS = {
    "best": {"classic": 0, "challenge": 0},
    "games_played": 0,
    "total_correct": 0,
    "total_answered": 0,
    "history": [],        # last 10 games, newest first
    "leaderboard": [],    # top 10 per score, all modes
}


def _clean(data):
    """Validate whatever we loaded; keep only well-formed pieces."""
    stats = copy.deepcopy(DEFAULT_STATS)
    if not isinstance(data, dict):
        return stats
    best = data.get("best")
    if isinstance(best, dict):
        for mode in ("classic", "challenge"):
            if isinstance(best.get(mode), int):
                stats["best"][mode] = best[mode]
    for key in ("games_played", "total_correct", "total_answered"):
        if isinstance(data.get(key), int) and data[key] >= 0:
            stats[key] = data[key]
    for key in ("history", "leaderboard"):
        if isinstance(data.get(key), list):
            stats[key] = [row for row in data[key] if isinstance(row, dict)][:10]
    return stats


def load_stats(path=STATS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _clean(json.load(f))
    except (OSError, ValueError):          # missing file OR corrupted JSON
        return copy.deepcopy(DEFAULT_STATS)


def save_stats(stats, path=STATS_FILE):
    """Write to a temp file first, then swap - a crash can't corrupt the data."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def record_game(stats, name, mode, score, correct, total, category):
    """Updates stats in place. Returns True if this is a new personal best."""
    is_best = score > stats["best"].get(mode, 0)
    if is_best:
        stats["best"][mode] = score
    stats["games_played"] += 1
    stats["total_correct"] += correct
    stats["total_answered"] += total

    row = {"name": name or "Player", "mode": mode, "score": score, "correct": correct,
           "total": total, "category": category, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    stats["history"].insert(0, row)
    del stats["history"][10:]

    stats["leaderboard"].append(row)
    stats["leaderboard"].sort(key=lambda r: (r["mode"] == "challenge", r["score"]), reverse=True)
    del stats["leaderboard"][10:]
    return is_best


def accuracy(stats):
    answered = stats["total_answered"]
    return round(stats["total_correct"] / answered * 100) if answered else 0
