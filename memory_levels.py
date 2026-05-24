DIGIT_TRACK_LEVELS = [
    {"id": 1, "name": "Foundation", "digits": 3, "display": 5.0, "required_accuracy": 70, "icon": "🎯"},
    {"id": 2, "name": "Building Up", "digits": 4, "display": 6.0, "required_accuracy": 70, "icon": "🏗️"},
    {"id": 3, "name": "Pattern Spotter", "digits": 5, "display": 7.0, "required_accuracy": 70, "icon": "🔍"},
    {"id": 4, "name": "Memory Stretch", "digits": 6, "display": 8.0, "required_accuracy": 70, "icon": "💪"},
    {"id": 5, "name": "The Challenge", "digits": 7, "display": 10.0, "required_accuracy": 70, "icon": "⚡"},
    {"id": 6, "name": "Advanced Training", "digits": 8, "display": 12.0, "required_accuracy": 70, "icon": "🎓"},
    {"id": 7, "name": "Speed Builder", "digits": 9, "display": 14.0, "required_accuracy": 70, "icon": "🚀"},
    {"id": 8, "name": "Expert Level", "digits": 10, "display": 16.0, "required_accuracy": 70, "icon": "🏆"},
    {"id": 9, "name": "Master Challenge", "digits": 11, "display": 18.0, "required_accuracy": 70, "icon": "👑"},
    {"id": 10, "name": "Elite Performance", "digits": 12, "display": 20.0, "required_accuracy": 70, "icon": "💎"},
    {"id": 11, "name": "Legend Status", "digits": 13, "display": 22.0, "required_accuracy": 70, "icon": "⭐"},
    {"id": 12, "name": "Supreme Master", "digits": 14, "display": 24.0, "required_accuracy": 70, "icon": "🌟"},
    {"id": 13, "name": "Ultimate Champion", "digits": 15, "display": 26.0, "required_accuracy": 70, "icon": "🏅"},
]

RECENT_WINDOW = 5
UNLOCK_CORRECT_TARGET = 3


def get_digit_level(level_id):
    safe_id = max(1, min(13, int(level_id or 1)))
    return DIGIT_TRACK_LEVELS[safe_id - 1]


def default_digit_track():
    return {
        "current_level": 1,
        "unlocked_levels": [1],
        "levels": {
            str(level["id"]): {
                "attempts": 0,
                "correct": 0,
                "best_score": 0,
                "best_accuracy": 0,
                "recent": [],
                "cleared": False,
            }
            for level in DIGIT_TRACK_LEVELS
        },
    }


def merge_digit_track(loaded):
    merged = default_digit_track()
    if not isinstance(loaded, dict):
        return merged

    merged["current_level"] = int(loaded.get("current_level", 1) or 1)
    unlocked = loaded.get("unlocked_levels", [1])
    if isinstance(unlocked, list):
        merged["unlocked_levels"] = sorted({1, *[int(item) for item in unlocked if str(item).isdigit()]})

    loaded_levels = loaded.get("levels", {})
    if isinstance(loaded_levels, dict):
        for level_id, defaults in merged["levels"].items():
            old = loaded_levels.get(level_id, {})
            if isinstance(old, dict):
                defaults.update({
                    "attempts": int(old.get("attempts", defaults["attempts"]) or 0),
                    "correct": int(old.get("correct", defaults["correct"]) or 0),
                    "best_score": int(old.get("best_score", defaults["best_score"]) or 0),
                    "best_accuracy": int(old.get("best_accuracy", defaults["best_accuracy"]) or 0),
                    "recent": list(old.get("recent", defaults["recent"]))[-RECENT_WINDOW:],
                    "cleared": bool(old.get("cleared", defaults["cleared"])),
                })

    max_unlocked = max(merged["unlocked_levels"] or [1])
    merged["current_level"] = max(1, min(max_unlocked, merged["current_level"]))
    return merged


def record_digit_track_result(track, level_id, correct, accuracy, score):
    level_id = int(level_id)
    track = merge_digit_track(track)
    stats = track["levels"][str(level_id)]
    stats["attempts"] += 1
    if correct:
        stats["correct"] += 1
    stats["best_score"] = max(stats.get("best_score", 0), int(score or 0))
    stats["best_accuracy"] = max(stats.get("best_accuracy", 0), int(accuracy or 0))
    stats["recent"] = (stats.get("recent", []) + [{"correct": bool(correct), "accuracy": int(accuracy or 0)}])[-RECENT_WINDOW:]

    unlocked = False
    recent = stats["recent"]
    recent_accuracy = int(sum(item.get("accuracy", 0) for item in recent) / len(recent)) if recent else 0
    if stats["correct"] >= UNLOCK_CORRECT_TARGET and recent_accuracy >= get_digit_level(level_id)["required_accuracy"]:
        stats["cleared"] = True
        next_level = level_id + 1
        if next_level <= len(DIGIT_TRACK_LEVELS) and next_level not in track["unlocked_levels"]:
            track["unlocked_levels"].append(next_level)
            track["unlocked_levels"].sort()
            track["current_level"] = next_level
            unlocked = True

    return track, unlocked, recent_accuracy
