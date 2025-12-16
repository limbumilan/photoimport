import oracledb
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

USERNAME = "dotm_milan"
DSN = "10.250.252.201/DOTM"

SQL_QUERY = """

SELECT DISTINCT
    A.ID as ProductID,
    A.LASTNAME AS Surname,
    A.FIRSTNAME || ' ' || A.MIDDLENAME AS Given_Name,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS Sex,
    TO_CHAR(a.dateofbirthad,'DD-MM-YYYY') AS Date_of_birth,
    'Government of Nepal' as Nationality,
    (SELECT TO_CHAR(MIN(CAST(issuedate AS DATE)), 'DD-MM-YYYY')
     FROM edlvrs.licensedetail
     WHERE newlicenseno = ld.newlicenseno) as Date_of_issue,
    TO_CHAR(LD.EXPIRYDATE , 'DD-MM-YYYY') AS Date_of_expiry,
    A.CITIZENSHIPNUMBER as Citizenship_No,
    A.PASSPORTNUMBER as Passport_No,
    'Photo\\' || A.id || '.jpg' as Photo,
    A.MOBILENUMBER as Contact_No,
    (SELECT name FROM edlvrs.licenseissueoffice WHERE ID=ld.licenseissueoffice_id) AS License_Office,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || A.WITNESSLASTNAME AS FH_Name,
    (SELECT TYPE FROM EDLVRS.BLOODGROUP WHERE ID = A.BLOODGROUP_ID) AS BG,
    (SELECT NAME FROM EDLVRS.DISTRICT WHERE ID = AD.DISTRICT_ID) AS Region,
    COALESCE(NULLIF((SELECT NAME FROM EDLVRS.VILLAGEMETROCITY WHERE ID = ad.VILLAGEMETROCITY_ID),'OTHERS'),'')
        || ' ' || COALESCE(ad.tole,' ') || '-' || COALESCE(ad.wardnumber,' ') AS Street_House_Number,
    (SELECT name FROM edlvrs.country WHERE id = AD.Country_id) AS Country,
    ' ' as VMT,
    LD.NEWLICENSENO as Driving_License_No,
    (SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
     FROM edlvrs.licensedetail dl
     JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
     JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
     WHERE dl.newlicenseno = LD.newlicenseno
    ) AS Category,
    'Sign1\\' || A.id || '.jpg' AS Signature1,
    'Sign2\\' || A.id || '.jpg' AS Signature2
FROM EDLVRS.LICENSEDETAIL LD
JOIN EDLVRS.LICENSE L ON LD.LICENSE_ID = L.ID
JOIN EDLVRS.APPLICANT A ON L.APPLICANT_ID = A.ID
LEFT JOIN EDLVRS.ADDRESS AD ON A.ID = AD.APPLICANT_ID
WHERE LD.NEWLICENSENO IN (
     Select Ld.newlicenseno
     from edlvrs.licensedetail Ld 
     inner join edlvrs.license L
     on ld.license_id=L.id
     inner join edlvrs.licenseissueoffice O
     on Ld.licenseissueoffice_id=o.id
     inner join edlvrs.applicant a
     on L.applicant_id=a.id
     inner join edlvrs.address ad
     on a.id=ad.applicant_id
     where o.name=:office
     AND Ld.issuedate between TO_DATE(:date_from, 'DD-MM-YYYY')
     AND TO_DATE(:date_to, 'DD-MM-YYYY') 
    AND LD.expirydate = (
        SELECT MAX(expirydate)
        FROM EDLVRS.LICENSEDETAIL
         WHERE LICENSE_ID = L.ID
         AND ld.expirydate > ADD_MONTHS(SYSDATE, 6)
        )
       AND ld.issuedate = (
        SELECT MAX(issuedate)
       FROM EDLVRS.LICENSEDETAIL
       WHERE LICENSE_ID = L.ID
)
AND ad.addresstype = 'PERM'
AND l.printed <> 3
 

)
AND LD.expirydate = (
    SELECT MAX(expirydate)
    FROM EDLVRS.LICENSEDETAIL
    WHERE LICENSE_ID = L.ID
      AND ld.expirydate > ADD_MONTHS(SYSDATE, 6)
)
AND ld.issuedate = (
    SELECT MAX(issuedate)
    FROM EDLVRS.LICENSEDETAIL
    WHERE LICENSE_ID = L.ID
)
AND ad.addresstype = 'PERM'
AND l.printed <> 3






"""

