import customtkinter as ctk
from PIL import Image, ImageDraw
from pathlib import Path
from item1_landing import Item1Landing
from item2_landing import Item2Landing
from extractionfinal import LicenseExportLanding  # your export page

# -------------------------------
# MAIN APP
# -------------------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Theme
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Department of Transport Management")
        self.geometry("900x600")
        self.configure(fg_color="#F0F4FF")

        self.assets_dir = Path(__file__).parent / "assets"
        self.assets_dir.mkdir(exist_ok=True)

        self.menu_visible = True
        self.animation_speed = 12
        self._image_refs = []
        self.current_landing = None  # currently displayed landing page

        self.create_frames()
        self.show_login()

    # -------------------------------
    # FRAMES
    # -------------------------------
    def create_frames(self):
        self.login_frame = ctk.CTkFrame(self, fg_color="#F0F4FF")
        self.main_frame = ctk.CTkFrame(self, fg_color="#F0F4FF")

        self.create_login_ui(self.login_frame)
        self.create_main_ui(self.main_frame)

    def show_login(self):
        if self.current_landing:
            self.current_landing.destroy()
            self.current_landing = None
        self.main_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)

    def show_main(self):
        self.login_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    # -------------------------------
    # LOGIN
    # -------------------------------
    def create_login_ui(self, parent):
        logo = self.load_logo((160, 120))
        ctk.CTkLabel(parent, image=logo, text="").pack(pady=30)

        ctk.CTkLabel(
            parent,
            text="Department of Transport Management",
            font=("Arial", 16, "bold"),
            text_color="#1E3A8A"
        ).pack(pady=10)

        self.password = ctk.CTkEntry(parent, show="*", width=200)
        self.password.pack(pady=10)

        ctk.CTkButton(
            parent,
            text="Login",
            width=150,
            command=self.login
        ).pack(pady=10)

    def login(self):
        if self.password.get():
            self.show_main()

    # -------------------------------
    # MAIN UI
    # -------------------------------
    def create_main_ui(self, parent):
        # Left menu
        self.left_menu = ctk.CTkFrame(parent, width=180, fg_color="#1E3A8A")
        self.left_menu.pack(side="left", fill="y")
        self.left_menu.pack_propagate(False)

        # Hamburger
        self.toggle_btn = ctk.CTkButton(
            self.left_menu,
            text="☰",
            width=40,
            height=40,
            fg_color="transparent",
            hover_color="#274690",
            font=("Arial", 22, "bold"),
            command=self.toggle_menu
        )
        self.toggle_btn.pack(anchor="e", padx=10, pady=10)

        # Tabs
        self.tabs_frame = ctk.CTkFrame(self.left_menu, fg_color="#1E3A8A")
        self.tabs_frame.pack(fill="y", expand=True)

        self.tab_buttons = {}
        for tab in ["Reports", "Export", "Logout"]:
            btn = ctk.CTkButton(
                self.tabs_frame,
                text=tab,
                height=42,
                fg_color="transparent",
                text_color="white",
                anchor="w",
                command=lambda t=tab: self.tab_click(t)
            )
            btn.pack(fill="x", padx=10, pady=4)
            self.tab_buttons[tab] = btn

        # Content area
        self.content = ctk.CTkFrame(parent, fg_color="#FFFFFF")
        self.content.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Initialize tabs frames
        self.tabs = {
            "Reports": ctk.CTkFrame(self.content, fg_color="#FFFFFF"),
            "Export": ctk.CTkFrame(self.content, fg_color="#FFFFFF"),
            "Logout": ctk.CTkFrame(self.content, fg_color="#FFFFFF"),
        }

        self.create_reports_tab(self.tabs["Reports"])
        self.create_export_tab(self.tabs["Export"])

        self.show_tab("Reports")

    # -------------------------------
    # TAB CLICK
    # -------------------------------
    def tab_click(self, tab_name):
        if tab_name.lower() == "logout":
            self.logout_confirm()
        else:
            self.show_tab(tab_name)

    def logout_confirm(self):
        from tkinter import messagebox
        answer = messagebox.askyesno("Confirm Logout", "Do you want to logout?")
        if answer:
            if self.current_landing:
                self.current_landing.destroy()
                self.current_landing = None
            self.show_login()

    # -------------------------------
    # SHOW TAB WITH ANIMATION
    # -------------------------------
    def show_tab(self, name):
        # Hide current landing page if exists
        if self.current_landing:
            self.current_landing.pack_forget()
            self.current_landing.destroy()
            self.current_landing = None

        # Hide all tab frames
        for t in self.tabs.values():
            t.pack_forget()

        # Slide in animation
        frame = self.tabs[name]
        frame.pack(fill="both", expand=True)
        frame.place(x=900, y=0)
        self.slide_in(frame, target_x=0)

        for tab, btn in self.tab_buttons.items():
            btn.configure(fg_color="#274690" if tab == name else "transparent")

    def slide_in(self, widget, target_x, speed=30):
        current_x = widget.winfo_x()
        if current_x > target_x:
            current_x -= speed
            if current_x < target_x:
                current_x = target_x
            widget.place(x=current_x, y=0)
            self.after(10, lambda: self.slide_in(widget, target_x, speed))
        else:
            widget.place(x=target_x, y=0)

    # -------------------------------
    # REPORTS LIST
    # -------------------------------
    def create_reports_tab(self, parent):
        parent.pack(fill="both", expand=True)
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        items = ["Item 1", "Item 2", "Item 3"]
        for item in items:
            btn = ctk.CTkButton(
                scroll,
                text=f"▶ {item}",
                anchor="w",
                height=40,
                fg_color="#F0F4FF",
                text_color="#1E3A8A",
                command=lambda name=item: self.open_item(name)
            )
            btn.pack(fill="x", pady=6)

    # -------------------------------
    # EXPORT TAB
    # -------------------------------
    def create_export_tab(self, parent):
        parent.pack(fill="both", expand=True)
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        items = ["emergency license", "regular license"]
        for item in items:
            btn = ctk.CTkButton(
                scroll,
                text=f"▶ {item}",
                anchor="w",
                height=40,
                fg_color="#F0F4FF",
                text_color="#1E3A8A",
                command=lambda name=item: self.open_item(name)
            )
            btn.pack(fill="x", pady=6)

    # -------------------------------
    # OPEN LANDING PAGES (FULL PAGE)
    # -------------------------------
    def open_item(self, name):
        # Destroy previous landing page
        if self.current_landing:
            self.current_landing.pack_forget()
            self.current_landing.destroy()
            self.current_landing = None

        # Open new landing page
        if name == "Item 1":
            self.current_landing = Item1Landing(self.content, on_back=lambda: self.show_tab("Reports"))
        elif name == "Item 2":
            self.current_landing = Item2Landing(self.content, on_back=lambda: self.show_tab("Reports"))
        elif name in ["emergency license", "regular license"]:
            self.current_landing = LicenseExportLanding(self.content, on_back=lambda: self.show_tab("Export"))

        if self.current_landing:
            self.current_landing.pack(fill="both", expand=True)

    # -------------------------------
    # MENU ANIMATION
    # -------------------------------
    def toggle_menu(self):
        if self.menu_visible:
            self.hide_menu()
        else:
            self.show_menu_anim()

    def hide_menu(self):
        w = self.left_menu.winfo_width()
        if w > 60:
            self.left_menu.configure(width=w - self.animation_speed)
            self.after(10, self.hide_menu)
        else:
            self.tabs_frame.pack_forget()
            self.menu_visible = False

    def show_menu_anim(self):
        self.tabs_frame.pack(fill="y", expand=True)
        w = self.left_menu.winfo_width()
        if w < 180:
            self.left_menu.configure(width=w + self.animation_speed)
            self.after(10, self.show_menu_anim)
        else:
            self.menu_visible = True

    # -------------------------------
    # LOGO
    # -------------------------------
    def load_logo(self, size):
        path = self.assets_dir / "logo.png"
        if path.exists():
            img = Image.open(path).resize(size)
        else:
            img = Image.new("RGB", size, "#3B82F6")
            draw = ImageDraw.Draw(img)
            draw.text((20, 50), "LOGO", fill="white")

        ctk_img = ctk.CTkImage(img, size=size)
        self._image_refs.append(ctk_img)
        return ctk_img


# -------------------------------
# RUN APP
# -------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
