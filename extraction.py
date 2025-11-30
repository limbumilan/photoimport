import oracledb
import pandas as pd
from datetime import datetime
import os
import getpass

# ============================================
# CONFIG
# ============================================
USERNAME = "dotm_milan"
DSN = "10.250.252.201/DOTM"

BASE_DATA_FOLDER = "/Users/milanlimbu/desktop/data"

OUTPUT_DIRS = {
    "photo": os.path.join(BASE_DATA_FOLDER, "Photo"),
    "sign1": os.path.join(BASE_DATA_FOLDER, "Sign1"),
    "sign2": os.path.join(BASE_DATA_FOLDER, "Sign2")
}

# Create folders if missing
os.makedirs(BASE_DATA_FOLDER, exist_ok=True)
for folder in OUTPUT_DIRS.values():
    os.makedirs(folder, exist_ok=True)

# ============================================
# SQL - MAIN LICENSE QUERY
# ============================================
SQL_LICENSE_INFO = """
SELECT
    A.ID AS PRODUTID,
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
    'Photo' || A.ID || '.jpg' AS Photo,
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
       WHERE dl.newlicenseno = LD.newlicenseno) AS Category,

    'Sign1' || A.ID || '.jpg' AS Signature1,
    'Sign2' || A.ID || '.jpg' AS Signature2

FROM edlvrs.licensedetail LD
JOIN edlvrs.license L ON LD.license_id = L.id
JOIN edlvrs.applicant A ON L.applicant_id = A.id
LEFT JOIN edlvrs.address AD ON A.id = AD.applicant_id AND AD.addresstype='PERM'

WHERE LD.newlicenseno = :license_no
AND LD.expirydate = (
        SELECT MAX(expirydate)
        FROM edlvrs.licensedetail
        WHERE license_id = L.id
)
AND LD.issuedate = (
        SELECT MAX(issuedate)
        FROM edlvrs.licensedetail
        WHERE license_id = L.id
)
AND L.printed <> 3
"""

# ============================================
# BLOB EXPORT UTILITY
# ============================================
def save_blob(blob, file_path):
    with open(file_path, "wb") as f:
        f.write(blob.read())

def export_blobs(conn, ids, sql_template, out_dir, label):
    if not ids:
        print(f"No IDs for {label}.")
        return

    cursor = conn.cursor()

    bind_vars = {f"id{i}": val for i, val in enumerate(ids)}
    placeholders = ",".join(f":id{i}" for i in range(len(ids)))

    sql = sql_template.replace("{{IDS}}", placeholders)

    cursor.execute(sql, bind_vars)
    rows = cursor.fetchall()

    print(f"{label} → {len(rows)} found")

    for aid, blob in rows:
        path = os.path.join(out_dir, f"{aid}.jpg")
        save_blob(blob, path)
        print(f"{label} saved: {path}")

    cursor.close()

# ============================================
# MAIN
# ============================================
def main():

    license_input = input("Enter License Numbers (comma or space separated): ")
    license_numbers = [x.strip() for x in license_input.replace(",", " ").split() if x.strip()]

    if not license_numbers:
        print("No license numbers entered.")
        return

    password = getpass.getpass(f"Enter password for {USERNAME}@{DSN}: ")

    try:
        conn = oracledb.connect(user=USERNAME, password=password, dsn=DSN)
        print("\nConnected to Oracle.\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    all_data = []
    applicant_ids = set()

    # Fetch info
    for lic in license_numbers:
        print(f"\nFetching license → {lic}")
        try:
            df = pd.read_sql(SQL_LICENSE_INFO, conn, params={"license_no": lic})

            if df.empty:
                print(f"⚠ No data for {lic}")
                continue

            ids = df["PRODUTID"].dropna().astype(int).tolist()
            applicant_ids.update(ids)
            all_data.append(df)

            print(f"✓ Applicant IDs: {ids}")

        except Exception as e:
            print(f"Error: {e}")

    if not all_data:
        print("\nNo valid license records found.")
        return

    # Save Excel in BASE DATA FOLDER
    excel_path = os.path.join(
        BASE_DATA_FOLDER,
        f"license_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )

    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_excel(excel_path, index=False)

    print(f"\nExcel saved → {excel_path}")
    print(f"Total applicant IDs → {len(applicant_ids)}")

    ids_list = list(applicant_ids)

    # SQL for blobs
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

    print("\n--- Exporting Images ---\n")

    export_blobs(conn, ids_list, SQL_PHOTO, OUTPUT_DIRS["photo"], "Photo")
    export_blobs(conn, ids_list, SQL_SIGN2, OUTPUT_DIRS["sign2"], "Signature2")
    export_blobs(conn, ids_list, SQL_SIGN1, OUTPUT_DIRS["sign1"], "Signature1")

    print("\nAll tasks completed successfully!")
    

    conn.close()

# ============================================
# RUN
# ============================================
if __name__ == "__main__":
    main()
