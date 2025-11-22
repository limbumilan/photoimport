import oracledb
import pandas as pd
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os

# --------------------------------------------------
# YOUR SQL TEMPLATE
# --------------------------------------------------
SQL_QUERY = """
SELECT DISTINCT
    A.ID,
    A.LASTNAME AS SURNAME,
    A.FIRSTNAME || ' ' || A.MIDDLENAME AS NAME,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS GENDER,
    TO_CHAR(a.dateofbirthad,'DD-MM-YYYY') AS DOB,
    A.CITIZENSHIPNUMBER,
    A.PASSPORTNUMBER,
    A.MOBILENUMBER,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || A.WITNESSLASTNAME AS WITNESS,
    (SELECT TYPE FROM EDLVRS.BLOODGROUP WHERE ID = A.BLOODGROUP_ID) AS BG,
    (SELECT NAME FROM EDLVRS.VILLAGEMETROCITY WHERE ID = AD.VILLAGEMETROCITY_ID)
      || ' ' || AD.WARDNUMBER AS ADDRESS,
    (SELECT NAME FROM EDLVRS.DISTRICT WHERE ID = AD.DISTRICT_ID) AS DISTRICT,
    (select name from edlvrs.licenseissueoffice WHERE ID=ld.licenseissueoffice_id )AS LICENSEOFFICE,
    LD.LICENSEISSUEOFFICE_ID,
    (
        SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
        FROM edlvrs.licensedetail dl
        JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
        JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
        WHERE dl.newlicenseno = LD.newlicenseno
    ) AS CATEGORY,
    LD.NEWLICENSENO,
    (SELECT TO_CHAR(MIN(CAST(issuedate AS DATE)), 'DD-MM-YYYY')
        FROM edlvrs.licensedetail
        WHERE newlicenseno = ld.newlicenseno
    ) AS ISSUEDATE,
    TO_CHAR(LD.EXPIRYDATE , 'DD-MM-YYYY')  AS EXPIRYDATE
FROM EDLVRS.LICENSEDETAIL LD
JOIN EDLVRS.LICENSE L ON LD.LICENSE_ID = L.ID
JOIN EDLVRS.APPLICANT A ON L.APPLICANT_ID = A.ID
LEFT JOIN EDLVRS.ADDRESS AD ON A.ID = AD.APPLICANT_ID
WHERE LD.NEWLICENSENO = :license_no
AND LD.expirydate = (
     SELECT MAX(expirydate)
     FROM EDLVRS.LICENSEDETAIL
     WHERE LICENSE_ID = L.ID
)
"""

# --------------------------------------------------
# GUI Application
# --------------------------------------------------
class LicenseExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Oracle License Data Extractor")
        self.root.geometry("720x600")

        self.license_numbers = set()
    def refresh_all(self):
        self.license_numbers.clear()
        self.manual_entry.delete(0, tk.END)

        self.display.delete("1.0", tk.END)
        self.log.delete("1.0", tk.END)

        self.log_msg("Refreshed. You can start new extraction.")


        # Database Fields
        #tk.Label(root, text="Oracle Username:").pack()
        #self.username = tk.Entry(root, width=40)
        #self.username.pack()

        #tk.Label(root, text="Oracle Password:").pack()
        #self.password = tk.Entry(root, width=40, show="*")
        #self.password.pack()

        #tk.Label(root, text="Oracle DSN (host:port/service):").pack()
        #self.dsn = tk.Entry(root, width=40)
        #self.dsn.pack()

        tk.Label(root, text=" ").pack()
        
        

        # Buttons for loading IDs
        tk.Button(root, text="Load from Text File", width=25, command=self.load_text).pack()
        tk.Button(root, text="Load from Excel File", width=25, command=self.load_excel).pack()

        tk.Label(root, text="Or enter license numbers manually (comma separated):").pack()
        self.manual_entry = tk.Entry(root, width=60)
        self.manual_entry.pack()

        tk.Button(root, text="Add Manual Entry", command=self.add_manual).pack()

        tk.Label(root, text=" ").pack()

        # Display loaded license numbers
        tk.Label(root, text="License Numbers Loaded:").pack()
        self.display = scrolledtext.ScrolledText(root, width=80, height=10)
        self.display.pack()

        # Run Button
        tk.Button(root, text="RUN EXTRACTION", bg="green", fg="white",
                  width=30, command=self.run_extraction).pack()
        
        tk.Button(root, text="REFRESH / CLEAR", bg="orange", fg="black",
          width=30, command=self.refresh_all).pack()

        # Status Log
        tk.Label(root, text="Status:").pack()
        self.log = scrolledtext.ScrolledText(root, width=80, height=10)
        self.log.pack()

    # --------------------------------------------------
    def log_msg(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    # --------------------------------------------------
    def refresh_display(self):
        self.display.delete("1.0", tk.END)
        for lic in sorted(self.license_numbers):
            self.display.insert(tk.END, lic + "\n")

    # --------------------------------------------------
    def load_text(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not filename:
            return
        with open(filename, "r") as file:
            for line in file:
                if line.strip():
                    self.license_numbers.add(line.strip())
        self.refresh_display()

    # --------------------------------------------------
    def load_excel(self):
        filename = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if not filename:
            return
        df = pd.read_excel(filename)
        for x in df.iloc[:, 0].dropna().astype(str).tolist():
            self.license_numbers.add(x)
        self.refresh_display()

    # --------------------------------------------------
    def add_manual(self):
        text = self.manual_entry.get().strip()
        if text:
            for x in text.split(","):
                if x.strip():
                    self.license_numbers.add(x.strip())
        self.manual_entry.delete(0, tk.END)
        self.refresh_display()

    # --------------------------------------------------
    def run_extraction(self):
        if not self.license_numbers:
            messagebox.showwarning("No License Numbers", "Please load or enter license numbers.")
            return

        username = "dotm_milan"  #self.username.get().strip()
        password = "123456#AcBd"   #self.password.get().strip()
        dsn = "10.250.252.201/dotm"  #self.dsn.get().strip()

        if not username or not password or not dsn:
            messagebox.showwarning("Missing Fields", "Please enter all Oracle connection details.")
            return

        try:
            self.log_msg("Connecting to Oracle...")
            conn = oracledb.connect(user=username,password= password,dsn= dsn)

            all_data = []

            for lic in self.license_numbers:
                self.log_msg(f"Fetching: {lic}")
                try:
                    df = pd.read_sql(SQL_QUERY, conn, params={"license_no": lic})
                    if not df.empty:
                        all_data.append(df)
                    else:
                        self.log_msg(f"⚠ No data found for {lic}")
                except Exception as e:
                    self.log_msg(f"❌ Error for {lic}: {e}")

            if not all_data:
                self.log_msg("No data extracted!")
                messagebox.showinfo("Done", "No data found for any license numbers.")
                return

            final_df = pd.concat(all_data, ignore_index=True)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_name = f"license_output_{timestamp}.xlsx"
            final_df.to_excel(output_name, index=False)

            self.log_msg(f"SUCCESS → Saved as {output_name}")
            messagebox.showinfo("Success", f"Data successfully extracted.\nSaved as:\n{output_name}")

        except Exception as e:
            self.log_msg(f"Connection Error: {e}")
            messagebox.showerror("Error", str(e))


# --------------------------------------------------
# START GUI
# --------------------------------------------------
root = tk.Tk()
app = LicenseExtractorGUI(root)
root.mainloop()
