
import oracledb
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime

# ============================================
# CONFIG
# ============================================
USERNAME = "dotm_milan"
DSN = "10.250.252.201/DOTM"

# ============================================
# SQL QUERY TEMPLATE
# ============================================
SQL_LICENSE_INFO = """
SELECT
    A.ID AS PRODUCTID,
    A.LASTNAME AS Surname,
    A.FIRSTNAME || ' ' || NVL(A.MIDDLENAME,'') AS Given_Name,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS Sex,
    TO_CHAR(A.DATEOFBIRTHAD,'DD-MM-YYYY') AS Date_of_birth,
    'Government of Nepal' AS Nationality,
    (SELECT TO_CHAR(MIN(CAST(ISSUEDATE AS DATE)),'DD-MM-YYYY')
       FROM edlvrs.licensedetail
       WHERE newlicenseno = ld.newlicenseno) AS Date_of_issue,
    TO_CHAR(LD.EXPIRYDATE, 'DD-MM-YYYY') AS Date_of_expiry,
    A.CITIZENSHIPNUMBER AS Citizenship_No,
    A.PASSPORTNUMBER AS Passport_No,
    '@photo\\' || A.ID || '.tif' AS Photo,
    A.MOBILENUMBER AS Contact_No,
    (SELECT name FROM edlvrs.licenseissueoffice WHERE ID = ld.licenseissueoffice_id) AS License_Office,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || NVL(A.WITNESSLASTNAME,'') AS FH_Name,
    (SELECT TYPE FROM edlvrs.bloodgroup WHERE ID = A.BLOODGROUP_ID) AS BG,
    (SELECT name FROM edlvrs.district WHERE ID = AD.district_id) AS Region,
    COALESCE(NULLIF(
        (SELECT NAME FROM edlvrs.villagemetrocity WHERE ID = AD.villagemetrocity_id),
        'OTHERS'
    ), '') || ' ' || COALESCE(AD.tole,'') || '-' || COALESCE(AD.wardnumber,'') AS Street_House_Number,
    (SELECT name FROM edlvrs.country WHERE id = AD.country_id) AS Country,
    LD.NEWLICENSENO AS Driving_License_No,
    (SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
       FROM edlvrs.licensedetail dl
       JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
       JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
       WHERE dl.newlicenseno = LD.newlicenseno) AS Category
FROM edlvrs.licensedetail LD
JOIN edlvrs.license L ON LD.license_id = L.id
JOIN edlvrs.applicant A ON L.applicant_id = A.id
LEFT JOIN edlvrs.address AD ON A.id = AD.applicant_id AND AD.addresstype='PERM'
WHERE LD.issuedate BETWEEN TO_DATE(:date_from,'DD-MM-YYYY') AND TO_DATE(:date_to,'DD-MM-YYYY')

AND LD.licenseissueoffice_id = (
SELECT id FROM edlvrs.licenseissueoffice
WHERE name=:office)

AND LD.expirydate = (
SELECT MAX(expirydate) 
FROM EDLVRS.LICENSEDETAIL
WHERE LICENSE_ID = L.ID 
AND ld.expirydate > ADD_MONTHS(SYSDATE, 6))

AND LD.issuedate = (
SELECT MAX(issuedate)
FROM EDLVRS.LICENSEDETAIL WHERE LICENSE_ID = L.ID)
AND ad.addresstype = 'PERM'
AND l.printed = '0'
and l.licensestatus = 'VALID'
and ld.accountstatus = 'VALID'
"""

# ============================================
# BLOB UTILITY FUNCTIONS
# ============================================
def save_blob(blob, file_path):
    with open(file_path, "wb") as f:
        f.write(blob.read())


def export_blobphoto(conn, ids, sql_template, out_dir, label):
    if not ids:
        print(f"No IDs for {label}")
        return
    cursor = conn.cursor()
    bind_vars = {f"id{i}": val for i, val in enumerate(ids)}
    placeholders = ",".join(f":id{i}" for i in range(len(ids)))
    sql = sql_template.replace("{{IDS}}", placeholders)
    cursor.execute(sql, bind_vars)
    rows = cursor.fetchall()
    for aid, blob in rows:
        path = os.path.join(out_dir, f"{aid}.tif")
        save_blob(blob, path)
        print(f"{label} saved: {path}")
    cursor.close()


