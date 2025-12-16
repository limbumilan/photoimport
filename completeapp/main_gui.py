import customtkinter as ctk
from PIL import Image, ImageDraw
from pathlib import Path
import tkinter as tk
from item1_landing import Item1Landing
from item2_landing import Item2Landing
from extractionfinal import LicenseExportLanding

from importfromlicenseoffice import RegularLicenseExportLanding
# -------------------------------
# PLACEHOLDER LANDING PAGES
# -------------------------------



# -------------------------------
# MAIN APP
# -------------------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Department of Transport Management")
        self.geometry("900x600")
        self.configure(fg_color="#F0F4FF")

        self.assets_dir = Path(__file__).parent / "assets"
        self.assets_dir.mkdir(exist_ok=True)

        self.menu_visible = True
        self.animation_speed = 18
        self.collapsed_width = 48
        self.expanded_width = 180
        self.current_landing = None
        self._image_refs = []

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
        self.main_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)

    def show_main(self):
        self.login_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    # -------------------------------
    # LOGIN UI
    # -------------------------------
    def create_login_ui(self, parent):
        logo = self.load_logo((160, 120))
        ctk.CTkLabel(parent, image=logo, text="").pack(pady=30)

        ctk.CTkLabel(parent, text="Department of Transport Management",
                     font=("Arial", 16, "bold"), text_color="#1E3A8A").pack(pady=10)

        self.password = ctk.CTkEntry(parent, show="*", width=200)
        self.password.pack(pady=10)

        ctk.CTkButton(parent, text="Login", width=150, command=self.login).pack(pady=10)

    def login(self):
        if self.password.get():
            self.show_main()

    # -------------------------------
    # MAIN UI
    # -------------------------------
    def create_main_ui(self, parent):
        self.left_menu = ctk.CTkFrame(parent, width=180, fg_color="#1E3A8A")
        self.left_menu.pack(side="left", fill="y")
        self.left_menu.pack_propagate(False)

        # Top area inside menu to always host the toggle button so it stays visible
        self.left_menu_top = ctk.CTkFrame(self.left_menu, fg_color="transparent")
        self.left_menu_top.pack(fill="x")
        self.left_menu_top.pack_propagate(False)

        self.toggle_btn = ctk.CTkButton(
            self.left_menu_top, text="☰", width=40, height=40,
            fg_color="transparent", hover_color="#274690",
            font=("Arial", 22, "bold"), command=self.toggle_menu
        )
        self.toggle_btn.pack(anchor="w", padx=8, pady=10)

        # lightweight tooltip for the toggle button
        try:
            class _ToolTip:
                def __init__(self, widget, text, delay=500):
                    self.widget = widget
                    self.text = text
                    self.delay = delay
                    self._id = None
                    self.tip = None
                    widget.bind("<Enter>", self._schedule)
                    widget.bind("<Leave>", self._hide)

                def _schedule(self, _event=None):
                    self._id = self.widget.after(self.delay, self._show)

                def _show(self):
                    if self.tip:
                        return
                    x = self.widget.winfo_rootx() + 20
                    y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
                    self.tip = tk.Toplevel(self.widget)
                    self.tip.wm_overrideredirect(True)
                    label = tk.Label(self.tip, text=self.text, bg="#333", fg="white", bd=1, padx=6, pady=2)
                    label.pack()
                    self.tip.wm_geometry(f"+{x}+{y}")

                def _hide(self, _event=None):
                    if self._id:
                        try:
                            self.widget.after_cancel(self._id)
                        except Exception:
                            pass
                        self._id = None
                    if self.tip:
                        try:
                            self.tip.destroy()
                        except Exception:
                            pass
                        self.tip = None

            _ToolTip(self.toggle_btn, "Toggle menu")
        except Exception:
            pass

        self.tabs_frame = ctk.CTkFrame(self.left_menu, fg_color="#1E3A8A")
        self.tabs_frame.pack(fill="y", expand=True)

        self.tab_buttons = {}
        for tab in ["Reports", "Export", "Logout"]:
            btn = ctk.CTkButton(
                self.tabs_frame, text=tab, height=42,
                fg_color="transparent", text_color="white",
                anchor="w", command=lambda t=tab: self.tab_click(t)
            )
            btn.pack(fill="x", padx=10, pady=4)
            self.tab_buttons[tab] = btn

        self.content = ctk.CTkFrame(parent, fg_color="#FFFFFF")
        self.content.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # IMPORTANT: tabs must NOT be packed here
        self.tabs = {
            "Reports": ctk.CTkFrame(self.content, fg_color="#FFFFFF"),
            "Export": ctk.CTkFrame(self.content, fg_color="#FFFFFF")
        }

        # track last shown tab so we can restore after collapse
        self._last_tab = "Reports"
        self._tabs_visible = True

        self.create_reports_tab(self.tabs["Reports"])
        self.create_export_tab(self.tabs["Export"])

        self.show_tab("Reports")

    # -------------------------------
    # TAB CONTROL
    # -------------------------------
    def tab_click(self, name):
        if name == "Logout":
            self.show_login()
        else:
            self.show_tab(name)

    def show_tab(self, name):
        # show_tab called -> name
        if self.current_landing:
            self.current_landing.destroy()
            self.current_landing = None

        for tab in self.tabs.values():
            tab.place_forget()

        frame = self.tabs[name]
        self.content.update_idletasks()
        w = self.content.winfo_width()

        # place the frame immediately at 0 so content is visible right away
        frame.place(x=0, y=0, relwidth=1, relheight=1)
        try:
            # ensure geometry is calculated and widget is on top
            frame.update_idletasks()
            frame.update()
            frame.tkraise()
        except Exception:
            try:
                frame.lift()
            except Exception:
                pass
        try:
            children = frame.winfo_children()
            # inspected children count = %d
            for c in children:
                pass

            # recursive inspection helper
            def _dump(w, depth=0, maxdepth=4):
                if depth > maxdepth:
                    return
                try:
                    kids = w.winfo_children()
                except Exception:
                    return
                for k in kids:
                    try:
                        ktype = type(k)
                        try:
                            text = k.cget('text')
                        except Exception:
                            text = None
                        try:
                            mapped = k.winfo_ismapped()
                            w_w = k.winfo_width()
                            w_h = k.winfo_height()
                            w_x = k.winfo_x()
                            w_y = k.winfo_y()
                        except Exception:
                            mapped = None
                            w_w = w_h = w_x = w_y = None
                        # node depth=%d type=%s text=%s mapped=%s w/h=%s x/y=%s
                    except Exception:
                        pass
                    _dump(k, depth+1, maxdepth)

            _dump(frame)
        except Exception:
            pass
        try:
            frame.tkraise()
        except Exception:
            try:
                frame.lift()
            except Exception:
                pass

        # record last shown tab
        self._last_tab = name
        self._tabs_visible = True

        for t, btn in self.tab_buttons.items():
            btn.configure(fg_color="#274690" if t == name else "transparent")

    def _ensure_update(self, widget, depth=0, maxdepth=6):
        try:
            widget.update_idletasks()
            widget.update()
        except Exception:
            pass
        if depth >= maxdepth:
            return
        try:
            for c in widget.winfo_children():
                self._ensure_update(c, depth+1, maxdepth)
        except Exception:
            pass

    # -------------------------------
    # ANIMATIONS
    # -------------------------------
    def slide_in(self, widget, target_x=0):
        try:
            x = widget.winfo_x()
        except Exception:
            x = 0

        if x > target_x:
            new_x = max(x - self.animation_speed, target_x)
            try:
                widget.place(x=new_x, y=0, relwidth=1, relheight=1)
            except Exception:
                widget.place_configure(x=new_x, y=0, relwidth=1, relheight=1)
            self.after(10, lambda: self.slide_in(widget, target_x))
        else:
            try:
                widget.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                try:
                    widget.place_configure(x=0, y=0, relwidth=1, relheight=1)
                except Exception:
                    pass
            try:
                widget.update_idletasks()
            except Exception:
                pass
            # ensure widget is raised when animation finishes
            try:
                widget.tkraise()
            except Exception:
                try:
                    widget.lift()
                except Exception:
                    pass

    def toggle_menu(self):
        if self.menu_visible:
            # hide tab buttons (keep the frame) then collapse menu
            self.hide_tab_buttons()
            # switch icon immediately
            try:
                self.toggle_btn.configure(text="→")
            except Exception:
                pass
            # mark state immediately so repeated clicks toggle correctly
            self.menu_visible = False
            self.hide_menu()
        else:
            # show tab buttons then expand menu
            try:
                self.toggle_btn.configure(text="☰")
            except Exception:
                pass
            self.show_tab_buttons()
            # mark state immediately so repeated clicks toggle correctly
            self.menu_visible = True
            self.show_menu()

    def hide_menu(self):
        # immediately collapse to the compact width and keep the toggle visible
        self.left_menu.configure(width=self.collapsed_width)
        self.left_menu_top.configure(width=self.collapsed_width)
        self.menu_visible = False


    def show_menu(self):
        # animate expand to full menu width and restore buttons
        # show buttons immediately so they appear when menu finishes
        self.show_tab_buttons()
        # immediately expand to full width
        self.left_menu.configure(width=self.expanded_width)
        self.left_menu_top.configure(width=self.expanded_width)
        self.menu_visible = True

    def _animate_menu(self, target, step=12, delay=10):
        # safe animate: enforce bounds to avoid runaway widths
        try:
            current = self.left_menu.winfo_width()
        except Exception:
            current = self.expanded_width if target > 100 else self.collapsed_width

        if current == target:
            self.left_menu.configure(width=target)
            self.left_menu_top.configure(width=target)
            self.menu_visible = (target == self.expanded_width)
            return

        if current < target:
            new = min(target, current + step)
        else:
            new = max(target, current - step)

        # clamp to expected range
        new = max(self.collapsed_width, min(self.expanded_width, new))
        self.left_menu.configure(width=new)
        self.left_menu_top.configure(width=new)

        # continue animation until target
        self.after(delay, lambda: self._animate_menu(target, step, delay))

    # -------------------------------
    # TAB BUTTON VISIBILITY HELPERS
    # -------------------------------
    def hide_tab_buttons(self):
        for btn in list(self.tab_buttons.values()):
            try:
                btn.pack_forget()
            except Exception:
                pass

    def show_tab_buttons(self):
        # re-pack in the original order
        for tab in ["Reports", "Export", "Logout"]:
            btn = self.tab_buttons.get(tab)
            if btn:
                try:
                    btn.pack(fill="x", padx=10, pady=4)
                except Exception:
                    pass

    # -------------------------------
    # TABS CONTENT
    # -------------------------------
    def create_reports_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent,fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        for name in ["Item 1", "Item 2"]:
            ctk.CTkButton(
                scroll, text=f"▶ {name}", anchor="w", height=40,
                fg_color="#E6EEF9", text_color="#1E3A8A",
                command=lambda n=name: self.open_item(n)
            ).pack(fill="x", pady=6)

    def create_export_tab(self, parent):
        # create_export_tab building export buttons
        # use a plain frame instead of CTkScrollableFrame to avoid nested-canvas visibility issues
        scroll = ctk.CTkFrame(parent, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        for name in ["emergency license", "regular license"]:
            btn = ctk.CTkButton(
                scroll, text=f"▶ {name}", anchor="w", height=40,
                fg_color="#E6EEF9", text_color="#1E3A8A",
                border_width=1, border_color="#C7D2FE",
                command=lambda n=name: self.open_item(n)
            )
            btn.pack(fill="x", pady=6)
            # created export button: {name}

        try:
            scroll.update_idletasks()
            scroll.tkraise()
        except Exception:
            pass

    # -------------------------------
    # LANDING PAGES
    # -------------------------------
    def open_item(self, name):
        # open_item called -> name
        if self.current_landing:
            self.current_landing.destroy()

        if name == "Item 1":
            self.current_landing = Item1Landing(self.content, lambda: self.show_tab("Reports"))
        elif name == "Item 2":
            self.current_landing = Item2Landing(self.content, lambda: self.show_tab("Reports"))
        elif name == "emergency license":
            self.current_landing = LicenseExportLanding(self.content, lambda: self.show_tab("Export"))
        else:
            self.current_landing = RegularLicenseExportLanding(self.content, lambda: self.show_tab("Export"))
        # ensure geometry is calculated; fallback to window width if needed
        try:
            self.content.update_idletasks()
            w = self.content.winfo_width()
        except Exception:
            try:
                w = self.winfo_width()
            except Exception:
                w = 800

        if not w or w < 2:
            try:
                w = self.winfo_width()
            except Exception:
                w = 800

        # place the landing off-screen to the right then slide in
        try:
            self.current_landing.place(x=w, y=0, relwidth=1, relheight=1)
        except Exception:
            try:
                self.current_landing.place_configure(x=w, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        # give widgets a chance to map before animating
        self._ensure_update(self.current_landing)
        self.slide_in(self.current_landing)
        try:
            self.current_landing.tkraise()
        except Exception:
            try:
                self.current_landing.lift()
            except Exception:
                pass

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
            draw.text((40, 45), "LOGO", fill="white")

        ctk_img = ctk.CTkImage(img, size=size)
        self._image_refs.append(ctk_img)
        return ctk_img


if __name__ == "__main__":
    app = App()
    app.mainloop()
