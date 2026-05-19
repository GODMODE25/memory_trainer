import os
import json
import urllib.request
import customtkinter as ctk
from PIL import Image

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except:
        pass


def get_save_path(username="DefaultUser"):
    base_dir = os.path.dirname(__file__)
    saves_dir = os.path.join(base_dir, "saves")
    os.makedirs(saves_dir, exist_ok=True)
    new_path = os.path.join(saves_dir, f"memory_save_{username}.json")
    
    # Automatic migration
    old_path = os.path.join(base_dir, f"memory_save_{username}.json")
    if os.path.exists(old_path) and not os.path.exists(new_path):
        try:
            import shutil
            shutil.move(old_path, new_path)
        except:
            pass
    return new_path


def default_save():
    return {
        "high_scores": [],
        "stats": {
            "games_played": 0,
            "correct": 0,
            "wrong": 0,
            "best_streak": 0,
            "best_level": 0,
            "total_score": 0,
        },
        "practice_stats": {
            "attempts": 0,
            "correct": 0,
            "best_streak": 0,
            "techniques_used": {},
            "total_memorize_time": 0.0,
        },
        "achievements": [],
        "daily_streak": 0,
        "last_played_date": "",
        "daily_quest": {
            "type": "Numbers",
            "target": 5,
            "current": 0,
            "completed": False,
            "date": ""
        }
    }


def load_save(username="DefaultUser"):
    filename = get_save_path(username)
    data = default_save()
    try:
        with open(filename, "r", encoding="utf-8") as save_file:
            loaded = json.load(save_file)
        if isinstance(loaded, dict):
            data["high_scores"] = loaded.get("high_scores", [])
            data["stats"].update(loaded.get("stats", {}))
            data["practice_stats"].update(loaded.get("practice_stats", {}))
            data["achievements"] = loaded.get("achievements", [])
            data["daily_streak"] = loaded.get("daily_streak", 0)
            data["last_played_date"] = loaded.get("last_played_date", "")
            data["daily_quest"] = loaded.get("daily_quest", data["daily_quest"])
    except (OSError, json.JSONDecodeError, TypeError):
        return default_save()
    return data


def save_save(data, username="DefaultUser"):
    filename = get_save_path(username)
    try:
        with open(filename, "w", encoding="utf-8") as save_file:
            json.dump(data, save_file, indent=2)
    except OSError:
        pass


def get_emoji_image(emoji_char, size=(20, 20)):
    try:
        codepoint = "-".join(f"{ord(c):x}" for c in emoji_char)
        base_dir = os.path.dirname(__file__)
        assets_dir = os.path.join(base_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        img_path = os.path.join(assets_dir, f"{codepoint}.png")
        
        if not os.path.exists(img_path):
            url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{codepoint}.png"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=3) as response, open(img_path, 'wb') as out_file:
                out_file.write(response.read())
                
        if os.path.exists(img_path):
            pil_img = Image.open(img_path)
            return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
    except:
        pass
    return None
