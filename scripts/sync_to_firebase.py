import os
import sys

# Ensure application directory is always in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from config import Config
from firebase_config import encode_firestore, decode_firestore, LOCAL_DATA_FILE

def sync_all_data():
    print("\n==================================================")
    print(f"  SYNCING SHIV TRADERS DATA TO FIREBASE FIRESTORE")
    print(f"  Project ID: {Config.FIREBASE_PROJECT_ID}")
    print("==================================================")

    if not os.path.exists(LOCAL_DATA_FILE):
        print("[ERROR] local_db.json not found.")
        return

    with open(LOCAL_DATA_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)

    api_key = Config.FIREBASE_API_KEY
    project_id = Config.FIREBASE_PROJECT_ID
    base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"

    # 1. Company Information
    if 'company' in db:
        comp_data = db['company']
        url = f"{base_url}/company/main_info?key={api_key}"
        res = requests.patch(url, json=encode_firestore(comp_data), timeout=10)
        print(f"Synced [company] document: HTTP {res.status_code}")

    # 2. Products
    if 'products' in db:
        for pid, pdata in db['products'].items():
            url = f"{base_url}/products/{pid}?key={api_key}"
            res = requests.patch(url, json=encode_firestore(pdata), timeout=10)
            print(f"Synced [products] -> {pdata.get('name')}: HTTP {res.status_code}")

    # 3. Projects
    if 'projects' in db:
        for prid, prdata in db['projects'].items():
            url = f"{base_url}/projects/{prid}?key={api_key}"
            res = requests.patch(url, json=encode_firestore(prdata), timeout=10)
            print(f"Synced [projects] -> {prdata.get('project_name')}: HTTP {res.status_code}")

    # 4. Services
    if 'services' in db:
        for sid, sdata in db['services'].items():
            url = f"{base_url}/services/{sid}?key={api_key}"
            res = requests.patch(url, json=encode_firestore(sdata), timeout=10)
            print(f"Synced [services] -> {sdata.get('title')}: HTTP {res.status_code}")

    # 5. Credentials
    if 'credentials' in db:
        for cid, cdata in db['credentials'].items():
            url = f"{base_url}/credentials/{cid}?key={api_key}"
            res = requests.patch(url, json=encode_firestore(cdata), timeout=10)
            print(f"Synced [credentials] -> {cdata.get('title')}: HTTP {res.status_code}")

    # 6. Enquiries
    if 'enquiries' in db:
        for eid, edata in db['enquiries'].items():
            url = f"{base_url}/enquiries/{eid}?key={api_key}"
            res = requests.patch(url, json=encode_firestore(edata), timeout=10)
            print(f"Synced [enquiries] -> {edata.get('name')}: HTTP {res.status_code}")

    print("\n[SUCCESS] All collections successfully populated in your live Firebase Firestore!")
    print(f"Check your Firebase Console at: https://console.firebase.google.com/project/{project_id}/firestore\n")

if __name__ == '__main__':
    sync_all_data()
