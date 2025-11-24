import oracledb
import pandas as pd
from datetime import datetime
import os
import getpass

# ------------------------------
# ORACLE CONNECTION DETAILS
# ------------------------------
username = "dotm_milan"
dsn = "10.250.252.201/DOTM"
password = getpass.getpass(f"Enter password for {username}@{dsn}: ")

# ------------------------------
# OUTPUT FOLDERS
# ------------------------------
output_folder_photos = r"/Users/milanlimbu/desktop/data/Photos"
output_folder_sign1 = r"/Users/milanlimbu/desktop/data/Sign1"
output_folder_sign2 = r"/Users/milanlimbu/desktop/data/Sign2"

os.makedirs(output_folder_photos, exist_ok=True)
os.makedirs(output_folder_sign1, exist_ok=True)
os.makedirs(output_folder_sign2, exist_ok=True)

# ------------------------------
# INPUT LICENSE NUMBERS
# ------------------------------
raw_input_ids = input("Enter License Numbers (comma or space separated): ")
license_numbers = [x.strip() for x in raw_input_ids.replace(",", " ").split() if x.strip()]
print(f"Processing licenses: {license_numbers}")

if not license_numbers:
    print("No license numbers entered. Exiting.")
    exit()

# ------------------------------
# SQL QUERY
# ------------------------------
SQL_QUERY = """
SELECT DISTINCT
    A.ID AS ProdutID,
    A.LASTNAME AS Surname,
    A.FIRSTNAME || ' ' || NVL(A.MIDDLENAME,'') AS Given_Name,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS Sex,
    TO_CHAR(A.DATEOFBIRTHAD,'DD-MM-YYYY') AS Date_of_birth,
    'Government of Nepal' AS Nationality,
    (SELECT TO_CHAR(MIN(CAST(ISSUEDATE AS DATE)), 'DD-MM-YYYY')
       FROM EDLVRS.LICENSEDETAIL
       WHERE NEWLICENSENO = LD.NEWLICENSENO) AS Date_of_issue,
    TO_CHAR(LD.EXPIRYDATE,'DD-MM-YYYY') AS Date_of_expiry,
    A.CITIZENSHIPNUMBER AS Citizenship_No,
    A.PASSPORTNUMBER AS Passport_No,
    'Photo'||A.ID||'.jpg' AS Photo,
    A.MOBILENUMBER AS Contact_No,
    (SELECT NAME FROM EDLVRS.LICENSEISSUEOFFICE WHERE ID = LD.LICENSEISSUEOFFICE_ID) AS License_Office,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || NVL(A.WITNESSLASTNAME,'') AS FH_Name,
    (SELECT NAME FROM EDLVRS.DISTRICT WHERE ID = AD.DISTRICT_ID) AS Region,
    COALESCE(NULLIF((SELECT NAME FROM EDLVRS.VILLAGEMETROCITY WHERE ID = AD.VILLAGEMETROCITY_ID),'OTHERS'),'') 
    || ' ' || COALESCE(AD.TOLE,'') || '-' || COALESCE(AD.WARDNUMBER,'') AS Street_House_Number,
    (SELECT TYPE FROM EDLVRS.BLOODGROUP WHERE ID = A.BLOODGROUP_ID) AS BG,
    LD.NEWLICENSENO AS Driving_License_No,
    (SELECT NAME FROM EDLVRS.COUNTRY WHERE ID = AD.COUNTRY_ID) AS Country,
    (SELECT LISTAGG(TCL.TYPE, ', ') WITHIN GROUP (ORDER BY TCL.TYPE)
       FROM EDLVRS.LICENSEDETAIL DL
       JOIN EDLVRS.LICENSECATEGORY CL ON CL.LICENSEDETAIL_ID = DL.ID
       JOIN EDLVRS.LICENSECATEGORYTYPE TCL ON TCL.ID = CL.LISCCATEGORYTYPE_ID
       WHERE DL.NEWLICENSENO = LD.NEWLICENSENO) AS Category,
    'Sign1'||A.ID||'.jpg' AS Signature1,
    'Sign2'||A.ID||'.jpg' AS Signature2
FROM EDLVRS.LICENSEDETAIL LD
JOIN EDLVRS.LICENSE L ON LD.LICENSE_ID = L.ID
JOIN EDLVRS.APPLICANT A ON L.APPLICANT_ID = A.ID
LEFT JOIN EDLVRS.ADDRESS AD ON A.ID = AD.APPLICANT_ID AND AD.ADDRESSTYPE='PERM'
WHERE LD.NEWLICENSENO = :license_no
  AND LD.EXPIRYDATE = (
        SELECT MAX(EXPIRYDATE)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID
      )
  AND LD.ISSUEDATE = (
        SELECT MAX(ISSUEDATE)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID
      )
"""

