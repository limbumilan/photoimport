# detail_gui.py
import customtkinter as ctk

class DetailWindow(ctk.CTkToplevel):
    def __init__(self, parent, item_name):
        super().__init__(parent)
        self.title(f"Details - {item_name}")
        self.geometry("400x300")
        self.configure(fg_color="#f0f0f0")

        ctk.CTkLabel(self, text=f"Details of {item_name}", font=("Arial", 14)).pack(pady=20)
        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=10)
