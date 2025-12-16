import oracledb
import pandas as pd
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import os
from PIL import Image

# ================= CONFIG =================
USERNAME = "dotm_milan"
DSN = "10.250.252.201/DOTM"


BASE_DATA_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "data")

OUTPUT_DIRS = {
    "photo": os.path.join(BASE_DATA_FOLDER, "Photo"),
    "sign1": os.path.join(BASE_DATA_FOLDER, "Sign1"),
    "sign2": os.path.join(BASE_DATA_FOLDER, "Sign2")
}

# Make folders
os.makedirs(BASE_DATA_FOLDER, exist_ok=True)
for f in OUTPUT_DIRS.values():
    os.makedirs(f, exist_ok=True)



# ================= SQL =================
SQL_LICENSE_INFO = """
SELECT distinct
    A.ID as ProductID,
    A.LASTNAME AS Surname, A.FIRSTNAME || ' ' || A.MIDDLENAME  AS Given_Name,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS Sex, TO_CHAR (a.dateofbirthad,'DD-MM-YYYY') AS Date_of_birth,
    'Government of Nepal' as Nationality,
    (select TO_CHAR(MIN(CAST(issuedate AS DATE)), 'DD-MM-YYYY')  from edlvrs.licensedetail where newlicenseno=ld.newlicenseno) as Date_of_issue,
    TO_CHAR(LD.EXPIRYDATE , 'DD-MM-YYYY')  AS Date_of_expiry,
    
    A.CITIZENSHIPNUMBER as Citizenship_No,
    A.PASSPORTNUMBER as Passport_No,
    '@photo\\'||A.id||'.tif ' as Photo,
    A.MOBILENUMBER as Contact_No,
    (select name from edlvrs.licenseissueoffice WHERE ID=ld.licenseissueoffice_id )AS License_Office,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || A.WITNESSLASTNAME AS FH_Name,
    (SELECT TYPE FROM EDLVRS.BLOODGROUP WHERE ID = A.BLOODGROUP_ID) AS BG,
    (SELECT NAME FROM EDLVRS.DISTRICT WHERE ID = AD.DISTRICT_ID) AS Region,
    
    coalesce(nullif((SELECT NAME FROM EDLVRS.VILLAGEMETROCITY WHERE ID = ad.VILLAGEMETROCITY_ID),'OTHERS'),'')||' '||coalesce(ad.tole,' ')||'-'||coalesce(ad.wardnumber,' ') AS Street_House_Number,
    (Select name from edlvrs.country where id=AD.Country_id)as Country, 
    ' ' as VMT,
    LD.NEWLICENSENO as Driving_License_No,
    
    

    -- CATEGORY FIXED: AGGREGATED ONLY ONCE
    (SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
     FROM edlvrs.licensedetail dl
     JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
     JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
     WHERE dl.newlicenseno = LD.newlicenseno
    ) AS Category,  
    'Sign1\\'||A.id||'.jpg' AS Signature1,
    'Sign2\\'||A.id||'.jpg' As Signature2
    
FROM EDLVRS.LICENSEDETAIL LD
JOIN EDLVRS.LICENSE L
    ON LD.LICENSE_ID = L.ID
JOIN EDLVRS.APPLICANT A
    ON L.APPLICANT_ID = A.ID
LEFT JOIN EDLVRS.ADDRESS AD
    ON A.ID = AD.APPLICANT_ID


WHERE LD.NEWLICENSENO =:license_no



AND LD.expirydate = ( SELECT MAX(expirydate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID
        having ld.expirydate > ADD_MONTHS(SYSDATE, 6)
        )
and ld.issuedate=(
       SELECT MAX(issuedate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID)
and ad.addresstype='PERM'
and l.printed <> 3
  
<-- unchanged -->"""
SQL_PHOTO = """
 SELECT applicant_id, photograph
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({{IDS}})
      AND photograph IS NOT NULL<-- unchanged -->"""


SQL_SIGN2 = """
 SELECT applicant_id, signature
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({{IDS}})
      AND signature IS NOT NULL


<-- unchanged -->"""
SQL_SIGN1 = """

SELECT A.ID, B.signature
    FROM edlvrs.applicant A
    JOIN edlvrs.license L ON A.id = L.applicant_id
    JOIN edlvrs.licensedetail LD ON L.id = LD.license_id
    JOIN edlvrs.dotm_user_biometric B ON LD.issue_authority_id = B.user_id
    WHERE A.id IN ({{IDS}})
      AND B.signature IS NOT NULL
      AND LD.id = (
        SELECT MAX(id) FROM edlvrs.licensedetail WHERE license_id = L.id
      )

<-- unchanged -->"""

