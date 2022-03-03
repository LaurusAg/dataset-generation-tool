#!/usr/bin/env python
from smb.SMBConnection import SMBConnection


servers_list = [
    {"ip": "192.168.0.95", "hostname": "LAURUS-SERVER" }  # hostname = name of the PC (not ZeroTier)
    ]
test_directory_name = 'AI/arugula-basil-datasets'
shared_drive_name = 'LaurusServer-2TB'

conn = None
server = None
for srv in servers_list:
    try:
        conn = SMBConnection("pi", "laurus2022", "dataset_gen", srv["hostname"], use_ntlm_v2 = True)
        conn.connect(srv["ip"], port=139, timeout=5)
        server = srv
    except Exception as e:
        conn = None
        continue

if conn is None:
    print("Couldn't find an online server. Dataset is saved locally.")
else:
    print("Connected to", server["hostname"],"at", server["ip"])

    print('Listing shared folders:')
    shared = conn.listShares()
    for i in shared:
        print(i.name)

    try:
        conn.getAttributes(shared_drive_name, test_directory_name)
        print("Directory already exists. New images will be added to the existing dataset.")
    except Exception:
        try:
            conn.createDirectory(shared_drive_name, test_directory_name)
        except:
            print('Failed to create directory.')