import customtkinter as ctk
from PIL import Image
import os
from pathlib import Path

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Demo GUI App")
        self.geometry("800x600")
        self.configure(fg_color="#e8e8e8")

        self._image_references = []
        Path("assets").mkdir(exist_ok=True)

        self.create_widgets()

    def create_widgets(self):
        # ------------------------------
        # Frame for tab buttons (top-left)
        # ------------------------------
        self.tab_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_buttons_frame.pack(anchor="nw", padx=10, pady=10)

        # Tab buttons
        self.btn_login = ctk.CTkButton(self.tab_buttons_frame, text="Login", command=lambda: self.show_tab("login"))
        self.btn_list1 = ctk.CTkButton(self.tab_buttons_frame, text="List 1", command=lambda: self.show_tab("list1"))
        self.btn_list2 = ctk.CTkButton(self.tab_buttons_frame, text="List 2", command=lambda: self.show_tab("list2"))

        self.btn_login.grid(row=0, column=0, padx=5)
        self.btn_list1.grid(row=0, column=1, padx=5)
        self.btn_list2.grid(row=0, column=2, padx=5)

        # ------------------------------
        # Frames for tab content
        # ------------------------------
        self.tab_frames = {}

        self.tab_frames["login"] = ctk.CTkFrame(self, width=780, height=500)
        self.tab_frames["login"].pack(padx=10, pady=(0,10), fill="both", expand=True)

        self.tab_frames["list1"] = ctk.CTkFrame(self, width=780, height=500)
        self.tab_frames["list1"].pack_forget()

        self.tab_frames["list2"] = ctk.CTkFrame(self, width=780, height=500)
        self.tab_frames["list2"].pack_forget()

        # Populate tab contents
        self.create_login_tab(self.tab_frames["login"])
        self.create_list_tab(self.tab_frames["list1"], ["Item 1", "Item 2", "Item 3"])
        self.create_list_tab(self.tab_frames["list2"], ["Entry A", "Entry B", "Entry C"])

    # ------------------------------
    # Show selected tab
    # ------------------------------
    def show_tab(self, tab_name):
        for name, frame in self.tab_frames.items():
            if name == tab_name:
                frame.pack(padx=10, pady=(0,10), fill="both", expand=True)
            else:
                frame.pack_forget()

    # ------------------------------
    # Login tab with logo
    # ------------------------------
    def create_login_tab(self, parent):
        logo_img = self.load_image("assets/placeholder.png", (120,120))
        self.logo_img = logo_img
        ctk.CTkLabel(parent, image=self.logo_img, text="").pack(pady=20)

        ctk.CTkLabel(parent, text="Password:", font=("Arial",12)).pack(pady=(10,2), anchor="w", padx=20)
        self.password_entry = ctk.CTkEntry(parent, show="*")
        self.password_entry.pack(pady=(0,10), padx=20, fill="x")

        ctk.CTkButton(parent, text="Login", command=self.login_action).pack(pady=5)

    # ------------------------------
    # List tabs
    # ------------------------------
    def create_list_tab(self, parent, items):
        scroll_frame = ctk.CTkScrollableFrame(parent, width=300, height=400)
        scroll_frame.pack(padx=20, pady=20, fill="both", expand=True)
        for item in items:
            ctk.CTkLabel(scroll_frame, text=item, anchor="w", font=("Arial",12)).pack(fill="x", padx=5, pady=2)

    # ------------------------------
    # Dummy login action
    # ------------------------------
    def login_action(self):
        password = self.password_entry.get()
        msg = f"Logged in with password: {password}" if password else "Please enter a password"
        ctk.CTkLabel(self.tab_frames["login"], text=msg).pack(pady=10)

    # ------------------------------
    # Image loader
    # ------------------------------
    def load_image(self, path, size):
        try:
            if os.path.exists(path):
                img = Image.open(path).resize(size, Image.LANCZOS)
            else:
                img = Image.new("RGB", size, color="#3B82F6")
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self._image_references.append(ctk_img)
            return ctk_img
        except:
            img = Image.new("RGB", size, color="#FF5555")
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self._image_references.append(ctk_img)
            return ctk_img

if __name__ == "__main__":
    app = App()
    app.mainloop()
