import re
import random
import string
from memory_data import DIFFICULTIES, WORD_BANK


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


def compute_score_gain(length, time_left, hints_used, streak, difficulty_name, max_time):
    config = DIFFICULTIES[difficulty_name]
    streak_bonus = 1 + (streak // 3)
    base = length * 10 * config["mult"] * streak_bonus
    time_bonus = base * 0.5 * (time_left / max(1.0, max_time))
    penalty = hints_used * 25
    return max(5, int(base + time_bonus - penalty))


def calculate_account_level(total_score):
    return min(100, 1 + (total_score // 500))
