import customtkinter as ctk
from memory_data import ACHIEVEMENTS, HEADER_COLOR


class AchievementsWindow(ctk.CTkToplevel):
    def __init__(self, parent, unlocked_set, get_icon_image_callback):
        super().__init__(parent)
        self.parent = parent
        self.unlocked = unlocked_set
        self.get_icon_image = get_icon_image_callback
        
        self.title("Achievements 🏆")
        self.geometry("450x400")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        ctk.CTkLabel(self, text="Achievements 🏆", font=ctk.CTkFont(size=20, weight="bold"), text_color=HEADER_COLOR).pack(padx=20, pady=(20, 10))
        
        scroll_frame = ctk.CTkScrollableFrame(self, width=400, height=280)
        scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        icon_colors = {
            "first_correct": "#f59e0b",
            "streak_5": "#f97316",
            "score_1000": "#38bdf8",
            "level_10": "#a78bfa",
            "insane_perfect": "#34d399",
        }
        for achievement in ACHIEVEMENTS:
            is_unlocked = achievement["id"] in self.unlocked
            bg_color = "transparent"
            fg_color = "#33cc66" if is_unlocked else "gray"
            icon_color = icon_colors.get(achievement["id"], "gray")
            
            card = ctk.CTkFrame(scroll_frame, fg_color=bg_color)
            card.pack(fill="x", pady=5, padx=5)
            
            # Icon Label
            icon_char = achievement.get("icon", "🔒") if is_unlocked else "🔒"
            img = self.get_icon_image(icon_char, size=(32, 32))
            if img:
                ctk.CTkLabel(card, text="", image=img).pack(side="left", padx=10)
            else:
                ctk.CTkLabel(card, text=icon_char, font=ctk.CTkFont(size=24), text_color=icon_color).pack(side="left", padx=10)
            
            # Text container
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True)
            
            name_lbl = ctk.CTkLabel(info_frame, text=achievement["name"], font=ctk.CTkFont(size=14, weight="bold"), text_color=fg_color, anchor="w")
            name_lbl.pack(fill="x")
            
            desc_lbl = ctk.CTkLabel(info_frame, text=achievement["description"], font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
            desc_lbl.pack(fill="x")
            
            status_text = "Unlocked ✅" if is_unlocked else "Locked"
            status_lbl = ctk.CTkLabel(card, text=status_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=fg_color)
            status_lbl.pack(side="right", padx=10)
            
        close_btn = ctk.CTkButton(self, text="Close", command=self.destroy)
        close_btn.pack(pady=(10, 20))
