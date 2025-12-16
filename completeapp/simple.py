import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import pandas as pd
import oracledb
from datetime import datetime
import os

# ---------------- CONFIG ----------------
USERNAME = "dotm_milan"
DSN = "10.250.252.201/DOTM"
BASE_DATA_FOLDER = "/Users/milanlimbu/desktop/data"
OUTPUT_DIRS = {
    "photo": os.path.join(BASE_DATA_FOLDER, "Photo"),
    "sign1": os.path.join(BASE_DATA_FOLDER, "Sign1"),
    "sign2": os.path.join(BASE_DATA_FOLDER, "Sign2")
}
os.makedirs(BASE_DATA_FOLDER, exist_ok=True)
for f in OUTPUT_DIRS.values():
    os.makedirs(f, exist_ok=True)

# ---------------- SQL TEMPLATES ----------------
SQL_LICENSE_INFO = """ 
-- Your existing license SQL here, with :license_no and office_id parameters
"""

SQL_PHOTO = """ SELECT applicant_id, photograph FROM edlvrs.applicant_biometric WHERE applicant_id IN ({{IDS}}) AND photograph IS NOT NULL """
SQL_SIGN1 = """ SELECT A.ID, B.signature FROM ... """  # your previous SQL
SQL_SIGN2 = """ SELECT applicant_id, signature FROM edlvrs.applicant_biometric WHERE applicant_id IN ({{IDS}}) AND signature IS NOT NULL """

# ---------------- APP CLASS ----------------
class LicenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DOTM License Manager")
        self.geometry("800x600")
        self.frames = {}
        for F in (LoginPage, LicensePage, ExportPage):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("LoginPage")

        # Shared state
        self.conn = None
        self.applicant_ids = set()
        self.final_df = pd.DataFrame()

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()


# ---------------- PAGES ----------------
class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        tk.Label(self, text="Oracle Password:").pack(pady=10)
        self.entry_password = ttk.Entry(self, width=30, show="*")
        self.entry_password.pack(pady=5)
        ttk.Button(self, text="Login", command=self.login).pack(pady=10)

    def login(self):
        password = self.entry_password.get().strip()
        if not password:
            messagebox.showwarning("Missing", "Enter Oracle password")
            return
        try:
            conn = oracledb.connect(user=USERNAME, password=password, dsn=DSN)
            self.controller.conn = conn
            messagebox.showinfo("Success", "Connected to Oracle")
            self.controller.show_frame("LicensePage")
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))


class LicensePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        tk.Label(self, text="License Numbers (comma/space separated):").pack(pady=5)
        self.entry_license = ttk.Entry(self, width=80)
        self.entry_license.pack(pady=5)

        tk.Label(self, text="Select Office:").pack(pady=5)
        self.office_combo = ttk.Combobox(self, values=["All Offices", "Office 1", "Office 2"], state="readonly")
        self.office_combo.current(0)
        self.office_combo.pack(pady=5)

        ttk.Button(self, text="Fetch Data", command=self.start_fetch).pack(pady=10)
        ttk.Button(self, text="Next → Export Page", command=lambda: controller.show_frame("ExportPage")).pack(pady=5)

    def start_fetch(self):
        threading.Thread(target=self.fetch_data).start()

    def fetch_data(self):
        license_input = self.entry_license.get().strip()
        if not license_input:
            messagebox.showwarning("Input", "Enter license numbers")
            return
        license_numbers = [x.strip() for x in license_input.replace(",", " ").split() if x.strip()]
        office_selected = self.office_combo.get()
        office_id = None if office_selected=="All Offices" else office_selected  # adapt mapping

        conn = self.controller.conn
        all_data = []
        applicant_ids = set()
        for lic in license_numbers:
            try:
                df = pd.read_sql(SQL_LICENSE_INFO, conn, params={"license_no": lic, "office_id": office_id})
            except Exception as e:
                print(f"Error fetching {lic}: {e}")
                continue
            if df.empty:
                continue
            ids = df["ProductID"].dropna().astype(int).tolist()
            applicant_ids.update(ids)
            all_data.append(df)

        if not all_data:
            messagebox.showinfo("No Data", "No license records found")
            return

        self.controller.final_df = pd.concat(all_data, ignore_index=True)
        self.controller.applicant_ids = applicant_ids
        messagebox.showinfo("Success", f"Fetched {len(applicant_ids)} applicant records")


class ExportPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Button(self, text="← Back", command=lambda: controller.show_frame("LicensePage")).pack(pady=5)
        
        ttk.Button(self, text="Export CSV", command=self.export_csv).pack(pady=10)
        self.log_box = scrolledtext.ScrolledText(self, width=90, height=30)
        self.log_box.pack(pady=10)

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def export_csv(self):
        df = self.controller.final_df
        if df.empty:
            messagebox.showwarning("No Data", "No data to export")
            return
        csv_path = os.path.join(BASE_DATA_FOLDER, f"license_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(csv_path, index=False)
        self.log(f"CSV exported → {csv_path}")

        # Optionally, export images
        # You can reuse your export_blobs functions here for Photo, Sign1, Sign2


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app = LicenseApp()
    app.mainloop()
