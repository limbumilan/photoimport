
import oracledb
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
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

    
    (SELECT MAX(lio.name) KEEP (DENSE_RANK FIRST ORDER BY ld2.issuedate)
 FROM edlvrs.licensedetail ld2
 JOIN edlvrs.licenseissueoffice lio 
   ON lio.id = ld2.licenseissueoffice_id
 WHERE ld2.newlicenseno = ld.newlicenseno
) AS License_Office,
    


    
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
WHERE name=:office 
)

AND LD.expirydate = (
SELECT MAX(expirydate) 
FROM EDLVRS.LICENSEDETAIL ld2
WHERE ld2.LICENSE_ID = L.ID 
AND ld2.expirydate > ADD_MONTHS(SYSDATE, 12))

AND LD.issuedate = (
SELECT MAX(issuedate) 
FROM EDLVRS.LICENSEDETAIL ld2
WHERE ld2.LICENSE_ID = L.ID 
)


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





def export_blobs(conn, ids, sql_template, out_dir, extension, valid_ids, gui=None, task_weight=1, batch_size=500):
    import os
    from math import ceil

    if not ids:
        return set()

    processed_ids = set()
    total_records = len(ids)
    total_batches = ceil(total_records / batch_size)

    for batch_index in range(total_batches):

        batch_ids = ids[batch_index * batch_size:(batch_index + 1) * batch_size]

        placeholders = ",".join([f":id{i}" for i in range(len(batch_ids))])
        bind_vars = {f"id{i}": val for i, val in enumerate(batch_ids)}

        sql = sql_template.replace("{{IDS}}", placeholders)

        cursor = conn.cursor()

        batch_exported = 0
        batch_skipped = 0

        try:
            cursor.execute(sql, bind_vars)

            for aid, blob in cursor:

                if aid not in valid_ids:
                    continue

                file_path = os.path.join(out_dir, f"{aid}{extension}")

                # SKIP
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    batch_skipped += 1
                    processed_ids.add(aid)

                    if gui:
                        gui.done_tasks = min(gui.done_tasks + task_weight, gui.total_tasks)
                    continue

                # EXPORT
                blob_data = blob.read() if hasattr(blob, "read") else blob

                with open(file_path, "wb") as f:
                    f.write(blob_data)

                batch_exported += 1
                processed_ids.add(aid)

                if gui:
                    gui.done_tasks = min(gui.done_tasks + task_weight, gui.total_tasks)

        finally:
            cursor.close()

        # ✅ PRINT TO CONSOLE
        print(f"[Batch {batch_index+1}/{total_batches}] Exported: {batch_exported}, Skipped: {batch_skipped}")

        # ✅ UPDATE UI
        if gui:
            gui.update_progress(
                gui.done_tasks,
                text=f"Batch {batch_index+1}/{total_batches} | Exported: {batch_exported} | Skipped: {batch_skipped}"
            )

    return processed_ids











