import oracledb
import pandas as pd
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import os
from PIL import Image
from baselanding import BaseLanding
from tkinter import messagebox, filedialog, ttk
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


    

class RegularLicenseExportLanding(BaseLanding):
    def __init__(self, parent, on_back):
        super().__init__(parent, on_back=on_back)
        self.configure(fg_color="#F5F8FF")

        self.base_folder = None
        self.output_dirs = {}
        self.df = None

        # ================= Header =================
        header = ctk.CTkFrame(self, fg_color="#1E3A8A", height=60)
        header.pack(fill="x",side="top")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Regular License Export",
            text_color="white",
            font=("Arial", 18, "bold")
        ).pack(side="top", padx=10)

        # ================= Base Folder =================
        folder_frame = ctk.CTkFrame(self)
        folder_frame.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(folder_frame, text="Base Folder:").pack(side="left")
        self.folder_label = ctk.CTkLabel(folder_frame, text="Not selected")
        self.folder_label.pack(side="left", padx=10)
        ctk.CTkButton(
            folder_frame,
            text="Select Folder",
            command=self.select_base_folder
        ).pack(side="left")

        # ================= Login =================
        login_frame = ctk.CTkFrame(self)
        login_frame.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(login_frame, text="Oracle Password:").grid(row=0, column=0, sticky="w")
        self.password_entry = ctk.CTkEntry(login_frame, show="*", width=220)
        self.password_entry.grid(row=0, column=1, padx=10)

        # ================= Filters =================
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=15, pady=6)

        # Office
        ctk.CTkLabel(filter_frame, text="License Office:").grid(row=0, column=0, sticky="w")
        self.office_combo = ctk.CTkComboBox(filter_frame, width=260)
        self.office_combo.grid(row=0, column=1, padx=5)
        ctk.CTkButton(filter_frame, text="Load Offices", command=self.load_offices).grid(row=0, column=2, padx=5)

        # From Date ComboBoxes
        ctk.CTkLabel(filter_frame, text="From Date:").grid(row=1, column=0, sticky="w")
        self.from_day = ctk.CTkComboBox(filter_frame, values=[f"{i:02d}" for i in range(1, 32)], width=60)
        self.from_day.set("01")
        self.from_day.grid(row=1, column=1, sticky="w")
        self.from_month = ctk.CTkComboBox(filter_frame, values=[f"{i:02d}" for i in range(1, 13)], width=60)
        self.from_month.set("01")
        self.from_month.grid(row=1, column=1, padx=(70,0))
        self.from_year = ctk.CTkComboBox(filter_frame, values=[str(y) for y in range(2010,2036)], width=80)
        self.from_year.set("2024")
        self.from_year.grid(row=1, column=1, padx=(140,0))

        # To Date ComboBoxes
        ctk.CTkLabel(filter_frame, text="To Date:").grid(row=2, column=0, sticky="w")
        self.to_day = ctk.CTkComboBox(filter_frame, values=[f"{i:02d}" for i in range(1, 32)], width=60)
        self.to_day.set("01")
        self.to_day.grid(row=2, column=1, sticky="w")
        self.to_month = ctk.CTkComboBox(filter_frame, values=[f"{i:02d}" for i in range(1, 13)], width=60)
        self.to_month.set("01")
        self.to_month.grid(row=2, column=1, padx=(70,0))
        self.to_year = ctk.CTkComboBox(filter_frame, values=[str(y) for y in range(2010,2036)], width=80)
        self.to_year.set("2024")
        self.to_year.grid(row=2, column=1, padx=(140,0))

        # Fetch Button
        ctk.CTkButton(filter_frame, text="Fetch Data", command=self.fetch_data).grid(row=3, column=0, columnspan=3, pady=10)

        # ================= Table =================
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=15, pady=6)

        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # ================= Actions =================
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x",side="bottom", padx=15, pady=6)
        action_frame.pack_propagate(False) 
        #csv button and status label

        ctk.CTkButton(action_frame,
                       text="Export CSV", 
                       command=self.export_csv,
                       width=120,
                     fg_color="#1E90FF",
                     text_color="white"
                       ).pack(side="left",padx=10,pady=5)
        self.status_label = ctk.CTkLabel(action_frame, text="Status: Ready")
        self.status_label.pack(side="left", padx=20)

    # ================= Helper Methods =================   
    def select_base_folder(self):
        folder = filedialog.askdirectory(title="Select Base Folder")
        if not folder:
            return
        self.base_folder = folder
        self.folder_label.configure(text=folder)
        self.output_dirs = {
            "photo": os.path.join(folder, "Photo"),
            "sign1": os.path.join(folder, "Sign1"),
            "sign2": os.path.join(folder, "Sign2"),
        }
        for p in self.output_dirs.values():
            os.makedirs(p, exist_ok=True)

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
            WHERE A.id IN ({{IDS}}) AND B.signature IS NOT NULL AND 
            LD.expirydate = (
            SELECT MAX(expirydate) FROM edlvrs.licensedetail  ld
            WHERE ld.license_id = L.id)
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
