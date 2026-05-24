import os

APP_TITLE = "Memory Trainer Quest"
APP_VERSION = "2.0.0"
WINDOW_SIZE = "1120x720"
SAVE_FILE = os.path.join(os.path.dirname(__file__), "memory_save.json")
SESSION_TYPES = ["Game", "Practice"]
GAME_MODES = ["Numbers", "Phone", "Alphanumeric", "Words", "Sequence"]
PLAY_STYLES = ["Classic", "Digit Track"]
TECHNIQUES = ["Auto Coach", "Chunking", "Story Link", "Memory Palace", "Sound/Rhythm"]
HEADER_COLOR = "#3b82f6"
SUBHEADER_COLOR = "#22c55e"
BODY_COLOR = ("gray18", "gray86")
CHALLENGE_COLORS = ["#38bdf8", "#f59e0b", "#a78bfa", "#34d399"]
PALACE_LOCATIONS = ["door", "sofa", "table", "window", "stairs", "shelf"]

MNEMONIC_TIPS = {
    "Numbers": {
        "Chunking": "Split the number into small blocks. Three digits at a time is easier to hold than one long stream.",
        "Story Link": "Turn each chunk into a quick image, then connect the images in a tiny story.",
        "Memory Palace": "Place each chunk at a familiar location and walk through those locations in order.",
        "Sound/Rhythm": "Say the chunks in beats. Rhythm gives the sequence a shape your ear can remember.",
    },
    "Phone": {
        "Chunking": "Treat the prefix as one familiar block, then group the remaining digits in threes.",
        "Story Link": "Make the phone chunks into images and connect them like scenes in a short advert.",
        "Memory Palace": "Put the prefix at the door, then place each later chunk around the room.",
        "Sound/Rhythm": "Say it like a phone number: prefix, pause, middle, pause, ending.",
    },
    "Alphanumeric": {
        "Chunking": "Group letters and numbers into small teams so each block becomes one unit.",
        "Story Link": "Read letters as initials and numbers as props, then make one odd little scene.",
        "Memory Palace": "Drop each mixed block at a fixed location and retrieve them in that order.",
        "Sound/Rhythm": "Read the blocks aloud with a steady beat to reduce swapping errors.",
    },
    "Words": {
        "Chunking": "Pair nearby words into mini-phrases before recalling the full list.",
        "Story Link": "Make the words interact in one vivid sentence. Strange links stick better.",
        "Memory Palace": "Place each word at a location and mentally walk the route.",
        "Sound/Rhythm": "Say the words in a repeated cadence, like a line from a chant.",
    },
    "Sequence": {
        "Chunking": "Group the sequence into short runs and preserve the exact order inside each run.",
        "Story Link": "Turn each token into an object and make the objects bump into each other in order.",
        "Memory Palace": "Assign each run to a location and walk through the runs.",
        "Sound/Rhythm": "Echo it back in beats. Beat one, beat two, beat three.",
    },
}

DIFFICULTIES = {
    "Easy": {"start": 4, "growth": 1, "display": 4.0, "recall": 12.0, "lives": 5, "mult": 1.0},
    "Medium": {"start": 6, "growth": 1, "display": 3.0, "recall": 9.0, "lives": 4, "mult": 1.35},
    "Hard": {"start": 8, "growth": 2, "display": 2.4, "recall": 7.0, "lives": 3, "mult": 1.8},
    "Insane": {"start": 10, "growth": 2, "display": 1.8, "recall": 5.5, "lives": 2, "mult": 2.5},
}

WORD_BANK = [
    "apple", "badge", "cable", "delta", "ember", "focus", "globe", "harbor",
    "island", "jungle", "kernel", "lantern", "matrix", "nectar", "orbit",
    "puzzle", "quartz", "rocket", "silver", "timber", "velvet", "wander",
    "yellow", "zipper", "anchor", "binary", "cobalt", "dragon", "energy",
    "fabric", "garden", "horizon", "magnet", "signal", "voyage",
]

ACHIEVEMENTS = [
    {"id": "first_correct", "name": "First Spark", "description": "Recall one challenge.", "icon": "💡", "predicate": "correct>=1"},
    {"id": "streak_5", "name": "Hot Streak", "description": "Reach a 5-round streak.", "icon": "🔥", "predicate": "streak>=5"},
    {"id": "score_1000", "name": "Four Digits", "description": "Score 1000 points.", "icon": "💎", "predicate": "score>=1000"},
    {"id": "level_10", "name": "Climber", "description": "Reach level 10.", "icon": "🧗", "predicate": "level>=10"},
    {"id": "insane_perfect", "name": "Steel Nerves", "description": "Get an Insane round right without hints.", "icon": "🦾", "predicate": "perfect_round_insane"},
    {"id": "digit_level_1", "name": "Track Starter", "description": "Clear the first Digit Track level.", "icon": "🎯", "predicate": "digit_level>=1"},
    {"id": "digit_level_5", "name": "Five Rungs", "description": "Clear five Digit Track levels.", "icon": "📈", "predicate": "digit_level>=5"},
    {"id": "digit_perfect_10", "name": "Ten Clean", "description": "Perfectly recall a 10+ digit challenge.", "icon": "🏆", "predicate": "perfect_digits>=10"},
    {"id": "digit_speed", "name": "Quick Capture", "description": "Perfectly recall a Digit Track round with at least 40% recall time left.", "icon": "🚀", "predicate": "digit_speed"},
    {"id": "digit_all_levels", "name": "Ultimate Champion", "description": "Clear all 13 Digit Track levels.", "icon": "🏅", "predicate": "digit_level>=13"},
]