# ============================================
# GUI CLASS
# ============================================
class LicenseGUI:
    
    def __init__(self, root):
        
        self.root = root
        root.title("Demo Personalization ware")
        root.geometry("1100x650")
        root.configure(bg="#87CEEB")  # sky blue background
        self.btn_bg="#4682B4"
        self.btn_fg="white"

        self.base_folder = None
        self.output_dirs = {}
        self.df = None
        self.done_tasks=0
        

        # ===== Base Folder Selection =====
        folder_frame = tk.Frame(root, bg="#87CEEB")
        folder_frame.pack(fill="x", pady=5)
        tk.Label(folder_frame, text="Base Data Folder:", bg="#87CEEB", fg="#003366", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.folder_label = tk.Label(folder_frame, text="Not selected", fg="#003366", bg="#87CEEB", font=("Arial", 10))
        self.folder_label.pack(side="left", padx=5)
        tk.Button(folder_frame, text="Select Folder", command=self.select_base_folder, bg=self.btn_bg, fg=self.btn_fg).pack(side="left", padx=5)

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
        tk.Button(filter_frame, text="Load Offices", command=self.load_offices, bg=self.btn_bg, fg=self.btn_fg).grid(row=0, column=2, padx=5)

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

        # ===== BUTTON FRAME (GRID ONLY) =====
        button_frame = tk.Frame(filter_frame, bg="#87CEEB")
        button_frame.grid(row=3, column=0, columnspan=4, pady=15)

        tk.Button(
        button_frame,
        text="Fetch Data",
        command=lambda: threading.Thread(target=self.fetch_data).start(),
        bg=self.btn_bg,
        fg=self.btn_fg,
       width=15
        ).grid(row=0, column=0, padx=10)

        tk.Button(
        button_frame,
        text="Export Office Report",
        command=self.export_office_report,
        bg=self.btn_bg,
        fg=self.btn_fg,
        width=18
        ).grid(row=0, column=1, padx=10)



        
        # ===== Table =====
        table_frame = tk.Frame(root, bg="#87CEEB")
        table_frame.pack(fill="both", expand=True, padx=8, pady=5)
        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.pack(side="top", fill="both", expand=True)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(xscrollcommand=hsb.set)

        # ===== Actions =====
        action_frame = tk.Frame(root, bg="#87CEEB")
        action_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(action_frame, text="Export CSV", command=self.export_csv, bg=self.btn_bg, fg=self.btn_fg).pack(side="left", padx=5)
        self.status_label = tk.Label(action_frame, text="Status: Ready", anchor="w", bg="#87CEEB", fg="#003366")
        self.status_label.pack(side="left", padx=20)
        tk.Button(action_frame, text="Clear Table", command=self.clear_table, bg=self.btn_bg, fg=self.btn_fg).pack(side="left", padx=5)


        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
    "Custom.Horizontal.TProgressbar",
        troughcolor="#87CEEB",   # match your UI background
        background="#00BFFF",
        bordercolor="#87CEEB",
        lightcolor="#00BFFF",
       darkcolor="#00BFFF"
                             )

        
        self.progress = ttk.Progressbar(
        action_frame,
        orient="horizontal",
        length=300,
        mode="determinate",   # important for your use case
        style="TProgressbar")

        self.progress.pack(side="left", padx=10)

        self.percent_label = tk.Label(
        action_frame,
        text="0%",
        bg="#87CEEB",
        fg="#003366",
        font=("Arial", 10, "bold")
        )
        self.percent_label.pack(side="left", padx=5)
        

    

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
            self.office_combo["values"] =["All"]+ offices
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
      date_to   = f"{self.to_day.get()}-{self.to_month.get()}-{self.to_year.get()}"

      if not office:
        messagebox.showwarning("Warning", "Select an office first!")
        return

    # UI START
      self.progress.config(mode="indeterminate")
      self.progress.start(30)
      self.status_label.config(text="Connecting...")
      self.percent_label.config(text="0%")
      self.root.update_idletasks()

      try:
        self.office = office
        self.date_from = date_from
        self.date_to = date_to

        conn = oracledb.connect(user=USERNAME, password=pwd, dsn=DSN)

        self.status_label.config(text="Fetching data...")
        self.root.update_idletasks()

        # 🔥 SWITCH LOGIC
        if office == "All":
            df = self.fetch_all_offices(conn, date_from, date_to)
        else:
            df = pd.read_sql(SQL_LICENSE_INFO, conn, params={
                "office": office,
                "date_from": date_from,
                "date_to": date_to
            })

        if df is None or df.empty:
            messagebox.showinfo("No Data", "No records found.")
            return

        # ===== FILTERING =====
        filtered_out_ids = []

        mask1 = df["CITIZENSHIP_NO"].str.contains("ANUSHUCHI", na=False)
        mask2 = (df["GIVEN_NAME"].str.len() + df["SURNAME"].str.len()) >= 30
        mask3 = ~df["DRIVING_LICENSE_NO"].astype(str).str.match(r'^\d{2}-\d{2}-\d{8}$')
        mask4 = df["CATEGORY"].str.len() < 1

        filtered_out_ids.extend(df.loc[mask1 | mask2 | mask3 | mask4, "PRODUCTID"].tolist())

        df = df[~mask1 & ~mask2 & ~mask3 & ~mask4]
        df = df.drop_duplicates(subset="PRODUCTID")

        self.df = df

        if filtered_out_ids:
            messagebox.showwarning(
                "Skipped",
                f"{len(filtered_out_ids)} records skipped"
            )

        # ===== TABLE =====
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = df.columns.tolist()
        self.tree["show"] = "headings"

        for c in df.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140)

        for row in df.itertuples(index=False):
            self.tree.insert("", "end", values=row)

        self.status_label.config(text=f"Fetched {len(df)} records")

        # ===== PROCESS IDS =====
        ids_list = df["PRODUCTID"].dropna().astype(int).tolist()
        valid_ids = set(ids_list)

        ids_to_process = []

        for aid in ids_list:
            photo = os.path.join(self.output_dirs["photo"], f"{aid}.tif")
            sign1 = os.path.join(self.output_dirs["sign1"], f"{aid}.jpg")
            sign2 = os.path.join(self.output_dirs["sign2"], f"{aid}.jpg")

            if not (
                os.path.exists(photo) and os.path.exists(sign1) and os.path.exists(sign2)
            ):
                ids_to_process.append(aid)

        if not ids_to_process:
            messagebox.showinfo("Done", "All files already exist ✅")
            return

        # ===== EXPORT =====
        SQL_PHOTO = """
        SELECT applicant_id, photograph FROM edlvrs.applicant_biometric 
        WHERE applicant_id IN ({{IDS}}) AND photograph IS NOT NULL
        """

        SQL_SIGN2 = """
        SELECT applicant_id, signature FROM edlvrs.applicant_biometric 
        WHERE applicant_id IN ({{IDS}}) AND signature IS NOT NULL
        """

        SQL_SIGN1 = """
         SELECT A.ID, B.signature 
          FROM edlvrs.applicant A
          JOIN edlvrs.license L ON A.id = L.applicant_id
          JOIN edlvrs.licensedetail LD ON L.id = LD.license_id
          JOIN edlvrs.dotm_user_biometric B ON LD.issue_authority_id = B.user_id
          WHERE A.id IN ({{IDS}}) 
          AND B.signature IS NOT NULL 
          AND LD.expirydate = (
            SELECT MAX(ld3.expirydate) FROM edlvrs.licensedetail ld3 WHERE ld3.license_id = L.id
          )
          """

       

        total = len(ids_to_process) * 3

        self.progress.stop()
        self.progress.config(mode="determinate", maximum=total, value=0)
        self.done_tasks = 0
        self.total_tasks = total

        export_blobs(conn, ids_to_process, SQL_PHOTO, self.output_dirs["photo"], ".tif", valid_ids, self)
        export_blobs(conn, ids_to_process, SQL_SIGN2, self.output_dirs["sign2"], ".jpg", valid_ids, self)
        export_blobs(conn, ids_to_process, SQL_SIGN1, self.output_dirs["sign1"], ".jpg", valid_ids, self)

        conn.close()

        self.status_label.config(text="Completed ✅")
        messagebox.showinfo("Done", "Extraction completed successfully!")

      except Exception as e:
        messagebox.showerror("Error", str(e))

    def export_office_report(self):
      if self.df is None or self.df.empty:
        messagebox.showwarning("No Data", "Fetch data first!")
        return

    # Ensure required columns exist
      required_cols = ["LAST_TRANSACTION_LICENSE_OFFICE_ID", "LAST_TRANSACTION_LICENSE_OFFICE"]
      for col in required_cols:
        if col not in self.df.columns:
            messagebox.showerror("Error", f"{col} not found in data!")
            return

    # ===== GROUP DATA =====
      report_df = (
        self.df
        .groupby(
            ["LAST_TRANSACTION_LICENSE_OFFICE_ID", "LAST_TRANSACTION_LICENSE_OFFICE"]
        )
        .size()
        .reset_index(name="COUNT")
        .sort_values(by="COUNT", ascending=False)
    )

    # ===== ADD TOTAL ROW =====
      total_value = report_df["COUNT"].sum()

      total_row = pd.DataFrame({
        "LAST_TRANSACTION_LICENSE_OFFICE_ID": ["TOTAL"],
        "LAST_TRANSACTION_LICENSE_OFFICE": [""],
        "COUNT": [total_value]
    })

      report_df = pd.concat([report_df, total_row], ignore_index=True)

    # ===== DEFAULT FILE NAME =====
      date_from = getattr(self, "date_from", "start")
      date_to = getattr(self, "date_to", "end")

      def clean(x):
        return str(x).replace("/", "-").replace(":", "-").replace(" ", "_")

      default_name = f"office_report_{clean(date_from)}_to_{clean(date_to)}.csv"

    # ===== SAVE FILE =====
      file = filedialog.asksaveasfilename(
        defaultextension=".csv",
        initialfile=default_name,
        filetypes=[("CSV files", "*.csv")],
        title="Save Office Report"
      )

      if file:
        report_df.to_csv(file, index=False, encoding="utf-8-sig")
        messagebox.showinfo("Saved", f"Report exported successfully!\n{file}")
    
    
    # ===== Export CSV =====
    def export_csv(self):
        if self.df is None:
            messagebox.showwarning("No data", "Fetch data first!")
            return

        
        office = getattr(self, "office", "office")
        date_from = getattr(self, "date_from", "start")
        date_to = getattr(self, "date_to", "end")

        def clean(x):
            return str(x).replace("/", "-").replace(":", "-").replace(" ", "_")


        
        default_name = f"{clean(office)}_from_{clean(date_from)}_to_{clean(date_to)}.csv"
        
        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV file"
        )
        if file:
            self.df.to_csv(file, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Saved", f"CSV exported successfully!\n{file}")
            
            
    def clear_table(self):
        confirm = messagebox.askyesno("Confirm", "Clear all data from table?")
        if confirm:
           self.tree.delete(*self.tree.get_children())
           self.df = None
           self.status_label.config(text="Table cleared")

           
    def update_progress(self, value, text=""):
         max_val = float(self.progress.cget("maximum") or 1)

    # clamp value so it never exceeds max
         value = min(value, max_val)

         percent = int((value / max_val) * 100)

         def _update():
            self.progress["value"] = value
            self.percent_label.config(text=f"{percent}%")
            self.status_label.config(text=f"{text} | {value}/{int(max_val)}")

            

         self.root.after(0, _update)
    
    


    def fetch_all_offices(self, conn, date_from, date_to):



        SQL_ALL = """
SELECT
    A.ID AS PRODUCTID,
    A.LASTNAME AS SURNAME,
    A.FIRSTNAME || ' ' || NVL(A.MIDDLENAME,'') AS GIVEN_NAME,

    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS SEX,

    TO_CHAR(A.DATEOFBIRTHAD,'DD-MM-YYYY') AS DATE_OF_BIRTH,
    'Government of Nepal' AS NATIONALITY,

    -- FIRST ISSUE DATE
    (SELECT TO_CHAR(MIN(ISSUEDATE),'DD-MM-YYYY')
     FROM edlvrs.licensedetail
     WHERE newlicenseno = ld.newlicenseno) AS DATE_OF_ISSUE,

    TO_CHAR(LD.EXPIRYDATE, 'DD-MM-YYYY') AS DATE_OF_EXPIRY,

    A.CITIZENSHIPNUMBER AS CITIZENSHIP_NO,
    A.PASSPORTNUMBER AS PASSPORT_NO,

    '@photo\\' || A.ID || '.tif' AS PHOTO,
    A.MOBILENUMBER AS CONTACT_NO,

    -- FIRST LICENSE OFFICE
    (SELECT MAX(lio.name) KEEP (DENSE_RANK FIRST ORDER BY ld2.issuedate)
     FROM edlvrs.licensedetail ld2
     JOIN edlvrs.licenseissueoffice lio
       ON lio.id = ld2.licenseissueoffice_id
     WHERE ld2.newlicenseno = ld.newlicenseno
    ) AS LICENSE_OFFICE,

    A.WITNESSFIRSTNAME || ' ' ||
    NVL(A.WITNESSMIDDLENAME,'') || ' ' ||
    NVL(A.WITNESSLASTNAME,'') AS FH_NAME,

    (SELECT TYPE FROM edlvrs.bloodgroup WHERE ID = A.BLOODGROUP_ID) AS BG,

    (SELECT name FROM edlvrs.district WHERE ID = AD.district_id) AS REGION,

    COALESCE(NULLIF(
        (SELECT NAME FROM edlvrs.villagemetrocity WHERE ID = AD.villagemetrocity_id),
        'OTHERS'
    ), '') || ' ' || COALESCE(AD.tole,'') || '-' || COALESCE(AD.wardnumber,'') AS STREET_HOUSE_NUMBER,

    (SELECT name FROM edlvrs.country WHERE id = AD.country_id) AS COUNTRY,

    LD.NEWLICENSENO AS DRIVING_LICENSE_NO,

    -- CATEGORY LIST
    (SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
     FROM edlvrs.licensedetail dl
     JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
     JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
     WHERE dl.newlicenseno = LD.newlicenseno
    ) AS CATEGORY,

    -- LAST TRANSACTION OFFICE NAME
    (SELECT MAX(lio1.name) KEEP (DENSE_RANK LAST ORDER BY ld3.issuedate)
     FROM edlvrs.licensedetail ld3
     JOIN edlvrs.licenseissueoffice lio1
       ON lio1.id = ld3.licenseissueoffice_id
     WHERE ld3.license_id = L.id
    ) AS LAST_TRANSACTION_LICENSE_OFFICE,

    -- LAST TRANSACTION OFFICE ID
    (SELECT MAX(ld4.licenseissueoffice_id) KEEP (DENSE_RANK LAST ORDER BY ld4.issuedate)
     FROM edlvrs.licensedetail ld4
     WHERE ld4.license_id = L.id
    ) AS LAST_TRANSACTION_LICENSE_OFFICE_ID

FROM edlvrs.licensedetail LD
JOIN edlvrs.license L ON LD.license_id = L.id
JOIN edlvrs.applicant A ON L.applicant_id = A.id
LEFT JOIN edlvrs.address AD
    ON A.id = AD.applicant_id AND AD.addresstype = 'PERM'

WHERE LD.issuedate BETWEEN TO_DATE(:date_from,'DD-MM-YYYY')
                        AND TO_DATE(:date_to,'DD-MM-YYYY')

-- LATEST VALID RECORDS ONLY
AND LD.expirydate = (
    SELECT MAX(expirydate)
    FROM EDLVRS.LICENSEDETAIL ld2
    WHERE ld2.LICENSE_ID = L.ID
    AND ld2.expirydate > ADD_MONTHS(SYSDATE, 12)
)

AND LD.issuedate = (
    SELECT MAX(issuedate)
    FROM EDLVRS.LICENSEDETAIL ld2
    WHERE ld2.LICENSE_ID = L.ID
)

AND AD.addresstype = 'PERM'
AND L.printed = '0'
AND L.licensestatus = 'VALID'
AND LD.accountstatus = 'VALID'
"""

       
    

        df = pd.read_sql(SQL_ALL, conn, params={
        "date_from": date_from,
        "date_to": date_to
    })

    # 🔥 Normalize column names (important for your filters)
        df.columns = [c.upper() for c in df.columns]

        return df




def process_all_offices(self, conn, df):

    import os

    office_map = {}

    # ===== GROUP IDS BY OFFICE =====
    for _, row in df.iterrows():

        aid = int(row["PRODUCTID"])

        office_name = str(row["LAST_TRANSACTION_LICENSE_OFFICE"]).replace(" ", "_")
        office_id = str(row["LAST_TRANSACTION_LICENSE_OFFICE_ID"])

        key = f"{office_name}_{office_id}"

        office_map.setdefault(key, []).append(aid)

    # ===== CREATE OFFICE FOLDERS =====
    office_dirs = {}

    for key in office_map:

        base = os.path.join(self.base_folder, key)

        office_dirs[key] = {
            "photo": os.path.join(base, "photo"),
            "sign1": os.path.join(base, "sign1"),
            "sign2": os.path.join(base, "sign2")
        }

        for path in office_dirs[key].values():
            os.makedirs(path, exist_ok=True)

    # ===== SQL (UNCHANGED) =====
    SQL_PHOTO = """
    SELECT applicant_id, photograph FROM edlvrs.applicant_biometric 
    WHERE applicant_id IN ({{IDS}}) AND photograph IS NOT NULL
    """

    SQL_SIGN2 = """
    SELECT applicant_id, signature FROM edlvrs.applicant_biometric 
    WHERE applicant_id IN ({{IDS}}) AND signature IS NOT NULL
    """

    SQL_SIGN1 = """
    SELECT A.ID, B.signature 
    FROM edlvrs.applicant A
    JOIN edlvrs.license L ON A.id = L.applicant_id
    JOIN edlvrs.licensedetail LD ON L.id = LD.license_id
    JOIN edlvrs.dotm_user_biometric B ON LD.issue_authority_id = B.user_id
    WHERE A.id IN ({{IDS}})
    AND B.signature IS NOT NULL 
    AND LD.expirydate = (
      SELECT MAX(ld3.expirydate) FROM edlvrs.licensedetail ld3 WHERE ld3.license_id = L.id
    )
    """

    # ===== PROGRESS =====
    total = sum(len(v) for v in office_map.values()) * 3

    self.progress.stop()
    self.progress.config(mode="determinate", maximum=total, value=0)
    self.done_tasks = 0

    # ===== EXPORT PER OFFICE =====
    for office_key, ids_list in office_map.items():

        dirs = office_dirs[office_key]
        valid_ids = set(ids_list)

        export_blobs(conn, ids_list, SQL_PHOTO, dirs["photo"], ".tif", valid_ids, self)
        export_blobs(conn, ids_list, SQL_SIGN2, dirs["sign2"], ".jpg", valid_ids, self)
        export_blobs(conn, ids_list, SQL_SIGN1, dirs["sign1"], ".jpg", valid_ids, self)

    conn.close()

    self.status_label.config(text="Completed (All Offices) ✅")
    messagebox.showinfo("Done", "All offices extraction completed successfully!")


    


   

# ============================================
# RUN GUI
# ============================================
root = tk.Tk()
app = LicenseGUI(root)
root.mainloop()
