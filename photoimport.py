import oracledb
import os
import getpass
# ==========================
# ORACLE CONNECTION DETAILS
# ==========================
username = "dotm_milan"
dsn = "10.250.252.201:1521/DOTM" 
password = getpass.getpass(f"Enter password for {username}@{dsn}: ")

# ==========================
# LOCAL OUTPUT FOLDER (MAC)
# ==========================
output_folder1 = r"C:\Users\HP\Desktop\DATA\photos"
output_folder2= r"C:\Users\HP\Desktop\DATA\sign1"
output_folder3=r"C:\Users\HP\Desktop\DATA\sign2"
os.makedirs(output_folder1, exist_ok=True)
os.makedirs(output_folder2, exist_ok=True)
os.makedirs(output_folder3, exist_ok=True)

raw_ids=input("Enter Applicant IDs (comma or space separated):")

id_list = [id.strip() for id in raw_ids.replace(",", " ").split() if id.strip()]

print(f"Fetching photos for: {id_list}")

# Connect to Oracle
connection = oracledb.connect(user=username, password=password, dsn=dsn)
cursor1 = connection.cursor()
cursor2=connection.cursor()
cursor3=connection.cursor()

bind_vars1 = ",".join([f":id{i}" for i in range(len(id_list))])
sql1 = f"""
    SELECT applicant_id, photograph
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({bind_vars1})
      AND photograph IS NOT NULL
"""
cursor1.execute(sql1,id_list)
   

print("Exporting photographs...")

for applicant_id, blob in cursor1:
    filename = f"{applicant_id}.jpg"
    file_path = os.path.join(output_folder1, filename)

    with open(file_path, "wb") as f:
        offset = 1
        chunk_size = 65536  # 64 KB

        while True:
            data = blob.read(offset, chunk_size)
            if not data:
                break
            f.write(data)
            offset += len(data)

    print(f"✔ Saved {filename}")

cursor1.close()
bind_vars2 = ",".join([f":id{i}" for i in range(len(id_list))])
sql2 = f"""
    SELECT applicant_id, signature
    FROM edlvrs.applicant_biometric
    WHERE applicant_id IN ({bind_vars2}) and signature IS NOT NULL 
   """
cursor2.execute(sql2,id_list)

print("Exporting signature2...")
for applicant_id, blob in cursor2:
    filename = f"{applicant_id}.jpg"
    file_path = os.path.join(output_folder3, filename)

    with open(file_path, "wb") as f:
        offset = 1
        chunk_size = 65536  # 64 KB

        while True:
            data = blob.read(offset, chunk_size)
            if not data:
                break
            f.write(data)
            offset += len(data)
            print(f"✔ Saved {filename}")
cursor2.close()
#SIGN2....................................

bind_vars3 = ",".join([f":id{i}" for i in range(len(id_list))])
sql3 = f"""
     select A.id,B.signature
     FROM EDLVRS.APPLICANT A
     INNER JOIN EDLVRS.LICENSE L
     ON A.ID=L.APPLICANT_ID
     INNER JOIN EDLVRS.LICENSEDETAIL LD
     ON L.ID=LD.LICENSE_ID
     INNER JOIN EDLVRS.DOTM_USER_BIOMETRIC B
     ON LD.ISSUE_AUTHORITY_ID=b.user_id
     
     WHERE A.ID IN ({bind_vars3})
     
     and b.signature is not null
     and
      LD.ID = ( SELECT ID
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID
        ORDER BY issuedate DESC
        FETCH FIRST 1 ROW ONLY )
    
    """

cursor3.execute(sql3,id_list)
   

print("Exporting sign1...")

for applicant_id, blob in cursor3:
    filename = f"{applicant_id}.jpg"
    file_path = os.path.join(output_folder2, filename)

    with open(file_path, "wb") as f:
        offset = 1
        chunk_size = 65536  # 64 KB

        while True:
            data = blob.read(offset, chunk_size)
            if not data:
                break
            f.write(data)
            offset += len(data)

    print(f"✔ Saved {filename}")

cursor3.close()

connection.close()


print("All photographs exported successfully!")
