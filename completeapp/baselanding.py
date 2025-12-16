import customtkinter as ctk

class BaseLanding(ctk.CTkFrame):
    """Base class for full-page landing pages with Back button and smooth display."""

    def __init__(self, parent, on_back, **kwargs):
        super().__init__(parent, fg_color="#FFFFFF", **kwargs)
        self.parent = parent
        self.on_back = on_back

        # Container frame
        self.body = ctk.CTkFrame(self, fg_color="#FFFFFF")
        self.body.pack(fill="both", expand=True)

        # Back button at top-left
        self.back_btn = ctk.CTkButton(
            self.body,
            text="← Back",
            width=100,
            height=35,
            fg_color="#1E3A8A",
            hover_color="#274690",
            text_color="white",
            command=self.go_back
        )
        self.back_btn.pack(anchor="nw", padx=15, pady=15)

    def go_back(self):
        """Call the callback to return to main content."""
        if self.on_back:
            self.on_back()
