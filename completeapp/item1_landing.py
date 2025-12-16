from baselanding import BaseLanding
import customtkinter as ctk

class Item1Landing(BaseLanding):
    def __init__(self, parent, on_back):
        super().__init__(parent, on_back)
        # Page title
        ctk.CTkLabel(
            self.body,
            text="Item 1 Details",
            font=("Arial", 18, "bold"),
            text_color="#1E3A8A"
        ).pack(pady=50)
        # Add your page content below
