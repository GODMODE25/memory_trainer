import os
import customtkinter as ctk
from memory_utils import get_save_path, load_save, save_save, save_config, default_save


class AuthWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_success_callback):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success_callback
        
        self.title("Login / Register")
        self.geometry("350x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        # Hide parent during authentication
        self.parent.withdraw()
        
        # Window closing handler (exits app if auth screen is closed)
        self.protocol("WM_DELETE_WINDOW", self.parent.quit)
        
        ctk.CTkLabel(self, text="Memory Trainer Quest", font=ctk.CTkFont(family="Impact", size=24)).pack(pady=20)
        
        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username", width=200)
        self.username_entry.pack(pady=10)
        self.username_entry.bind("<Return>", lambda _event: self.attempt_login())
        
        self.error_label = ctk.CTkLabel(self, text="", text_color="#ff5555")
        self.error_label.pack(pady=5)
        
        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self, text="Remember me", variable=self.remember_var).pack(pady=5)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        self.login_button = ctk.CTkButton(btn_frame, text="Login", command=self.attempt_login, width=90)
        self.login_button.pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Register", command=self.attempt_register, width=90).pack(side="left", padx=5)

        self.after(100, self.username_entry.focus_set)
        
    def attempt_login(self):
        user = self.username_entry.get().strip()
        if not user:
            self.error_label.configure(text="Username cannot be empty")
            return
        filename = get_save_path(user)
        if os.path.exists(filename):
            self.complete_login(user)
        else:
            self.error_label.configure(text="User not found. Please register.")
            
    def attempt_register(self):
        user = self.username_entry.get().strip()
        if not user:
            self.error_label.configure(text="Username cannot be empty")
            return
        filename = get_save_path(user)
        if os.path.exists(filename):
            self.error_label.configure(text="Username taken. Choose another.")
        else:
            save_save(default_save(), user)
            self.complete_login(user)
            
    def complete_login(self, user):
        save_data = load_save(user)
        if self.remember_var.get():
            save_config({"remembered_user": user})
        else:
            save_config({})
        
        # Reset window protocol so closing doesn't quit the whole app now
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.destroy()
        
        # Restore parent window
        self.parent.deiconify()
        self.on_success(user, save_data)
