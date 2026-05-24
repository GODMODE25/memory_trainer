import re
import random
import string
from memory_data import DIFFICULTIES, WORD_BANK
from memory_levels import get_digit_level


def compute_length(level, difficulty):
    config = DIFFICULTIES[difficulty]
    return config["start"] + ((level - 1) // 2) * config["growth"]


def generate_challenge(mode, length):
    if mode == "Numbers":
        return "".join(random.choice(string.digits) for _ in range(length))
    if mode == "Phone":
        prefix = random.choice(["070", "080", "081", "090", "091"])
        return prefix + "".join(random.choice(string.digits) for _ in range(8))
    if mode == "Alphanumeric":
        pool = string.ascii_uppercase + string.digits
        return "".join(random.choice(pool) for _ in range(length))
    if mode == "Words":
        count = max(2, min(6, length // 2))
        return " ".join(random.choice(WORD_BANK) for _ in range(count))
    pool = string.ascii_uppercase[:6] + string.digits
    return ", ".join(random.choice(pool) for _ in range(length))


def normalize_compare(mode, user_input, answer):
    user_input = user_input.strip()
    answer = answer.strip()
    
    if mode == "Words":
        user_words = re.findall(r"\b\w+\b", user_input.lower())
        answer_words = re.findall(r"\b\w+\b", answer.lower())
        return user_words == answer_words
    
    user_clean = "".join(c.lower() for c in user_input if c.isalnum())
    answer_clean = "".join(c.lower() for c in answer if c.isalnum())
    return user_clean == answer_clean


def analyze_digit_answer(user_input, answer):
    user_clean = "".join(char for char in user_input if char.isdigit())
    answer_clean = "".join(char for char in answer if char.isdigit())
    total = len(answer_clean)
    details = []
    correct_digits = 0

    for index in range(max(len(user_clean), total)):
        expected = answer_clean[index] if index < total else ""
        actual = user_clean[index] if index < len(user_clean) else ""
        correct = bool(expected) and actual == expected
        if correct:
            correct_digits += 1
        details.append({
            "position": index + 1,
            "expected": expected,
            "actual": actual,
            "correct": correct,
            "missing": bool(expected and not actual),
            "extra": bool(actual and not expected),
        })

    accuracy = int((correct_digits / total) * 100) if total else 0
    return {
        "correct": user_clean == answer_clean,
        "correct_digits": correct_digits,
        "total_digits": total,
        "accuracy": accuracy,
        "details": details,
        "user_clean": user_clean,
        "answer_clean": answer_clean,
    }


def compute_score_gain(length, time_left, hints_used, streak, difficulty_name, max_time):
    config = DIFFICULTIES[difficulty_name]
    streak_bonus = 1 + (streak // 3)
    base = length * 10 * config["mult"] * streak_bonus
    time_bonus = base * 0.5 * (time_left / max(1.0, max_time))
    penalty = hints_used * 25
    return max(5, int(base + time_bonus - penalty))


def compute_digit_track_score(level_id, accuracy, time_left, hints_used, streak, max_time):
    level = get_digit_level(level_id)
    streak_bonus = 1 + (streak // 3)
    accuracy_factor = max(0.0, accuracy / 100)
    base = level["digits"] * 20 * accuracy_factor
    speed_bonus = base * 0.5 * (time_left / max(1.0, max_time))
    level_bonus = level["id"] * 8
    penalty = hints_used * 30
    return max(5, int((base + speed_bonus + level_bonus) * streak_bonus - penalty))


def calculate_account_level(total_score):
    return min(100, 1 + (total_score // 500))