# ================= UTIL =================
def save_blob(blob, path):
    with open(path, "wb") as f:
        f.write(blob.read())

def export_blobs(conn, ids, sql, out_dir, ext, log):
    if not ids:
        return
    cur = conn.cursor()
    binds = {f"id{i}": v for i, v in enumerate(ids)}
    sql = sql.replace("{{IDS}}", ",".join(f":id{i}" for i in range(len(ids))))
    cur.execute(sql, binds)
    for aid, blob in cur.fetchall():
        save_blob(blob, os.path.join(out_dir, f"{aid}.{ext}"))
        log(f"Saved {out_dir}\\{aid}.{ext}")
    cur.close()

# ================= LANDING PAGE =================
class LicenseExportLanding(ctk.CTkFrame):

    def __init__(self, parent, on_back):
        super().__init__(parent)
        self.on_back = on_back
        ctk.CTkButton(self, text="← Back", command=self.on_back).pack(pady=10, padx=10, anchor="w")

        # Landing page content
        ctk.CTkLabel(self, text="License Export Page", font=("Arial", 18, "bold")).pack(pady=20)
        ctk.CTkLabel(self, text="Here you can run the license export tool.").pack(pady=10)

        # Example: export button
        ctk.CTkButton(self, text="Run Export").pack(pady=10)
        self.configure(fg_color="#F5F8FF")

        # ---------- HEADER ----------
        header = ctk.CTkFrame(self, fg_color="#1E3A8A", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        

        ctk.CTkLabel(
            header,
            text="DOTM License Export Tool",
            text_color="white",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)

        # ---------- CONTENT ----------
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=20)

        # Logo
      
        #ctk.CTkLabel(body, image=self.logo_img, text="").pack(pady=5)

        # Inputs
        ctk.CTkLabel(body, text="License Numbers").pack(anchor="w")
        self.license_box = ctk.CTkTextbox(body, height=80)
        self.license_box.pack(fill="x", pady=5)

        ctk.CTkLabel(body, text="Oracle Password").pack(anchor="w")
        self.password = ctk.CTkEntry(body, show="*")
        self.password.pack(fill="x", pady=5)

        ctk.CTkButton(
            body,
            text="Run Export",
            height=40,
            command=self.run_export
        ).pack(pady=10)

        ctk.CTkLabel(body, text="Log").pack(anchor="w")
        self.log_box = ctk.CTkTextbox(body, height=200)
        self.log_box.pack(fill="both", expand=True)

    # ---------- LOG ----------
    def log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.update_idletasks()

    # ---------- EXPORT ----------
    def run_export(self):
        licenses = self.license_box.get("1.0", "end").replace(",", " ").split()
        password = self.password.get()

        if not licenses or not password:
            messagebox.showerror("Error", "License numbers and password required")
            return

        try:
            conn = oracledb.connect(user=USERNAME, password=password, dsn=DSN)
            self.log("Connected to Oracle")
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            return

        all_df = []
        applicant_ids = set()

        for lic in licenses:
            df = pd.read_sql(SQL_LICENSE_INFO, conn, params={"license_no": lic})
            if not df.empty:
                all_df.append(df)
                applicant_ids.update(df["PRODUCTID"].astype(int).tolist())
            else:
                self.log(f"No issued record for {lic}")

        if not all_df:
            self.log("No valid data found")
            conn.close()
            return

        final_df = pd.concat(all_df, ignore_index=True)
        csv_path = os.path.join(
            BASE_DATA_FOLDER,
            f"license_export_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )
        final_df.to_csv(csv_path, index=False)
        self.log(f"CSV saved → {csv_path}")

        ids = list(applicant_ids)
        export_blobs(conn, ids, SQL_PHOTO, OUTPUT_DIRS["photo"], "tif", self.log)
        export_blobs(conn, ids, SQL_SIGN2, OUTPUT_DIRS["sign2"], "jpg", self.log)
        export_blobs(conn, ids, SQL_SIGN1, OUTPUT_DIRS["sign1"], "jpg", self.log)

        conn.close()
        self.log("✔ Export completed successfully")