class LicenseGUI:
    def __init__(self, root):
        self.root = root
        root.title("Driving License Data Fetcher")
        root.geometry("800x500")

        # Password frame
        login_frame = tk.LabelFrame(root, text="Oracle Login", padx=10, pady=10)
        login_frame.pack(fill="x")
        tk.Label(login_frame, text="Password:").grid(row=0, column=0)
        self.password_entry = tk.Entry(login_frame, show="*")
        self.password_entry.grid(row=0, column=1)

        # Filters frame
        filter_frame = tk.LabelFrame(root, text="Filters", padx=10, pady=10)
        filter_frame.pack(fill="x")

        tk.Label(filter_frame, text="Select Office:").grid(row=0, column=0)
        self.office_combo = ttk.Combobox(filter_frame, width=40)
        self.office_combo.grid(row=0, column=1)
        tk.Button(filter_frame, text="Load Offices", command=self.load_offices).grid(row=0, column=2, padx=5)

        # Date pickers
        tk.Label(filter_frame, text="From Date:").grid(row=1, column=0)
        self.from_day = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1, 32)], width=5)
        self.from_day.grid(row=1, column=1)
        self.from_day.set("01")
        self.from_month = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1, 13)], width=5)
        self.from_month.grid(row=1, column=2)
        self.from_month.set("01")
        self.from_year = ttk.Combobox(filter_frame, values=[str(y) for y in range(2010, 2035)], width=7)
        self.from_year.grid(row=1, column=3)
        self.from_year.set("2024")

        tk.Label(filter_frame, text="To Date:").grid(row=2, column=0)
        self.to_day = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1, 32)], width=5)
        self.to_day.grid(row=2, column=1)
        self.to_day.set("01")
        self.to_month = ttk.Combobox(filter_frame, values=[f"{i:02d}" for i in range(1, 13)], width=5)
        self.to_month.grid(row=2, column=2)
        self.to_month.set("01")
        self.to_year = ttk.Combobox(filter_frame, values=[str(y) for y in range(2010, 2035)], width=7)
        self.to_year.grid(row=2, column=3)
        self.to_year.set("2024")

        # Fetch button
        tk.Button(filter_frame, text="Fetch Data", command=self.fetch_data).grid(row=3, column=0, columnspan=4, pady=10)

        # Table
        self.tree = ttk.Treeview(root)
        self.tree.pack(fill="both", expand=True)

        # Export
        tk.Button(root, text="Export to Excel", command=self.export_excel).pack(pady=10)

        self.df = None

    def load_offices(self):
        try:
            pwd = self.password_entry.get()
            conn = oracledb.connect(user=USERNAME, password=pwd, dsn=DSN)
            cur = conn.cursor()
            cur.execute("SELECT name FROM edlvrs.licenseissueoffice WHERE name NOT LIKE '-%' ORDER BY name")
            offices = [row[0] for row in cur.fetchall()]
            self.office_combo["values"] = offices
            messagebox.showinfo("Success", "Offices loaded!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

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
            cursor = conn.cursor()
            cursor.execute(SQL_QUERY, {"office": office, "date_from": date_from, "date_to": date_to})

            rows = cursor.fetchall()
            if not rows:
                messagebox.showinfo("No Data", "No records found for the selected filters.")
                return

            cols = [col[0] for col in cursor.description]
            self.df = pd.DataFrame(rows, columns=cols)

            # Load table
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = cols
            self.tree["show"] = "headings"
            for c in cols:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=150)
            for r in rows:
                self.tree.insert("", "end", values=r)

            messagebox.showinfo("Done", f"Fetched {len(rows)} records")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_excel(self):
        if self.df is None:
            messagebox.showwarning("No data", "Fetch data first!")
            return
        file = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if file:
            self.df.to_excel(file, index=False)
            messagebox.showinfo("Saved", "Excel exported successfully!")

root = tk.Tk()
app = LicenseGUI(root)
root.mainloop()
