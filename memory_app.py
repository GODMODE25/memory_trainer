import customtkinter as ctk
import datetime
import os
import random
import string
import time

from memory_data import *
from memory_utils import (
    load_config,
    save_config,
    load_save,
    save_save,
    get_save_path,
    get_emoji_image,
    default_save,
)
from memory_engine import (
    compute_length,
    generate_challenge,
    normalize_compare,
    compute_score_gain,
    calculate_account_level,
)
from memory_auth import AuthWindow
from memory_achievements import AchievementsWindow


class MemoryApp(ctk.CTk):
    @property
    def account_level(self):
        try:
            total_score = self.save_data.get("stats", {}).get("total_score", 0) + getattr(self, "score", 0)
            return calculate_account_level(total_score)
        except AttributeError:
            return 1

    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(640, 520)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.current_challenge = ""
        self.game_state = "idle"
        self.recall_deadline = None
        self.recall_after_id = None
        self.tick_after_id = None
        self.stats_flushed = True
        self.score_recorded = True
        self.achievement_message = ""
        self.narrow_layout = None
        self.resize_after_id = None
        self.username = "DefaultUser" # Fallback
        self.icon_cache = {}
        self._prefetch_completed = False
        import threading
        threading.Thread(target=self._prefetch_icons, daemon=True).start()
        self.after(200, self._check_prefetch_done)

        # Check for remembered user
        config = load_config()
        remembered = config.get("remembered_user")
        
        self.session_type_var = ctk.StringVar(value="Game")
        self.mode_var = ctk.StringVar(value="Numbers")
        self.difficulty_var = ctk.StringVar(value="Medium")
        self.theme_var = ctk.StringVar(value="System")
        self.technique_var = ctk.StringVar(value="Auto Coach")
        self.assist_var = ctk.BooleanVar(value=True)
        self.timer_var = ctk.BooleanVar(value=True)

        self._build_ui()
        
        if remembered and os.path.exists(get_save_path(remembered)):
            self.username = remembered
            self.save_data = load_save(self.username)
            self._on_login_success()
        else:
            # We must show the auth screen after the main window is created
            self.after(100, self._show_auth_screen)
        self._fit_initial_window()
        self.bind("<Configure>", self._on_resize)
        self.bind("<F12>", self.capture_screenshot)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _show_auth_screen(self):
        def on_auth_success(username, save_data):
            self.username = username
            self.save_data = save_data
            self._on_login_success()
            
        AuthWindow(self, on_auth_success)

    def _on_login_success(self):
        self._reset_run_state()
        self._check_daily_streak(check_only=True)
        self._check_daily_quest()
        self._load_user_settings()
        self._refresh_hud()
        self.title(f"{APP_TITLE} - Logged in as {self.username}")

    def _load_user_settings(self):
        config = load_config()
        user_key = f"settings_{self.username}"
        settings = config.get(user_key) or config.get("last_settings")
        if settings:
            if "session_type" in settings:
                self.session_type_var.set(settings["session_type"])
            if "mode" in settings:
                self.mode_var.set(settings["mode"])
            if "difficulty" in settings:
                self.difficulty_var.set(settings["difficulty"])
            if "theme" in settings:
                theme = settings["theme"]
                self.theme_var.set(theme)
                ctk.set_appearance_mode(theme)
            if "technique" in settings:
                self.technique_var.set(settings["technique"])
            if "assist" in settings:
                self.assist_var.set(settings["assist"])
            if "timer" in settings:
                self.timer_var.set(settings["timer"])
            
            # Sync sliders to match loaded difficulty/session settings
            if self.is_practice_mode():
                self.display_slider.set(max(self.display_slider.get(), 5.0))
                self.recall_slider.set(max(self.recall_slider.get(), 15.0))
            else:
                cfg = self._difficulty_config()
                self.display_slider.set(cfg["display"])
                self.recall_slider.set(cfg["recall"])
            self.update_display_label(self.display_slider.get())
            self.update_recall_label(self.recall_slider.get())
            self.reset_game()

    def _save_user_settings(self):
        if not self.username or self.username == "DefaultUser":
            return
        config = load_config()
        user_key = f"settings_{self.username}"
        settings = {
            "session_type": self.session_type_var.get(),
            "mode": self.mode_var.get(),
            "difficulty": self.difficulty_var.get(),
            "theme": self.theme_var.get(),
            "technique": self.technique_var.get(),
            "assist": self.assist_var.get(),
            "timer": self.timer_var.get(),
        }
        config[user_key] = settings
        config["last_settings"] = settings
        save_config(config)

    def _on_logout(self):
        save_config({})
        self.username = "DefaultUser"
        self.save_data = default_save()
        self._show_auth_screen()

    def _check_daily_streak(self, check_only=False):
        today = datetime.date.today().isoformat()
        last_played = self.save_data.get("last_played_date", "")
        
        if last_played == today:
            return
            
        if last_played:
            last_date = datetime.date.fromisoformat(last_played)
            if (datetime.date.today() - last_date).days > 1:
                self.save_data["daily_streak"] = 0
                save_save(self.save_data, self.username)
                
        if not check_only:
            self.save_data["daily_streak"] = self.save_data.get("daily_streak", 0) + 1
            self.save_data["last_played_date"] = today
            save_save(self.save_data, self.username)
            self._refresh_hud()

    def _check_daily_quest(self):
        today = datetime.date.today().isoformat()
        quest = self.save_data.get("daily_quest", {})
        
        if quest.get("date") != today:
            modes = ["Numbers", "Words", "Alphanumeric"]
            quest_type = random.choice(modes)
            self.save_data["daily_quest"] = {
                "type": quest_type,
                "target": 5,
                "current": 0,
                "completed": False,
                "date": today
            }
            save_save(self.save_data, self.username)

    def _reset_run_state(self):
        config = self._difficulty_config()
        self.score = 0
        self.level = 1
        self.lives = config["lives"]
        self.streak = 0
        self.best_streak = 0
        self.round_no = 0
        self.correct_count = 0
        self.wrong_count = 0
        self.practice_attempts = 0
        self.practice_correct = 0
        self.practice_streak = 0
        self.practice_best_streak = 0
        self.practice_techniques_used = {}
        self.practice_total_memorize_time = 0.0
        self.hints_used = 0
        self.combo_multiplier = 1
        self.stats_flushed = False
        self.score_recorded = False

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.top_bar = ctk.CTkFrame(self, corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(9, weight=1)

        ctk.CTkLabel(self.top_bar, text="Session", text_color=SUBHEADER_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(14, 6), pady=(10, 4))
        self.session_menu = ctk.CTkOptionMenu(self.top_bar, values=SESSION_TYPES, variable=self.session_type_var, command=self._on_session_change, width=100)
        self.session_menu.grid(row=0, column=1, padx=(0, 12), pady=10)

        ctk.CTkLabel(self.top_bar, text="Mode", text_color=SUBHEADER_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=(0, 6), pady=(10, 4))
        self.mode_menu = ctk.CTkOptionMenu(self.top_bar, values=GAME_MODES, variable=self.mode_var, command=self._on_mode_change, width=130)
        self.mode_menu.grid(row=0, column=3, padx=(0, 12), pady=(10, 4))

        ctk.CTkLabel(self.top_bar, text="Difficulty", text_color=SUBHEADER_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=(0, 6), pady=(10, 4))
        self.difficulty_menu = ctk.CTkOptionMenu(self.top_bar, values=list(DIFFICULTIES), variable=self.difficulty_var, command=self._on_difficulty_change, width=120)
        self.difficulty_menu.grid(row=0, column=5, padx=(0, 12), pady=(10, 4))

        ctk.CTkLabel(self.top_bar, text="Theme", text_color=SUBHEADER_COLOR, font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=(14, 6), pady=(4, 10))
        self.theme_menu = ctk.CTkOptionMenu(self.top_bar, values=["System", "Dark", "Light"], variable=self.theme_var, command=self._on_theme_change, width=105)
        self.theme_menu.grid(row=1, column=1, padx=(0, 12), pady=(4, 10))

        self.assist_check = ctk.CTkCheckBox(self.top_bar, text="Assist", variable=self.assist_var, command=self._redraw_current_challenge, width=74)
        self.assist_check.grid(row=1, column=2, padx=(0, 12), pady=(4, 10), sticky="w")

        self.timer_check = ctk.CTkCheckBox(self.top_bar, text="Timer", variable=self.timer_var, width=74)
        self.timer_check.grid(row=1, column=3, padx=(0, 12), pady=(4, 10), sticky="w")

        self.about_button = ctk.CTkButton(self.top_bar, text="About", width=80, command=self.show_about)
        self.about_button.grid(row=0, column=6, padx=(0, 12), pady=(10, 4))

        self.top_high_score_label = ctk.CTkLabel(self.top_bar, text="High Score: 0", text_color=HEADER_COLOR, font=ctk.CTkFont(weight="bold"))
        self.top_high_score_label.grid(row=1, column=9, padx=(0, 14), pady=(4, 10), sticky="e")

        self.top_streak_label = ctk.CTkLabel(self.top_bar, text="Streak: 0", text_color=HEADER_COLOR, font=ctk.CTkFont(weight="bold"))
        self.top_streak_label.grid(row=1, column=8, padx=(0, 12), pady=(4, 10), sticky="e")

        self.logout_button = ctk.CTkButton(self.top_bar, text="Logout", width=60, command=self._on_logout)
        self.logout_button.grid(row=0, column=9, padx=(0, 14), pady=(10, 4), sticky="e")

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=3)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.game_area = ctk.CTkScrollableFrame(self.main_frame)
        self.game_area.grid(row=0, column=0, padx=(0, 12), sticky="nsew")
        self.game_area.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.game_area, text="Memory Trainer", font=ctk.CTkFont(family="Impact", size=36), text_color=HEADER_COLOR)
        self.title_label.grid(row=0, column=0, padx=20, pady=(22, 12))

        self.challenge_frame = ctk.CTkFrame(self.game_area, fg_color="transparent")
        self.challenge_frame.grid(row=1, column=0, padx=20, pady=(18, 14), sticky="ew")
        self.challenge_frame.grid_columnconfigure(0, weight=1)
        self.challenge_label = ctk.CTkLabel(self.challenge_frame, text="Click Start to begin", font=ctk.CTkFont(family="Consolas", size=34, weight="bold"), wraplength=460)
        self.challenge_label.grid(row=0, column=0, sticky="ew")
        self.challenge_widgets = [self.challenge_label]

        progress_row = ctk.CTkFrame(self.game_area, fg_color="transparent")
        progress_row.grid(row=2, column=0, padx=24, pady=(0, 10), sticky="ew")
        progress_row.grid_columnconfigure(0, weight=1)
        self.recall_progress = ctk.CTkProgressBar(progress_row)
        self.recall_progress.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.recall_progress.set(0)
        self.countdown_label = ctk.CTkLabel(progress_row, text="0.0s", width=54)
        self.countdown_label.grid(row=0, column=1)

        self.entry = ctk.CTkEntry(self.game_area, placeholder_text="Enter the value here", width=290, justify="center", font=ctk.CTkFont(size=16))
        self.entry.grid(row=3, column=0, padx=24, pady=8)
        self.entry.configure(state="disabled")
        self.entry.bind("<Return>", lambda _event: self.check_number())

        self.result_label = ctk.CTkLabel(self.game_area, text="", font=ctk.CTkFont(size=16), wraplength=500)
        self.result_label.grid(row=4, column=0, padx=20, pady=10)

        button_row = ctk.CTkFrame(self.game_area, fg_color="transparent")
        button_row.grid(row=5, column=0, padx=20, pady=12)
        
        self.start_button = ctk.CTkButton(
            button_row, 
            text="Start", 
            command=self.start_game, 
            width=150, 
            height=45, 
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#8a2be2",
            hover_color="#7b1fa2"
        )
        self.start_button.grid(row=0, column=1, padx=10, pady=5)
        
        self.hint_button = ctk.CTkButton(button_row, text="Hint", command=self.show_hint, width=82, state="disabled")
        self.hint_button.grid(row=0, column=0, padx=5)
        self.skip_button = ctk.CTkButton(button_row, text="Skip", command=self.skip_round, width=82, state="disabled")
        self.skip_button.grid(row=0, column=2, padx=5)
        self.reset_button = ctk.CTkButton(button_row, text="Reset", command=self.reset_game, width=82)
        self.reset_button.grid(row=0, column=3, padx=5)

        slider_frame = ctk.CTkFrame(self.game_area, fg_color="transparent")
        slider_frame.grid(row=6, column=0, padx=24, pady=(18, 20), sticky="ew")
        slider_frame.grid_columnconfigure(1, weight=1)

        config = self._difficulty_config()
        self.display_label = ctk.CTkLabel(slider_frame, text=f"Display time: {config['display']:.1f}s", width=130, anchor="w")
        self.display_label.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        self.display_slider = ctk.CTkSlider(slider_frame, from_=1, to=10, number_of_steps=18, command=self.update_display_label)
        self.display_slider.set(config["display"])
        self.display_slider.grid(row=0, column=1, pady=5, sticky="ew")

        self.recall_label = ctk.CTkLabel(slider_frame, text=f"Recall time: {config['recall']:.1f}s", width=130, anchor="w")
        self.recall_label.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
        self.recall_slider = ctk.CTkSlider(slider_frame, from_=3, to=20, number_of_steps=34, command=self.update_recall_label)
        self.recall_slider.set(config["recall"])
        self.recall_slider.grid(row=1, column=1, pady=5, sticky="ew")

        self.hud_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.hud_frame.grid(row=0, column=1, sticky="nsew")
        self.hud_frame.grid_columnconfigure(0, weight=1)

        self.game_sidebar = ctk.CTkFrame(self.hud_frame, fg_color="transparent")
        self.game_sidebar.grid(row=0, column=0, sticky="nsew")
        self.game_sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.game_sidebar, text="HUD", font=ctk.CTkFont(size=18, weight="bold"), text_color=HEADER_COLOR).grid(row=0, column=0, padx=14, pady=(16, 8), sticky="w")
        hud_font = ctk.CTkFont(size=14, weight="bold")
        self.score_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#f59e0b")
        self.account_level_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#38bdf8")
        self.level_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#a78bfa")
        self.lives_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#f43f5e")
        self.streak_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#fdba74")
        self.round_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#94a3b8")
        self.accuracy_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#34d399")
        self.best_label = ctk.CTkLabel(self.game_sidebar, text="", font=hud_font, text_color="#fbbf24")
        for row, label in enumerate([self.score_label, self.account_level_label, self.level_label, self.lives_label, self.streak_label, self.round_label, self.accuracy_label, self.best_label], start=1):
            label.grid(row=row, column=0, padx=14, pady=2, sticky="w")

        ctk.CTkLabel(self.game_sidebar, text="Top 5 🏆", font=ctk.CTkFont(size=15, weight="bold"), text_color=SUBHEADER_COLOR).grid(row=9, column=0, padx=14, pady=(14, 4), sticky="w")
        self.high_scores_frame = ctk.CTkFrame(self.game_sidebar, fg_color="transparent")
        self.high_scores_frame.grid(row=10, column=0, padx=14, sticky="ew")

        self.achievements_button = ctk.CTkButton(self.game_sidebar, text="Achievements 🏆", command=self.show_achievements, font=ctk.CTkFont(weight="bold"))
        self.achievements_button.grid(row=11, column=0, padx=14, pady=(16, 10), sticky="ew")

        self.quest_frame = ctk.CTkFrame(self.game_sidebar, fg_color="transparent")
        self.quest_frame.grid(row=12, column=0, padx=14, sticky="ew")

        self.coach_sidebar = ctk.CTkFrame(self.hud_frame, fg_color="transparent")
        self.coach_sidebar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.coach_sidebar, text="Coach", font=ctk.CTkFont(size=18, weight="bold"), text_color=HEADER_COLOR).grid(row=0, column=0, padx=14, pady=(16, 8), sticky="w")
        ctk.CTkLabel(self.coach_sidebar, text="Technique", font=ctk.CTkFont(size=14, weight="bold"), text_color=SUBHEADER_COLOR).grid(row=1, column=0, padx=14, pady=(6, 4), sticky="w")
        self.technique_menu = ctk.CTkOptionMenu(self.coach_sidebar, values=TECHNIQUES, variable=self.technique_var, command=self._on_technique_change)
        self.technique_menu.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")
        self.coach_title_label = ctk.CTkLabel(self.coach_sidebar, text="Practice Mode", font=ctk.CTkFont(size=15, weight="bold"), text_color=SUBHEADER_COLOR, anchor="w")
        self.coach_title_label.grid(row=3, column=0, padx=14, pady=(4, 4), sticky="ew")
        self.coach_instruction_label = ctk.CTkLabel(self.coach_sidebar, text="", wraplength=210, justify="left", anchor="w")
        self.coach_instruction_label.grid(row=4, column=0, padx=14, pady=4, sticky="ew")
        self.coach_example_label = ctk.CTkLabel(self.coach_sidebar, text="", wraplength=210, justify="left", anchor="w")
        self.coach_example_label.grid(row=5, column=0, padx=14, pady=4, sticky="ew")
        self.coach_review_label = ctk.CTkLabel(self.coach_sidebar, text="", wraplength=210, justify="left", anchor="w")
        self.coach_review_label.grid(row=6, column=0, padx=14, pady=(10, 4), sticky="ew")
        hud_font = ctk.CTkFont(size=14, weight="bold")
        self.practice_attempts_label = ctk.CTkLabel(self.coach_sidebar, text="", font=hud_font, text_color="#f59e0b")
        self.practice_correct_label = ctk.CTkLabel(self.coach_sidebar, text="", font=hud_font, text_color="#34d399")
        self.practice_accuracy_label = ctk.CTkLabel(self.coach_sidebar, text="", font=hud_font, text_color="#a78bfa")
        self.practice_best_streak_label = ctk.CTkLabel(self.coach_sidebar, text="", font=hud_font, text_color="#fdba74")
        self.practice_time_label = ctk.CTkLabel(self.coach_sidebar, text="", font=hud_font, text_color="#38bdf8")

        for row, label in enumerate([self.practice_attempts_label, self.practice_correct_label, self.practice_accuracy_label, self.practice_best_streak_label, self.practice_time_label], start=7):
            label.grid(row=row, column=0, padx=14, pady=2, sticky="w")

    def _get_icon_image(self, emoji_char, size=(20, 20)):
        cache_key = (emoji_char, size)
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
            
        img = get_emoji_image(emoji_char, size)
        if img:
            self.icon_cache[cache_key] = img
        return img

    def _prefetch_icons(self):
        icons_to_fetch = ["🎯", "⭐", "📈", "💖", "🔥", "🔄", "📊", "⚡", "📜", "🎉", "💡", "💎", "🧗", "🦾", "🔒", "✅", "⏱"]
        for icon in icons_to_fetch:
            get_emoji_image(icon)
        self._prefetch_completed = True

    def _check_prefetch_done(self):
        if self._prefetch_completed:
            self._refresh_hud()
        else:
            self.after(200, self._check_prefetch_done)

    def _difficulty_config(self):
        return DIFFICULTIES[self.difficulty_var.get()]

    def show_about(self):
        popup = ctk.CTkToplevel(self)
        popup.title("About")
        popup.geometry("400x300")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        
        title_lbl = ctk.CTkLabel(popup, text="Memory Trainer Quest", font=ctk.CTkFont(size=20, weight="bold"), text_color=HEADER_COLOR)
        title_lbl.pack(padx=20, pady=(20, 10))
        
        desc_lbl = ctk.CTkLabel(popup, text=f"A tool to train your memory using various techniques like Chunking, Story Link, and Memory Palace.\n\nVersion {APP_VERSION} (Modular Edition)\n\nBuilt with CustomTkinter.\n\nSamuel Musa (c) 2026", wraplength=350, justify="left")
        desc_lbl.pack(padx=20, pady=10)
        
        close_btn = ctk.CTkButton(popup, text="Close", command=popup.destroy)
        close_btn.pack(pady=(20, 10))

    def _fit_initial_window(self):
        self.update_idletasks()
        requested_width = max(self.winfo_reqwidth() + 40, 1120)
        requested_height = max(self.winfo_reqheight() + 40, 720)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(requested_width, max(640, screen_width - 80))
        height = min(requested_height, max(520, screen_height - 100))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self._apply_responsive_layout()

    def _on_resize(self, event):
        if event.widget is not self:
            return
        if self.resize_after_id is not None:
            try:
                self.after_cancel(self.resize_after_id)
            except ValueError:
                pass
        self.resize_after_id = self.after(80, self._apply_responsive_layout)

    def _window_width(self):
        try:
            return int(self.geometry().split("x", 1)[0])
        except (TypeError, ValueError, IndexError):
            return self.winfo_width()

    def _apply_responsive_layout(self):
        self.resize_after_id = None
        width = self._window_width()
        use_narrow = width < 900
        if use_narrow != self.narrow_layout:
            self.narrow_layout = use_narrow
            self.game_area.grid_forget()
            self.hud_frame.grid_forget()
            if use_narrow:
                self.main_frame.grid_columnconfigure(0, weight=1)
                self.main_frame.grid_columnconfigure(1, weight=0)
                self.main_frame.grid_rowconfigure(0, weight=1)
                self.main_frame.grid_rowconfigure(1, weight=1)
                self.game_area.grid(row=0, column=0, padx=0, pady=(0, 12), sticky="nsew")
                self.hud_frame.grid(row=1, column=0, sticky="nsew")
            else:
                self.main_frame.grid_columnconfigure(0, weight=3)
                self.main_frame.grid_columnconfigure(1, weight=1)
                self.main_frame.grid_rowconfigure(0, weight=1)
                self.main_frame.grid_rowconfigure(1, weight=0)
                self.game_area.grid(row=0, column=0, padx=(0, 12), pady=0, sticky="nsew")
                self.hud_frame.grid(row=0, column=1, sticky="nsew")
        self._update_wrap_lengths()

    def _update_wrap_lengths(self):
        window_width = max(320, self._window_width())
        content_width = window_width - (80 if self.narrow_layout else 360)
        challenge_wrap = max(260, min(720, content_width))
        sidebar_wrap = max(220, min(520, window_width - 80 if self.narrow_layout else 260))
        self.result_label.configure(wraplength=challenge_wrap)
        if hasattr(self, "challenge_label"):
            self.challenge_label.configure(wraplength=challenge_wrap)
        for label in (self.coach_instruction_label, self.coach_example_label, self.coach_review_label):
            label.configure(wraplength=sidebar_wrap)
        if self.current_challenge and self.game_state in ("showing", "idle"):
            self._redraw_current_challenge()

    def is_practice_mode(self):
        return self.session_type_var.get() == "Practice"

    def get_selected_technique(self):
        selected = self.technique_var.get()
        if selected != "Auto Coach":
            return selected
        mode = self.mode_var.get()
        if mode in ("Numbers", "Phone", "Sequence"):
            return "Chunking"
        if mode == "Words":
            return "Story Link"
        return "Sound/Rhythm"

    def chunk_text(self, challenge, size=3):
        if self.mode_var.get() == "Words":
            items = challenge.split()
        else:
            items = [char for char in challenge if char not in (" ", ",")]
        if not items:
            return []
        return ["".join(items[index:index + size]) for index in range(0, len(items), size)]

    def build_mnemonic(self, challenge, mode, technique):
        chunks = self.chunk_text(challenge, 3)
        words = challenge.split()
        items = words if mode == "Words" else chunks
        if not items:
            return "Create one clear image, then recall it before typing."

        if technique == "Chunking":
            return f"Chunks: {' / '.join(chunks)}"
        if technique == "Memory Palace":
            placements = []
            for index, item in enumerate(items[:len(PALACE_LOCATIONS)]):
                placements.append(f"{PALACE_LOCATIONS[index]}={item}")
            return "Place them: " + ", ".join(placements)
        if technique == "Sound/Rhythm":
            return "Beat pattern: " + " | ".join(chunks)
        if technique == "Story Link":
            if mode == "Words":
                return "Story: " + " meets ".join(words) + "."
            return "Story: imagine " + " then ".join(chunks) + " appearing in order."
        return MNEMONIC_TIPS.get(mode, MNEMONIC_TIPS["Numbers"]).get(technique, "Use a small vivid image for each group.")

    def update_coach_panel(self, phase, correct=None, user_input=""):
        if not hasattr(self, "coach_title_label"):
            return
        technique = self.get_selected_technique()
        mode = self.mode_var.get()
        tip = MNEMONIC_TIPS.get(mode, MNEMONIC_TIPS["Numbers"]).get(technique, "")
        mnemonic = self.build_mnemonic(self.current_challenge, mode, technique) if self.current_challenge else "Start a practice round to get a coaching example."

        titles = {
            "idle": "Practice Coach",
            "memorize": f"Try {technique}",
            "recall": f"Recall with {technique}",
            "hint": "Coach Hint",
            "review": "Round Review",
        }
        self.coach_title_label.configure(text=titles.get(phase, "Practice Coach"))

        if phase == "memorize":
            instruction = f"Try this: {tip}"
            example = mnemonic
            review = "Look for the pattern now. You will recall it in the next step."
        elif phase == "recall":
            instruction = f"Use the {technique.lower()} method. Rebuild the groups before typing."
            example = tip
            review = "The answer is hidden, but your structure should still be clear."
        elif phase == "hint":
            instruction = f"Coach hint: {tip}"
            example = mnemonic
            review = "Use the structure, not just the visible characters."
        elif phase == "review":
            result_text = "Correct" if correct else "Not yet"
            instruction = f"{result_text}. Correct answer: {self.current_challenge}"
            example = f"Your answer: {user_input or '(blank)'}"
            review = f"Suggested mnemonic: {mnemonic}\nWhy it works: {tip}"
        else:
            instruction = "Practice mode teaches one recall technique at a time."
            example = "Choose a technique, or leave Auto Coach on."
            review = "Scores and lives are off here. Focus on building a method."

        self.coach_instruction_label.configure(text=instruction)
        self.coach_example_label.configure(text=example)
        self.coach_review_label.configure(text=review)

    def _cancel_timers(self):
        for after_id in (self.recall_after_id, self.tick_after_id):
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except ValueError:
                    pass
        self.recall_after_id = None
        self.tick_after_id = None

    def update_display_label(self, value):
        self.display_label.configure(text=f"Display time: {float(value):.1f}s")

    def update_recall_label(self, value):
        self.recall_label.configure(text=f"Recall time: {float(value):.1f}s")

    def _display_text(self, challenge):
        if self.mode_var.get() in ("Numbers", "Phone", "Alphanumeric"):
            return " ".join(challenge)
        return challenge

    def _grouped_display_chunks(self, challenge):
        compact = "".join(char for char in challenge if char not in (" ", ","))
        return [compact[index:index + 3] for index in range(0, len(compact), 3)]

    def _clear_challenge_display(self):
        for child in self.challenge_frame.winfo_children():
            child.destroy()
        self.challenge_widgets = []

    def _set_challenge_display(self, text, text_color=None, allow_assist=False):
        self._clear_challenge_display()
        grouped_modes = {"Numbers", "Phone", "Alphanumeric", "Sequence"}
        use_assist = allow_assist and self.assist_var.get() and self.mode_var.get() in grouped_modes and text not in ("?", "Game Over")
        color = text_color if text_color is not None else BODY_COLOR

        if use_assist:
            row = ctk.CTkFrame(self.challenge_frame, fg_color="transparent")
            row.grid(row=0, column=0)
            self.challenge_widgets.append(row)
            available_width = max(280, self.challenge_frame.winfo_width() or self.winfo_width() - 360)
            chunks_per_row = max(2, min(8, available_width // 110))
            for index, chunk in enumerate(self._grouped_display_chunks(text)):
                label = ctk.CTkLabel(
                    row,
                    text=chunk,
                    font=ctk.CTkFont(family="Consolas", size=34, weight="bold"),
                    text_color=CHALLENGE_COLORS[index % len(CHALLENGE_COLORS)],
                )
                label.grid(row=index // chunks_per_row, column=index % chunks_per_row, padx=(0, 12), pady=2)
                self.challenge_widgets.append(label)
            return

        self.challenge_label = ctk.CTkLabel(
            self.challenge_frame,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=34, weight="bold"),
            text_color=color,
            wraplength=max(260, min(720, self.challenge_frame.winfo_width() or 460)),
        )
        self.challenge_label.grid(row=0, column=0, sticky="ew")
        self.challenge_widgets.append(self.challenge_label)

    def _set_challenge_text_color(self, color):
        for widget in self.challenge_widgets:
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=color)

    def _redraw_current_challenge(self):
        if self.game_state == "showing" and self.current_challenge:
            self._set_challenge_display(self.current_challenge, allow_assist=True)
        elif self.game_state in ("idle", "game_over") and self.current_challenge:
            self._set_challenge_display(self.current_challenge, allow_assist=True)

    def start_game(self):
        if self.game_state in ("showing", "waiting"):
            return
        if not self.is_practice_mode() and self.lives <= 0:
            self._reset_run_state()

        self._cancel_timers()
        self._check_daily_streak(check_only=False)
        self.round_no += 1
        self.hints_used = 0
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.configure(state="disabled")
        self.result_label.configure(text="", text_color=BODY_COLOR)

        length = compute_length(self.level, self.difficulty_var.get())
        self.current_challenge = generate_challenge(self.mode_var.get(), length)
        self._set_challenge_display(self.current_challenge, allow_assist=True)

        self.start_button.configure(text="Check", state="disabled", command=self.check_number)
        self.hint_button.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        self.game_state = "showing"
        self.memorize_start_time = time.monotonic()
        self.recall_progress.set(1)
        self.countdown_label.configure(text=f"{self.display_slider.get():.1f}s")
        if self.timer_var.get():
            self.recall_after_id = self.after(int(self.display_slider.get() * 1000), self.hide_challenge)
        else:
            self.start_button.configure(text="Ready", state="normal", command=self.hide_challenge)
        if self.is_practice_mode():
            self.update_coach_panel("memorize")
            self._tick_memorize()
        self._refresh_hud()

    def hide_challenge(self):
        self.recall_after_id = None
        if hasattr(self, 'memorize_start_time') and self.memorize_start_time:
            elapsed = time.monotonic() - self.memorize_start_time
            self.practice_total_memorize_time += elapsed
            self.memorize_start_time = None
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self._set_challenge_display("?", text_color=BODY_COLOR)
        self.entry.focus()
        self.start_button.configure(text="Check", state="normal", command=self.check_number)
        self.hint_button.configure(text="Coach Hint" if self.is_practice_mode() else "Hint", state="normal")
        self.skip_button.configure(state="normal")
        self.game_state = "waiting"
        if self.timer_var.get():
            self.recall_deadline = time.monotonic() + self.recall_slider.get()
            self._tick_recall()
        else:
            self.recall_deadline = None
            self.countdown_label.configure(text="Inf")
        if self.is_practice_mode():
            self.update_coach_panel("recall")
        self._tick_recall()

    def _tick_recall(self):
        if self.game_state != "waiting" or self.recall_deadline is None or not self.timer_var.get():
            return
        recall_seconds = self.recall_slider.get()
        time_left = max(0, self.recall_deadline - time.monotonic())
        self.recall_progress.set(time_left / recall_seconds if recall_seconds else 0)
        self.countdown_label.configure(text=f"{time_left:.1f}s")
        if time_left <= 0:
            self.tick_after_id = None
            self.check_number(timed_out=True)
            return
        self.tick_after_id = self.after(100, self._tick_recall)

    def _tick_memorize(self):
        if self.game_state != "showing" or not hasattr(self, 'memorize_start_time') or not self.memorize_start_time:
            return
        elapsed = time.monotonic() - self.memorize_start_time
        self.countdown_label.configure(text=f"{elapsed:.1f}s")
        self.tick_after_id = self.after(100, self._tick_memorize)

    def show_hint(self):
        if self.game_state != "waiting" or self.hints_used >= 2:
            return
        self.hints_used += 1
        visible_chars = max(1, int(len(self.current_challenge.replace(" ", "").replace(",", "")) * 0.3))
        candidates = [index for index, char in enumerate(self.current_challenge) if char not in (" ", ",")]
        shown = set(random.sample(candidates, min(visible_chars * self.hints_used, len(candidates))))
        masked = []
        for index, char in enumerate(self.current_challenge):
            if char in (" ", ","):
                masked.append(char)
            else:
                masked.append(char if index in shown else "*")
        self._set_challenge_display("".join(masked), allow_assist=True)
        if self.is_practice_mode():
            self.result_label.configure(text=f"Coach hint used ({self.hints_used}/2).", text_color="#f0ad4e")
            self.update_coach_panel("hint")
        else:
            self.result_label.configure(text=f"Hint used ({self.hints_used}/2). Score penalty applied.", text_color="#f0ad4e")
        if self.hints_used >= 2:
            self.hint_button.configure(state="disabled")

    def skip_round(self):
        if self.game_state == "waiting":
            self.check_number(force_wrong=True)

    def check_number(self, timed_out=False, force_wrong=False):
        if self.game_state != "waiting":
            return
        self._cancel_timers()
        user_input = self.entry.get().strip()
        answer = self.current_challenge.strip()
        time_left = max(0, self.recall_deadline - time.monotonic()) if self.recall_deadline else 0
        self.entry.configure(state="disabled")
        self.hint_button.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        self.game_state = "idle"

        mode = self.mode_var.get()
        correct = not force_wrong and normalize_compare(mode, user_input, answer)
        if correct:
            self.apply_correct(time_left)
        else:
            message = "Time's up" if timed_out else "Skipped" if force_wrong else "Incorrect"
            self.apply_wrong(f"{message}. It was {answer}")

        self.recall_progress.set(0)
        self.countdown_label.configure(text="0.0s")
        if self.is_practice_mode() or self.lives > 0:
            self.start_button.configure(text="Start", state="normal", command=self.start_game)
        if self.is_practice_mode():
            self.update_coach_panel("review", correct=correct, user_input=user_input)
        else:
            self.check_achievements()
        self._refresh_hud()

    def apply_correct(self, time_left):
        length = len(self.current_challenge.replace(" ", "").replace(",", ""))
        self.correct_count += 1
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        if self.is_practice_mode():
            self.practice_attempts += 1
            self.practice_correct += 1
            self.practice_streak += 1
            self.practice_best_streak = max(self.practice_best_streak, self.practice_streak)
            self._track_practice_technique()
            self.result_label.configure(text="Correct. Nice method work.", text_color="#33cc66")
        else:
            gain = compute_score_gain(length, time_left, self.hints_used, self.streak, self.difficulty_var.get(), self.recall_slider.get())
            self.score += gain
            self.combo_multiplier = 1 + (self.streak // 3)
            previous_level = self.level
            self.level = 1 + (self.correct_count // 3)
            if self.level > previous_level:
                self.result_label.configure(text=f"LEVEL UP! Correct +{gain}", text_color="#33cc66")
            else:
                self.result_label.configure(text=f"Correct! +{gain}", text_color="#33cc66")
        self._set_challenge_display(self.current_challenge, text_color="#33cc66", allow_assist=False)
        self.after(400, lambda: self._set_challenge_text_color(BODY_COLOR))
        
        # Update quest
        quest = self.save_data.get("daily_quest", {})
        if not quest.get("completed") and quest.get("type") == self.mode_var.get():
            quest["current"] += 1
            if quest["current"] >= quest["target"]:
                quest["completed"] = True
                current_text = self.result_label.cget("text")
                self.result_label.configure(text=f"{current_text} | Daily Quest Completed!")
            save_save(self.save_data, self.username)

    def apply_wrong(self, message):
        self.wrong_count += 1
        self.streak = 0
        if self.is_practice_mode():
            self.practice_attempts += 1
            self.practice_streak = 0
            self._track_practice_technique()
            chunks = " / ".join(self.chunk_text(self.current_challenge, 3))
            self.result_label.configure(text=f"Not yet. Try chunking this as {chunks}.", text_color="#f0ad4e")
        else:
            self.lives -= 1
            self.combo_multiplier = 1
            self.result_label.configure(text=message, text_color="#ff5555")
        self._set_challenge_display(self.current_challenge, text_color="#ff5555", allow_assist=False)
        self.after(400, lambda: self._set_challenge_text_color(BODY_COLOR))
        if not self.is_practice_mode() and self.lives <= 0:
            self.game_over()

    def check_achievements(self):
        unlocked = set(self.save_data.get("achievements", []))
        newly_unlocked = []
        for achievement in ACHIEVEMENTS:
            if achievement["id"] in unlocked:
                continue
            predicate = achievement["predicate"]
            earned = (
                (predicate == "correct>=1" and self.correct_count >= 1)
                or (predicate == "streak>=5" and self.best_streak >= 5)
                or (predicate == "score>=1000" and self.score >= 1000)
                or (predicate == "level>=10" and self.level >= 10)
                or (
                    predicate == "perfect_round_insane"
                    and self.difficulty_var.get() == "Insane"
                    and self.hints_used == 0
                    and self.streak > 0
                )
            )
            if earned:
                unlocked.add(achievement["id"])
                newly_unlocked.append(achievement["name"])
        if newly_unlocked:
            self.save_data["achievements"] = sorted(unlocked)
            save_save(self.save_data, self.username)
            self.achievement_message = f"Achievement unlocked: {', '.join(newly_unlocked)}"
            current = self.result_label.cget("text")
            self.result_label.configure(text=f"{current} | {self.achievement_message}")

    def _track_practice_technique(self):
        technique = self.get_selected_technique()
        self.practice_techniques_used[technique] = self.practice_techniques_used.get(technique, 0) + 1

    def _flush_stats(self):
        if self.is_practice_mode():
            self._flush_practice_stats()
            return
        if self.stats_flushed or self.round_no == 0:
            return
        stats = self.save_data.setdefault("stats", default_save()["stats"])
        stats["games_played"] = stats.get("games_played", 0) + 1
        stats["correct"] = stats.get("correct", 0) + self.correct_count
        stats["wrong"] = stats.get("wrong", 0) + self.wrong_count
        stats["best_streak"] = max(stats.get("best_streak", 0), self.best_streak)
        stats["best_level"] = max(stats.get("best_level", 0), self.level)
        stats["total_score"] = stats.get("total_score", 0) + self.score
        save_save(self.save_data, self.username)
        self.stats_flushed = True

    def _flush_practice_stats(self):
        if self.stats_flushed or self.practice_attempts == 0:
            return
        stats = self.save_data.setdefault("practice_stats", default_save()["practice_stats"])
        stats["attempts"] = stats.get("attempts", 0) + self.practice_attempts
        stats["correct"] = stats.get("correct", 0) + self.practice_correct
        stats["best_streak"] = max(stats.get("best_streak", 0), self.practice_best_streak)
        stats["total_memorize_time"] = stats.get("total_memorize_time", 0.0) + self.practice_total_memorize_time
        techniques = stats.setdefault("techniques_used", {})
        for technique, count in self.practice_techniques_used.items():
            techniques[technique] = techniques.get(technique, 0) + count
        save_save(self.save_data, self.username)
        self.stats_flushed = True

    def _score_qualifies_for_leaderboard(self):
        if self.is_practice_mode() or self.score <= 0:
            return False
        high_scores = self.save_data.get("high_scores", [])
        if len(high_scores) < 5:
            return True
        return self.score > min(item.get("score", 0) for item in high_scores)

    def _record_high_score(self, name="Player"):
        if self.score_recorded or not self._score_qualifies_for_leaderboard():
            return
        entry = {
            "name": name[:16] or "Player",
            "score": self.score,
            "level": self.level,
            "mode": self.mode_var.get(),
            "difficulty": self.difficulty_var.get(),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        }
        scores = self.save_data.setdefault("high_scores", [])
        scores.append(entry)
        self.save_data["high_scores"] = sorted(scores, key=lambda item: item.get("score", 0), reverse=True)[:5]
        save_save(self.save_data, self.username)
        self.score_recorded = True

    def game_over(self):
        self._flush_stats()
        dialog = ctk.CTkInputDialog(text="Game over! Enter your name for the leaderboard:", title="Game Over")
        name = dialog.get_input() or "Player"
        self._record_high_score(name)
        self._set_challenge_display("Game Over", text_color="#ff5555")
        self.result_label.configure(text=f"Final score: {self.score}", text_color="#ff5555")
        self.start_button.configure(text="New Game", state="normal", command=self.reset_game)
        self.game_state = "game_over"
        self._refresh_hud()

    def reset_game(self):
        self._cancel_timers()
        self._record_high_score("Auto Save")
        self._flush_stats()
        self._reset_run_state()
        self.current_challenge = ""
        self.game_state = "idle"
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.configure(state="disabled")
        self._set_challenge_display("Click Start to begin", text_color=BODY_COLOR)
        self.result_label.configure(text="", text_color=BODY_COLOR)
        self.recall_progress.set(0)
        self.countdown_label.configure(text="0.0s")
        self.start_button.configure(text="Start", state="normal", command=self.start_game)
        self.hint_button.configure(text="Coach Hint" if self.is_practice_mode() else "Hint", state="disabled")
        self.skip_button.configure(state="disabled")
        self.save_data = load_save(self.username)
        if self.is_practice_mode():
            self.update_coach_panel("idle")
        self._refresh_hud()

    def _on_session_change(self, value):
        if value == "Practice":
            self.assist_var.set(True)
            self.timer_var.set(False)
            self.display_slider.set(max(self.display_slider.get(), 5.0))
            self.recall_slider.set(max(self.recall_slider.get(), 15.0))
            self.update_display_label(self.display_slider.get())
            self.update_recall_label(self.recall_slider.get())
        else:
            config = self._difficulty_config()
            self.display_slider.set(config["display"])
            self.recall_slider.set(config["recall"])
            self.update_display_label(config["display"])
            self.update_recall_label(config["recall"])
        self.reset_game()

    def _on_mode_change(self, _value):
        self.reset_game()

    def _on_difficulty_change(self, _value):
        config = self._difficulty_config()
        display_time = max(config["display"], 5.0) if self.is_practice_mode() else config["display"]
        recall_time = max(config["recall"], 15.0) if self.is_practice_mode() else config["recall"]
        self.display_slider.set(display_time)
        self.recall_slider.set(recall_time)
        self.update_display_label(display_time)
        self.update_recall_label(recall_time)
        self.reset_game()

    def _on_theme_change(self, value):
        ctk.set_appearance_mode(value)

    def _on_technique_change(self, _value):
        if self.is_practice_mode():
            phase = "memorize" if self.game_state == "showing" else "recall" if self.game_state == "waiting" else "idle"
            self.update_coach_panel(phase)

    def _refresh_hud(self):
        if self.is_practice_mode():
            self.game_sidebar.grid_remove()
            self.coach_sidebar.grid(row=0, column=0, sticky="nsew")
            persisted = self.save_data.get("practice_stats", {})
            attempts = self.practice_attempts
            correct = self.practice_correct
            total_attempts = persisted.get("attempts", 0) + attempts
            total_correct = persisted.get("correct", 0) + correct
            accuracy = int((total_correct / total_attempts) * 100) if total_attempts else 0
            best = max(persisted.get("best_streak", 0), self.practice_best_streak)
            total_time = persisted.get("total_memorize_time", 0.0) + self.practice_total_memorize_time
            avg_time = total_time / total_attempts if total_attempts else 0.0
            
            img_practice = self._get_icon_image("🎮")
            if img_practice:
                self.top_high_score_label.configure(text=f" Practice: {correct}/{attempts}", image=img_practice, compound="left")
            else:
                self.top_high_score_label.configure(text=f"Practice 🎮: {correct}/{attempts}", image="")
                
            img_streak = self._get_icon_image("🔥")
            if img_streak:
                self.top_streak_label.configure(text=f" Daily Streak: {self.save_data.get('daily_streak', 0)}", image=img_streak, compound="left")
            else:
                self.top_streak_label.configure(text=f"Daily Streak 🔥: {self.save_data.get('daily_streak', 0)}", image="")

            # Attempts
            img_attempts = self._get_icon_image("🎯")
            if img_attempts:
                self.practice_attempts_label.configure(text=f" Practice attempts: {total_attempts}", image=img_attempts, compound="left")
            else:
                self.practice_attempts_label.configure(text=f"Practice attempts 🎯: {total_attempts}", image="")

            # Correct
            img_correct = self._get_icon_image("✅")
            if img_correct:
                self.practice_correct_label.configure(text=f" Practice correct: {total_correct}", image=img_correct, compound="left")
            else:
                self.practice_correct_label.configure(text=f"Practice correct ✅: {total_correct}", image="")

            # Accuracy
            img_accuracy = self._get_icon_image("📊")
            if img_accuracy:
                self.practice_accuracy_label.configure(text=f" Practice accuracy: {accuracy}%", image=img_accuracy, compound="left")
            else:
                self.practice_accuracy_label.configure(text=f"Practice accuracy 📊: {accuracy}%", image="")

            # Best Streak
            img_best = self._get_icon_image("🔥")
            if img_best:
                self.practice_best_streak_label.configure(text=f" Best practice streak: {best}", image=img_best, compound="left")
            else:
                self.practice_best_streak_label.configure(text=f"Best practice streak 🔥: {best}", image="")

            # Average Time
            img_time = self._get_icon_image("⏱")
            if img_time:
                self.practice_time_label.configure(text=f" Avg memorize time: {avg_time:.1f}s", image=img_time, compound="left")
            else:
                self.practice_time_label.configure(text=f"Avg memorize time ⏱: {avg_time:.1f}s", image="")
            return

        self.coach_sidebar.grid_remove()
        self.game_sidebar.grid(row=0, column=0, sticky="nsew")
        high_scores = sorted(self.save_data.get("high_scores", []), key=lambda item: item.get("score", 0), reverse=True)[:5]
        best_score = max([self.score] + [item.get("score", 0) for item in high_scores])
        total_rounds = self.correct_count + self.wrong_count
        accuracy = int((self.correct_count / total_rounds) * 100) if total_rounds else 0
        hearts = " ".join("❤️" for _ in range(max(0, self.lives))) or "None 💔"

        # Update quest display
        for child in self.quest_frame.winfo_children():
            child.destroy()
        quest = self.save_data.get("daily_quest", {})
        quest_icon = "🎉" if quest.get("completed") else "📜"
        quest_text = f"Daily Quest: {quest.get('type')} {quest.get('current')}/{quest.get('target')}"
        if quest.get("completed"):
            quest_text += " (Done)"
            
        img_quest = self._get_icon_image(quest_icon)
        if img_quest:
            lbl = ctk.CTkLabel(self.quest_frame, text=" " + quest_text, font=ctk.CTkFont(size=14, weight="bold"), text_color=SUBHEADER_COLOR, image=img_quest, compound="left")
        else:
            fallback_text = f"Daily Quest {quest_icon}: {quest.get('type')} {quest.get('current')}/{quest.get('target')}"
            if quest.get("completed"):
                fallback_text += " (Done 🎉)"
            lbl = ctk.CTkLabel(self.quest_frame, text=fallback_text, font=ctk.CTkFont(size=14, weight="bold"), text_color=SUBHEADER_COLOR)
        lbl.grid(row=0, column=0, sticky="w")

        # Top bars
        img_high = self._get_icon_image("🏆")
        if img_high:
            self.top_high_score_label.configure(text=f" High Score: {best_score}", image=img_high, compound="left")
        else:
            self.top_high_score_label.configure(text=f"High Score 🏆: {best_score}", image="")

        img_streak_top = self._get_icon_image("🔥")
        if img_streak_top:
            self.top_streak_label.configure(text=f" Daily Streak: {self.save_data.get('daily_streak', 0)}", image=img_streak_top, compound="left")
        else:
            self.top_streak_label.configure(text=f"Daily Streak 🔥: {self.save_data.get('daily_streak', 0)}", image="")

        # HUD Side Panel
        img_score = self._get_icon_image("🎯")
        if img_score:
            self.score_label.configure(text=f" Score: {self.score}", image=img_score, compound="left")
        else:
            self.score_label.configure(text=f"Score 🎯: {self.score}", image="")

        img_acct = self._get_icon_image("⭐")
        if img_acct:
            self.account_level_label.configure(text=f" Account Level: {self.account_level} / 100", image=img_acct, compound="left")
        else:
            self.account_level_label.configure(text=f"Account Level ⭐: {self.account_level} / 100", image="")

        img_lvl = self._get_icon_image("📈")
        if img_lvl:
            self.level_label.configure(text=f" Session Level: {self.level}", image=img_lvl, compound="left")
        else:
            self.level_label.configure(text=f"Session Level 📈: {self.level}", image="")

        img_hearts = self._get_icon_image("💖")
        if img_hearts:
            self.lives_label.configure(text=f" Lives: {hearts}", image=img_hearts, compound="left")
        else:
            self.lives_label.configure(text=f"Lives 💖: {hearts}", image="")

        img_strk = self._get_icon_image("🔥")
        if img_strk:
            self.streak_label.configure(text=f" Streak: {self.streak}   x{self.combo_multiplier}", image=img_strk, compound="left")
        else:
            self.streak_label.configure(text=f"Streak 🔥: {self.streak}   x{self.combo_multiplier}", image="")

        img_rnd = self._get_icon_image("🔄")
        if img_rnd:
            self.round_label.configure(text=f" Round: {self.round_no}", image=img_rnd, compound="left")
        else:
            self.round_label.configure(text=f"Round 🔄: {self.round_no}", image="")

        img_acc = self._get_icon_image("📊")
        if img_acc:
            self.accuracy_label.configure(text=f" Accuracy: {accuracy}%", image=img_acc, compound="left")
        else:
            self.accuracy_label.configure(text=f"Accuracy 📊: {accuracy}%", image="")

        img_bst = self._get_icon_image("⚡")
        if img_bst:
            self.best_label.configure(text=f" Best Streak: {self.best_streak}", image=img_bst, compound="left")
        else:
            self.best_label.configure(text=f"Best Streak ⚡: {self.best_streak}", image="")

        for child in self.high_scores_frame.winfo_children():
            child.destroy()
        if not high_scores:
            ctk.CTkLabel(self.high_scores_frame, text="No scores yet", anchor="w").grid(row=0, column=0, sticky="w")
        for index, item in enumerate(high_scores):
            text = f"{index + 1}. {item.get('name', 'Player')} {item.get('score', 0)} L{item.get('level', 1)} {item.get('difficulty', '')}"
            ctk.CTkLabel(self.high_scores_frame, text=text, anchor="w").grid(row=index, column=0, sticky="w")

    def show_achievements(self):
        unlocked = set(self.save_data.get("achievements", []))
        AchievementsWindow(self, unlocked, self._get_icon_image)

    def _on_close(self):
        self._cancel_timers()
        self._save_user_settings()
        self._record_high_score("Auto Save")
        self._flush_stats()
        self.destroy()

    def capture_screenshot(self, event=None):
        try:
            import os
            import time
            from PIL import ImageGrab
            
            x = self.winfo_rootx()
            y = self.winfo_rooty()
            width = self.winfo_width()
            height = self.winfo_height()
            
            base_dir = os.path.dirname(__file__)
            screenshots_dir = os.path.join(base_dir, "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            filename = os.path.join(screenshots_dir, f"screenshot_{int(time.time())}.png")
            img = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            img.save(filename)
            
            if hasattr(self, "result_label"):
                current_text = self.result_label.cget("text")
                self.result_label.configure(text="📸 Screenshot saved successfully!", text_color="#33cc66")
                self.after(2000, lambda: self.result_label.configure(text=current_text, text_color=BODY_COLOR))
            print(f"Screenshot saved to: {filename}")
        except Exception as e:
            print(f"Failed to capture screenshot: {e}")


if __name__ == "__main__":
    app = MemoryApp()
    app.mainloop()
