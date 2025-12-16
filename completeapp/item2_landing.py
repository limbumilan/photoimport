import customtkinter as ctk

class Item2Landing(ctk.CTkFrame):
    def __init__(self, parent, on_back, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_back = on_back

        # Title
        ctk.CTkLabel(self, text="Item 1 Landing Page", font=("Arial", 18, "bold")).pack(pady=20)

        # Example content
        ctk.CTkLabel(self, text="Details or controls for Item 1 go here.").pack(pady=10)

        # Back button
        ctk.CTkButton(self, text="Back to Reports", command=self.on_back).pack(pady=20)
