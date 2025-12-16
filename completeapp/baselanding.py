import customtkinter as ctk

class BaseLanding(ctk.CTkFrame):
    """Base class for full-page landing pages with Back button and smooth display."""

    def __init__(self, parent, on_back, **kwargs):
        super().__init__(parent, fg_color="#FFFFFF", **kwargs)
        self.parent = parent
        self.on_back = on_back

        # Main content container
        self.body = ctk.CTkFrame(self, fg_color="#FFFFFF")
        self.body.pack(fill="both", expand=True)

        # Footer to hold the Back button at the bottom
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom")

        self.back_btn = ctk.CTkButton(
            self.footer,
            text="← Back",
            width=140,
            height=36,
            fg_color="#1E3A8A",
            hover_color="#274690",
            text_color="white",
            command=self.go_back
        )
        self.back_btn.pack(pady=12)

    def go_back(self):
        """Call the callback to return to main content."""
        if self.on_back:
            self.on_back()