def export_blobsign(conn, ids, sql_template, out_dir, label):
    if not ids:
        print(f"No IDs for {label}")
        return
    cursor = conn.cursor()
    bind_vars = {f"id{i}": val for i, val in enumerate(ids)}
    placeholders = ",".join(f":id{i}" for i in range(len(ids)))
    sql = sql_template.replace("{{IDS}}", placeholders)
    cursor.execute(sql, bind_vars)
    rows = cursor.fetchall()
    for aid, blob in rows:
        path = os.path.join(out_dir, f"{aid}.jpg")
        save_blob(blob, path)
        print(f"{label} saved: {path}")
    cursor.close()


# ============================================
# GUI CLASS
# ============================================
class LicenseGUI:
    
    def __init__(self, root):
        
        self.root = root
        root.title("Demo Personalization ware")
        root.geometry("1100x650")
        root.configure(bg="#87CEEB")  # sky blue background

        self.base_folder = None
        self.output_dirs = {}
        self.df = None

        # ===== Base Folder Selection =====
        folder_frame = tk.Frame(root, bg="#87CEEB")
        folder_frame.pack(fill="x", pady=5)
        tk.Label(folder_frame, text="Base Data Folder:", bg="#87CEEB", fg="#003366", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.folder_label = tk.Label(folder_frame, text="Not selected", fg="#003366", bg="#87CEEB", font=("Arial", 10))
        self.folder_label.pack(side="left", padx=5)
        tk.Button(folder_frame, text="Select Folder", command=self.select_base_folder, bg="#4682B4", fg="white").pack(side="left", padx=5)

        # ===== Login Frame =====
        login_frame = tk.LabelFrame(root, text="Oracle Login", padx=10, pady=10, bg="#87CEEB", fg="#003366", font=("Arial", 10, "bold"))
        login_frame.pack(fill="x", pady=5)
        tk.Label(login_frame, text="Password:", bg="#87CEEB", fg="#003366").grid(row=0, column=0)
        self.password_entry = tk.Entry(login_frame, show="*")
        self.password_entry.grid(row=0, column=1)

        # ===== Filters =====
        filter_frame = tk.LabelFrame(root, text="Filters", padx=10, pady=10, bg="#87CEEB", fg="#003366", font=("Arial", 10, "bold"))
        filter_frame.pack(fill="x", pady=5)
        tk.Label(filter_frame, text="Select Office:", bg="#87CEEB", fg="#003366").grid(row=0, column=0)
        self.office_combo = ttk.Combobox(filter_frame, width=40)
        self.office_combo.grid(row=0, column=1)
        tk.Button(filter_frame, text="Load Offices", command=self.load_offices, bg="#4682B4", fg="white").grid(row=0, column=2, padx=5)

        tk.Label(filter_frame, text="From Date:", bg="#87CEEB", fg="#003366").grid(row=1, column=0)
        self.from_day = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,32)], width=5)
        self.from_day.grid(row=1, column=1)
        self.from_day.set("01")
        self.from_month = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,13)], width=5)
        self.from_month.grid(row=1, column=2)
        self.from_month.set("01")
        self.from_year = ttk.Combobox(filter_frame, values=[str(y) for y in range(2010,2035)], width=7)
        self.from_year.grid(row=1, column=3)
        self.from_year.set("2024")

        tk.Label(filter_frame, text="To Date:", bg="#87CEEB", fg="#003366").grid(row=2, column=0)
        self.to_day = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,32)], width=5)
        self.to_day.grid(row=2, column=1)
        self.to_day.set("01")
        self.to_month = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,13)], width=5)
        self.to_month.grid(row=2, column=2)
        self.to_month.set("01")
        self.to_year = ttk.Combobox(filter_frame, values=[str(y) for y in range(2010,2035)], width=7)
        self.to_year.grid(row=2, column=3)
        self.to_year.set("2024")

        tk.Button(filter_frame, text="Fetch Data", command=self.fetch_data, bg="#00BFFF", fg="white").grid(row=3, column=0, columnspan=4, pady=10)

        # ===== Table =====
        table_frame = tk.Frame(root, bg="#87CEEB")
        table_frame.pack(fill="both", expand=True, padx=8, pady=5)
        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.pack(side="top", fill="both", expand=True)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(xscrollcommand=hsb.set)

        # ===== Actions =====
        action_frame = tk.Frame(root, bg="#00FF00")
        action_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(action_frame, text="Export CSV", command=self.export_csv, bg="#1E90FF", fg="black").pack(side="left", padx=5)
        self.status_label = tk.Label(action_frame, text="Status: Ready", anchor="w", bg="#87CEEB", fg="#003366")
        self.status_label.pack(side="left", padx=20)

        
    
    

    # ===== Base Folder Selection =====
    def select_base_folder(self):
        folder = filedialog.askdirectory(title="Select Base Data Folder")
        if not folder:
            messagebox.showerror("Error", "No folder selected!")
            return
        self.base_folder = folder
        self.folder_label.config(text=f"Selected: {folder}")
        # Create subfolders
        self.output_dirs = {k: os.path.join(folder, k.capitalize()) for k in ["photo", "sign1", "sign2"]}
        for path in self.output_dirs.values():
            os.makedirs(path, exist_ok=True)
        messagebox.showinfo("Success", "Base folder selected and subfolders created!")

    # ===== Load Offices =====
    def load_offices(self):
        try:
            pwd = self.password_entry.get().strip()
            conn = oracledb.connect(user=USERNAME, password=pwd, dsn=DSN)
            cur = conn.cursor()
            cur.execute("SELECT name FROM edlvrs.licenseissueoffice WHERE name NOT LIKE '-%' ORDER BY name")
            offices = [row[0] for row in cur.fetchall()]
            self.office_combo["values"] = offices
            messagebox.showinfo("Success", "Offices loaded!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ===== Fetch Data =====
    def fetch_data(self):
        if not self.output_dirs:
            messagebox.showerror("Error", "Please select a base folder first!")
            return

        pwd = self.password_entry.get().strip()
        office = self.office_combo.get().strip()
        date_from = f"{self.from_day.get()}-{self.from_month.get()}-{self.from_year.get()}"
        date_to = f"{self.to_day.get()}-{self.to_month.get()}-{self.to_year.get()}"

        if not office:
            messagebox.showwarning("Warning", "Select an office first!")
            return

        try:
            conn = oracledb.connect(user=USERNAME, password=pwd, dsn=DSN)
            df = pd.read_sql(SQL_LICENSE_INFO, conn, params={"office": office, "date_from": date_from, "date_to": date_to})

            if df.empty:
                messagebox.showinfo("No Data", "No records found for selected filters.")
                return

            self.df = df

            # Display in Treeview
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = df.columns.tolist()
            self.tree["show"] = "headings"
            for c in df.columns:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=150)
            for row in df.itertuples(index=False):
                self.tree.insert("", "end", values=row)

            messagebox.showinfo("Done", f"Fetched {len(df)} records")

            # Export BLOBs
            ids_list = df["PRODUCTID"].dropna().astype(int).tolist()

            SQL_PHOTO = """
            SELECT applicant_id, photograph FROM edlvrs.applicant_biometric WHERE applicant_id IN ({{IDS}}) AND photograph IS NOT NULL
            """
            SQL_SIGN2 = """
            SELECT applicant_id, signature FROM edlvrs.applicant_biometric WHERE applicant_id IN ({{IDS}}) AND signature IS NOT NULL
            """
            SQL_SIGN1 = """
            SELECT A.ID, B.signature FROM edlvrs.applicant A
            JOIN edlvrs.license L ON A.id = L.applicant_id
            JOIN edlvrs.licensedetail LD ON L.id = LD.license_id
            JOIN edlvrs.dotm_user_biometric B ON LD.issue_authority_id = B.user_id
            WHERE A.id IN ({{IDS}}) AND B.signature IS NOT NULL AND LD.id = (SELECT MAX(id) FROM edlvrs.licensedetail WHERE license_id = L.id)
            """
            export_blobphoto(conn, ids_list, SQL_PHOTO, self.output_dirs["photo"], "Photo")
            export_blobsign(conn, ids_list, SQL_SIGN2, self.output_dirs["sign2"], "Signature2")
            export_blobsign(conn, ids_list, SQL_SIGN1, self.output_dirs["sign1"], "Signature1")

            conn.close()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ===== Export CSV =====
    def export_csv(self):
        if self.df is None:
            messagebox.showwarning("No data", "Fetch data first!")
            return
        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV file"
        )
        if file:
            self.df.to_csv(file, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Saved", "CSV exported successfully!")


# ============================================
# RUN GUI
# ============================================
root = tk.Tk()
app = LicenseGUI(root)
root.mainloop()
