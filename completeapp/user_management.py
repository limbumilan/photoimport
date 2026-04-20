import customtkinter as ctk
from tkinter import ttk, messagebox
from baselanding import BaseLanding
import mysql.connector
import hashlib


# =========================
# HASH FUNCTION
# =========================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# =========================
# DB CONNECTION
# =========================
def get_conn():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        
        database="print_mangement"
    )


# =========================
# USER MANAGEMENT
# =========================
class UserManagementLanding(BaseLanding):
    def __init__(self, parent, on_back):
        super().__init__(parent, on_back)
        self.configure(fg_color="#F5F8FF")

        self.edit_index = None

        # ================= HEADER =================
        header = ctk.CTkFrame(self, fg_color="#1E3A8A", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="User Management",
            text_color="white",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)

        # ================= BODY =================
        try:
            self.body.pack_forget()
        except Exception:
            pass

        self.body.pack(fill="both", expand=True, padx=20, pady=20)

        # ================= FORM =================
        form = ctk.CTkFrame(self.body)
        form.pack(fill="x", pady=10)

        form.grid_columnconfigure(0, weight=0)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=0)
        form.grid_columnconfigure(3, weight=1)
        form.grid_columnconfigure(4, weight=0)
        form.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(form, text="Username").grid(row=0, column=0, padx=5, pady=5)
        self.username = ctk.CTkEntry(form, width=180)
        self.username.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(form, text="Password").grid(row=0, column=2, padx=5)
        self.password = ctk.CTkEntry(form, show="*", width=180)
        self.password.grid(row=0, column=3, padx=5)

        ctk.CTkLabel(form, text="Role").grid(row=0, column=4, padx=5)
        self.role = ctk.CTkComboBox(form, values=["Admin", "User"])
        self.role.set("User")
        self.role.grid(row=0, column=5, padx=5)

        # Buttons
        self.btn_add = ctk.CTkButton(form, text="Add User", command=self.add_user)
        self.btn_add.grid(row=0, column=6, padx=5)

        self.btn_update = ctk.CTkButton(
            form,
            text="Update User",
            fg_color="green",
            command=self.update_user
        )
        self.btn_update.grid(row=0, column=7, padx=5)
        self.btn_update.configure(state="disabled")

        # ================= TABLE =================
        table_frame = ctk.CTkFrame(self.body)
        table_frame.pack(fill="both", expand=True, pady=10)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("Username", "Password", "Role"),
            show="headings"
        )

        for col in ("Username", "Password", "Role"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="white",
            fieldbackground="white",
            foreground="black"
        )

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # ================= ACTIONS =================
        actions = ctk.CTkFrame(self.body)
        actions.pack(fill="x", pady=5)

        ctk.CTkButton(actions, text="Delete User", command=self.delete_user).pack(side="left", padx=5)
        ctk.CTkButton(actions, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)

        self.refresh()

    # ================= ADD USER =================
    def add_user(self):
        u = self.username.get().strip()
        p = self.password.get().strip()
        r = self.role.get()

        if not u or not p:
            messagebox.showwarning("Warning", "Username and password required")
            return

        try:
            conn = get_conn()
            cur = conn.cursor()

            hashed_pw = hash_password(p)

            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (u, hashed_pw, r)
            )

            conn.commit()
            conn.close()

            self.refresh()
            self.clear_form()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= UPDATE USER =================
    def update_user(self):
        selected = self.tree.selection()
        if not selected:
            return

        old_username = self.tree.item(selected[0])["values"][0]

        u = self.username.get().strip()
        p = self.password.get().strip()
        r = self.role.get()

        if not u or not p:
            messagebox.showwarning("Warning", "Fields required")
            return

        try:
            conn = get_conn()
            cur = conn.cursor()

            hashed_pw = hash_password(p)

            cur.execute("""
                UPDATE users
                SET username=%s, password=%s, role=%s
                WHERE username=%s
            """, (u, hashed_pw, r, old_username))

            conn.commit()
            conn.close()

            self.refresh()
            self.clear_form()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= DELETE USER =================
    def delete_user(self):
        selected = self.tree.selection()
        if not selected:
            return

        username = self.tree.item(selected[0])["values"][0]

        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("DELETE FROM users WHERE username=%s", (username,))

            conn.commit()
            conn.close()

            self.refresh()
            self.clear_form()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= REFRESH TABLE =================
    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT username, password, role FROM users")
            rows = cur.fetchall()

            conn.close()

            for r in rows:
                self.tree.insert("", "end", values=r)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= FORM HELPERS =================
    def clear_form(self):
        self.username.delete(0, "end")
        self.password.delete(0, "end")
        self.role.set("User")

        self.btn_add.configure(state="normal")
        self.btn_update.configure(state="disabled")

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])["values"]

        self.username.delete(0, "end")
        self.username.insert(0, item[0])

        self.password.delete(0, "end")
        self.password.insert(0, "")  # do not show hashed password

        self.role.set(item[2])

        self.btn_add.configure(state="disabled")
        self.btn_update.configure(state="normal")