# ------------------------------
# CONNECT TO ORACLE
# ------------------------------
conn = None
try:
    conn = oracledb.connect(user=username, password=password, dsn=dsn)
    all_data = []
    app_ids = []

    # ------------------------------
    # FETCH DATA FOR EACH LICENSE
    # ------------------------------
    for lic in license_numbers:
        print(f"\nFetching data for {lic}...")
        try:
            df = pd.read_sql(SQL_QUERY, conn, params={"license_no": lic})
            print(f"Columns returned: {df.columns.tolist()}")
            print(f"Rows returned: {len(df)}")
            if not df.empty:
                all_data.append(df)
                ids = df["ProdutID"].dropna().astype(int).tolist()
                app_ids.extend(ids)
                print(f"Applicant IDs found: {ids}")
            else:
                print(f"No data found for {lic}")
        except Exception as e:
            print(f"Error fetching {lic}: {e}")

    if not all_data:
        print("No records extracted. Exiting.")
        exit()

    # ------------------------------
    # SAVE EXCEL IN CURRENT FOLDER
    # ------------------------------
    final_df = pd.concat(all_data, ignore_index=True)
    excel_file = os.path.join(os.getcwd(), f"license_output_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx")
    final_df.to_excel(excel_file, index=False)
    print(f"\nExcel saved → {excel_file}")

    # ------------------------------
    # Check applicant IDs before exporting images
    # ------------------------------
    app_ids = list(set(app_ids))
    print(f"\nTotal unique applicant IDs for images: {len(app_ids)}")
    if not app_ids:
        print("No applicant IDs found for images. Exiting.")
        exit()

    # ------------------------------
    # BLOB EXPORT FUNCTION
    # ------------------------------
    def save_blob(blob, folder, filename):
        path = os.path.join(folder, filename)
        with open(path, "wb") as f:
            f.write(blob.read())

    # ------------------------------
    # PREPARE BIND VARIABLES FOR MULTI-ID
    # ------------------------------
    bind_vars = {f"id{i}": val for i, val in enumerate(app_ids)}
    ids_placeholder = ",".join([f":id{i}" for i in range(len(app_ids))])

    # ------------------------------
    # EXPORT PHOTOS
    # ------------------------------
    sql_photo = f"""
    SELECT applicant_id, photograph
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({ids_placeholder})
      AND photograph IS NOT NULL
    """
    cursor = conn.cursor()
    cursor.execute(sql_photo, bind_vars)
    rows = cursor.fetchall()
    print(f"Photos to export: {len(rows)}")
    for aid, blob in rows:
        save_blob(blob, output_folder_photos, f"{aid}.jpg")
        print(f"Photo saved → {aid}.jpg")
    cursor.close()

    # ------------------------------
    # EXPORT SIGNATURE2
    # ------------------------------
    sql_sign2 = f"""
    SELECT applicant_id, signature
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({ids_placeholder})
      AND signature IS NOT NULL
    """
    cursor = conn.cursor()
    cursor.execute(sql_sign2, bind_vars)
    rows = cursor.fetchall()
    print(f"Signatures2 to export: {len(rows)}")
    for aid, blob in rows:
        save_blob(blob, output_folder_sign2, f"{aid}.jpg")
        print(f"Signature2 saved → {aid}.jpg")
    cursor.close()

    # ------------------------------
    # EXPORT SIGNATURE1
    # ------------------------------
    sql_sign1 = f"""
    SELECT A.ID, B.signature
    FROM EDLVRS.APPLICANT A
    JOIN EDLVRS.LICENSE L ON A.ID = L.APPLICANT_ID
    JOIN EDLVRS.LICENSEDETAIL LD ON L.ID = LD.LICENSE_ID
    JOIN EDLVRS.DOTM_USER_BIOMETRIC B ON LD.ISSUE_AUTHORITY_ID = B.USER_ID
    WHERE A.ID IN ({ids_placeholder})
      AND B.signature IS NOT NULL
      AND LD.ID = (
          SELECT MAX(ID) FROM EDLVRS.LICENSEDETAIL WHERE LICENSE_ID = L.ID
      )
    """
    cursor = conn.cursor()
    cursor.execute(sql_sign1, bind_vars)
    rows = cursor.fetchall()
    print(f"Signatures1 to export: {len(rows)}")
    for aid, blob in rows:
        save_blob(blob, output_folder_sign1, f"{aid}.jpg")
        print(f"Signature1 saved → {aid}.jpg")
    cursor.close()

    print("\nAll photos and signatures exported successfully!")

except Exception as e:
    print(f"Unexpected error: {e}")

finally:
    if conn:
        conn.close()
