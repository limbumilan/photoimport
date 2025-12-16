import oracledb
import pandas as pd
from datetime import datetime
import os
import getpass
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext


# ============================================
# CONFIG
# ============================================
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


# ============================================
# SQL
# ============================================
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
  
        
"""

SQL_PHOTO = """
    SELECT applicant_id, photograph
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({{IDS}})
      AND photograph IS NOT NULL
"""

SQL_SIGN2 = """
    SELECT applicant_id, signature
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({{IDS}})
      AND signature IS NOT NULL
"""

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
"""


# ============================================
# Helper Functions
# ============================================
def log(text):
    log_box.insert(tk.END, text + "\n")
    log_box.see(tk.END)


def save_blob(blob, file_path):
    with open(file_path, "wb") as f:
        f.write(blob.read())


def export_blobsphoto(conn, ids, sql_template, output_dir, label):
    if not ids:
        log(f"No IDs for {label}.")
        return

    cursor = conn.cursor()
    binds = {f"id{i}": val for i, val in enumerate(ids)}
    placeholders = ",".join(f":id{i}" for i in range(len(ids)))

    sql = sql_template.replace("{{IDS}}", placeholders)
    cursor.execute(sql, binds)

    rows = cursor.fetchall()
    log(f"{label}: {len(rows)} found")

    for aid, blob in rows:
        path = os.path.join(output_dir, f"{aid}.tif")
        save_blob(blob, path)
        log(f"{label} saved → {path}")

    cursor.close()

def export_blobssign(conn, ids, sql_template, output_dir, label):
    if not ids:
        log(f"No IDs for {label}.")
        return

    cursor = conn.cursor()
    binds = {f"id{i}": val for i, val in enumerate(ids)}
    placeholders = ",".join(f":id{i}" for i in range(len(ids)))

    sql = sql_template.replace("{{IDS}}", placeholders)
    cursor.execute(sql, binds)

    rows = cursor.fetchall()
    log(f"{label}: {len(rows)} found")

    for aid, blob in rows:
        path = os.path.join(output_dir, f"{aid}.jpg")
        save_blob(blob, path)
        log(f"{label} saved → {path}")

    cursor.close()

# ============================================
# Processing Thread
# ============================================
def start_processing():
    thread = threading.Thread(target=run_main_process)
    thread.start()


def run_main_process():
    license_input = entry_license.get().strip()
    if not license_input:
        messagebox.showwarning("Missing Input", "Enter license numbers.")
        return

    license_numbers = [x.strip() for x in license_input.replace(",", " ").split() if x.strip()]

    password = entry_password.get().strip()
    if not password:
        messagebox.showwarning("Missing Password", "Enter Oracle password.")
        return

    try:
        conn = oracledb.connect(user=USERNAME, password=password, dsn=DSN)
        log("Connected to Oracle.")
    except Exception as e:
        messagebox.showerror("Connection Failed", str(e))
        return

    all_data = []
    applicant_ids = set()

    for lic in license_numbers:
        log(f"Fetching license → {lic}")
        try:
            df = pd.read_sql(SQL_LICENSE_INFO, conn, params={"license_no": lic})
        except Exception as e:
            log(f"Error fetching {lic}: {e}")
            continue

        if df.empty:
            log(f"No data for {lic}")
            continue

        ids = df["PRODUCTID"].dropna().astype(int).tolist()
        applicant_ids.update(ids)
        all_data.append(df)

        log(f"Applicant IDs: {ids}")

    if not all_data:
        log("No valid license records found.")
        return

    csv_path = os.path.join(
        BASE_DATA_FOLDER,
        f"license_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    final_df = pd.concat(all_data, ignore_index=True)
    
    final_df.to_csv(csv_path, index=False, encoding="utf-8")
    log(f"csv saved → {csv_path}")
    log(f"Total applicant IDs: {len(applicant_ids)}")

    id_list = list(applicant_ids)

    log("--- Exporting Images ---")

    export_blobsphoto(conn, id_list, SQL_PHOTO, OUTPUT_DIRS["photo"], "Photo")
    export_blobssign(conn, id_list, SQL_SIGN2, OUTPUT_DIRS["sign2"], "Signature2")
    export_blobssign(conn, id_list, SQL_SIGN1, OUTPUT_DIRS["sign1"], "Signature1")

    conn.close()
    log("All tasks completed!")


# ============================================
# GUI WINDOW
# ============================================
root = tk.Tk()
root.title("DOTM License Data Extractor")
root.geometry("750x600")

# License input
ttk.Label(root, text="License Numbers (comma/space separated):").pack(anchor="w", padx=10, pady=5)
entry_license = ttk.Entry(root, width=80)
entry_license.pack(padx=10)

# Password input
ttk.Label(root, text="Oracle Password:").pack(anchor="w", padx=10, pady=5)
entry_password = ttk.Entry(root, width=40, show="*")
entry_password.pack(padx=10)

# Start button
ttk.Button(root, text="START PROCESS", command=start_processing).pack(pady=10)

# Log window
log_box = scrolledtext.ScrolledText(root, width=90, height=25)
log_box.pack(padx=10, pady=10)

root.mainloop()
