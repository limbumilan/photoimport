
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

#BASE_DATA_FOLDER  # Ask user to choose base folder
BASE_DATA_FOLDER = filedialog.askdirectory(title="Select Base Data Folder")
if not BASE_DATA_FOLDER:
    messagebox.showerror("Error", "No folder selected!")
    raise SystemExit("No folder selected")

OUTPUT_DIRS = {
    "photo": os.path.join(BASE_DATA_FOLDER, "Photo"),
    "sign1": os.path.join(BASE_DATA_FOLDER, "Sign1"),
    "sign2": os.path.join(BASE_DATA_FOLDER, "Sign2")
}

# Create folders if they don’t exist
for folder in OUTPUT_DIRS.values():
    os.makedirs(folder, exist_ok=True)


OUTPUT_DIRS = {
    "photo": os.path.join(BASE_DATA_FOLDER, "Photo"),
    "sign1": os.path.join(BASE_DATA_FOLDER, "Sign1"),
    "sign2": os.path.join(BASE_DATA_FOLDER, "Sign2")
}


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
AND LD.licenseissueoffice_id = (SELECT id FROM edlvrs.licenseissueoffice WHERE name=:office)
AND LD.expirydate = (SELECT MAX(expirydate) FROM EDLVRS.LICENSEDETAIL WHERE LICENSE_ID = L.ID AND ld.expirydate > ADD_MONTHS(SYSDATE, 6))
AND LD.issuedate = (SELECT MAX(issuedate) FROM EDLVRS.LICENSEDETAIL WHERE LICENSE_ID = L.ID)
AND L.printed <> 3
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
        root.title("Driving License Data Fetcher")
        root.geometry("1000x600")

        # LOGIN
        login_frame = tk.LabelFrame(root, text="Oracle Login", padx=10, pady=10)
        login_frame.pack(fill="x")
        tk.Label(login_frame, text="Password:").grid(row=0, column=0)
        self.password_entry = tk.Entry(login_frame, show="*")
        self.password_entry.grid(row=0, column=1)

        # FILTERS
        filter_frame = tk.LabelFrame(root, text="Filters", padx=10, pady=10)
        filter_frame.pack(fill="x")
        tk.Label(filter_frame, text="Select Office:").grid(row=0, column=0)
        self.office_combo = ttk.Combobox(filter_frame, width=40)
        self.office_combo.grid(row=0, column=1)
        tk.Button(filter_frame, text="Load Offices", command=self.load_offices).grid(row=0, column=2, padx=5)

        tk.Label(filter_frame, text="From Date:").grid(row=1, column=0)
        self.from_day = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,32)], width=5)
        self.from_day.grid(row=1, column=1)
        self.from_day.set("01")
        self.from_month = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,13)], width=5)
        self.from_month.grid(row=1, column=2)
        self.from_month.set("01")
        self.from_year = ttk.Combobox(filter_frame, values=[str(y) for y in range(2010,2035)], width=7)
        self.from_year.grid(row=1, column=3)
        self.from_year.set("2024")

        tk.Label(filter_frame, text="To Date:").grid(row=2, column=0)
        self.to_day = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,32)], width=5)
        self.to_day.grid(row=2, column=1)
        self.to_day.set("01")
        self.to_month = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1,13)], width=5)
        self.to_month.grid(row=2, column=2)
        self.to_month.set("01")
        self.to_year = ttk.Combobox(filter_frame, values=[str(y) for y in range(2010,2035)], width=7)
        self.to_year.grid(row=2, column=3)
        self.to_year.set("2024")

        tk.Button(filter_frame, text="Fetch Data", command=self.fetch_data).grid(row=3, column=0, columnspan=4, pady=10)

        # TABLE
        self.tree = ttk.Treeview(root)
        self.tree.pack(fill="both", expand=True)
        tk.Button(root, text="Export", command=self.export_csv).pack(pady=10)

        self.df = None

    # Load office names
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

    # Fetch data and export blobs
    def fetch_data(self):
        try:
            pwd = self.password_entry.get().strip()
            office = self.office_combo.get().strip()
            date_from = f"{self.from_day.get()}-{self.from_month.get()}-{self.from_year.get()}"
            date_to = f"{self.to_day.get()}-{self.to_month.get()}-{self.to_year.get()}"

            if not office:
                messagebox.showwarning("Warning", "Select an office first!")
                return

            conn = oracledb.connect(user=USERNAME, password=pwd, dsn=DSN)
            df = pd.read_sql(SQL_LICENSE_INFO, conn, params={"office": office, "date_from": date_from, "date_to": date_to})

            if df.empty:
                messagebox.showinfo("No Data", "No records found for selected filters.")
                return

            self.df = df

            # Show in table
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = df.columns.tolist()
            self.tree["show"] = "headings"
            for c in df.columns:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=150)
            for row in df.itertuples(index=False):
                self.tree.insert("", "end", values=row)

            messagebox.showinfo("Done", f"Fetched {len(df)} records")

            # Export blobs
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
            export_blobphoto(conn, ids_list, SQL_PHOTO, OUTPUT_DIRS["photo"], "Photo")
            export_blobsign(conn, ids_list, SQL_SIGN2, OUTPUT_DIRS["sign2"], "Signature2")
            export_blobsign(conn, ids_list, SQL_SIGN1, OUTPUT_DIRS["sign1"], "Signature1")

            conn.close()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Export Excel
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
            self.df.to_csv(file, index=False)
            messagebox.showinfo("Saved", "csv exported successfully!")

# ============================================
# RUN GUI
# ============================================
root = tk.Tk()
app = LicenseGUI(root)
root.mainloop()
