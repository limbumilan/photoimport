import oracledb
import pandas as pd
import customtkinter as ctk
from tkinter import messagebox, filedialog
from baselanding import BaseLanding
import os
from datetime import datetime

USERNAME = "dotm_milan"
DSN = "10.250.252.201/DOTM"


class RegularLicenseExportLanding(BaseLanding):

    def __init__(self, parent, on_back):
        super().__init__(parent, on_back)
        self.configure(fg_color="#F5F8FF")

        self.df = None
        self.base_folder = None

        # ---------- HEADER ----------
        header = ctk.CTkFrame(self, fg_color="#1E3A8A", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Regular License Export",
            text_color="white",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)

        # ---------- FIX BODY (IMPORTANT) ----------
        try:
            self.body.pack_forget()
        except Exception:
            pass

        self.body.pack(fill="both", expand=True, padx=20, pady=20)

        # ---------- TITLE ----------
        ctk.CTkLabel(
            self.body,
            text="Regular License Export Page",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        # ---------- FOLDER ----------
        ctk.CTkLabel(self.body, text="Base Folder").pack(anchor="w")
        self.folder_label = ctk.CTkLabel(self.body, text="Not selected")
        self.folder_label.pack(anchor="w", pady=2)

        ctk.CTkButton(
            self.body,
            text="Select Folder",
            command=self.select_folder
        ).pack(pady=5)

        # ---------- PASSWORD ----------
        ctk.CTkLabel(self.body, text="Oracle Password").pack(anchor="w")
        self.password = ctk.CTkEntry(self.body, show="*")
        self.password.pack(fill="x", pady=5)

        # ---------- OFFICE ----------
        ctk.CTkLabel(self.body, text="License Office").pack(anchor="w")
        self.office = ctk.CTkComboBox(self.body)
        self.office.pack(fill="x", pady=5)

        ctk.CTkButton(
            self.body,
            text="Load Offices",
            command=self.load_offices
        ).pack(pady=5)

        # ---------- DATE ----------
        ctk.CTkLabel(self.body, text="Date From (DD-MM-YYYY)").pack(anchor="w")
        self.date_from = ctk.CTkEntry(self.body)
        self.date_from.pack(fill="x", pady=5)

        ctk.CTkLabel(self.body, text="Date To (DD-MM-YYYY)").pack(anchor="w")
        self.date_to = ctk.CTkEntry(self.body)
        self.date_to.pack(fill="x", pady=5)

        # ---------- BUTTON ----------
        ctk.CTkButton(
            self.body,
            text="Fetch Data",
            height=40,
            command=self.fetch_data
        ).pack(pady=10)

        # ---------- LOG ----------
        ctk.CTkLabel(self.body, text="Log").pack(anchor="w")

        self.log_box = ctk.CTkTextbox(self.body, height=200)
        self.log_box.pack(fill="both", expand=True)

    # ---------- LOG ----------
    def log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.update_idletasks()

    # ---------- FOLDER ----------
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.base_folder = folder
            self.folder_label.configure(text=folder)

    # ---------- LOAD OFFICES ----------
    def load_offices(self):
        try:
            conn = oracledb.connect(
                user=USERNAME,
                password=self.password.get(),
                dsn=DSN
            )
            cur = conn.cursor()
            cur.execute("SELECT name FROM edlvrs.licenseissueoffice ORDER BY name")
            offices = [r[0] for r in cur.fetchall()]
            self.office.configure(values=offices)
            conn.close()
            self.log("Offices loaded")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- FETCH ----------
    def fetch_data(self):
        if not self.base_folder:
            messagebox.showerror("Error", "Select base folder first")
            return

        try:
            conn = oracledb.connect(
                user=USERNAME,
                password=self.password.get(),
                dsn=DSN
            )

            self.log("Connected to Oracle")

            # simple test query (replace with your real SQL)
            df = pd.read_sql(
                "SELECT * FROM edlvrs.licenseissueoffice",
                conn
            )

            self.df = df

            file_path = os.path.join(
                self.base_folder,
                f"regular_export_{datetime.now():%Y%m%d_%H%M%S}.csv"
            )

            df.to_csv(file_path, index=False)

            self.log(f"CSV saved → {file_path}")

            conn.close()
            self.log("✔ Done")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log(f"Error: {e}")