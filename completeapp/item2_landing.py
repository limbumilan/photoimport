from baselanding import BaseLanding
import customtkinter as ctk


class Item2Landing(BaseLanding):
    def __init__(self, parent, on_back, **kwargs):
        super().__init__(parent, on_back, **kwargs)

        # Page title inside the shared body container
        ctk.CTkLabel(
            self.body,
            text="Item 2 Details",
            font=("Arial", 18, "bold"),
            text_color="#1E3A8A"
        ).pack(pady=50)

        # Example content
        ctk.CTkLabel(self.body, text="Details or controls for Item 2 go here.").pack(pady=10)
