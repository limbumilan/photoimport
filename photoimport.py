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
output_folder1 = "/Users/milanlimbu/downloads/photos"
output_folder2="/Users/milanlimbu/downloads/sign1"
os.makedirs(output_folder1, exist_ok=True)
os.makedirs(output_folder2, exist_ok=True)

raw_ids=input("Enter Applicant IDs (comma or space separated):")

id_list = [id.strip() for id in raw_ids.replace(",", " ").split() if id.strip()]

print(f"Fetching photos for: {id_list}")

# Connect to Oracle
connection = oracledb.connect(user=username, password=password, dsn=dsn)
cursor1 = connection.cursor()
cursor2=connection.cursor()

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

print("Exporting signature...")
for applicant_id, blob in cursor2:
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
cursor2.close()          
connection.close()


print("All photographs exported successfully!")
