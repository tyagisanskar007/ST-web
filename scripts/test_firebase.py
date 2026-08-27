import os
import sys

# Ensure application directory is always in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from config import Config
from firebase_config import firebase_db

def check_connection():
    print("==================================================")
    print("      SHIV TRADERS - FIREBASE CONNECTION TEST")
    print("==================================================")
    print(f"Project ID:     {Config.FIREBASE_PROJECT_ID}")
    print(f"API Key:        {Config.FIREBASE_API_KEY[:10]}...")
    print(f"Storage Bucket: {Config.FIREBASE_STORAGE_BUCKET}")
    print("--------------------------------------------------")

    # Check 1: serviceAccountKey.json
    key_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'serviceAccountKey.json')
    if os.path.exists(key_path):
        print(f"[SUCCESS] serviceAccountKey.json found at: {key_path}")
    else:
        print("[INFO] No serviceAccountKey.json file found yet in project folder.")

    # Check 2: Firestore API access
    api_url = f"https://firestore.googleapis.com/v1/projects/{Config.FIREBASE_PROJECT_ID}/databases/(default)/documents/company/main_info?key={Config.FIREBASE_API_KEY}"
    try:
        res = requests.get(api_url, timeout=5)
        print(f"Firestore Endpoint Response: HTTP {res.status_code}")
        if res.status_code in (200, 404):
            print("[SUCCESS] Cloud Firestore is active and accessible!")
        elif res.status_code == 403:
            print("[NOTICE] Cloud Firestore is enabled, but access is blocked by default Security Rules.")
            print("         Update your Firestore Rules to: allow read, write: if true;")
    except Exception as e:
        print(f"[ERROR] Could not reach Firestore: {e}")
    print("==================================================\n")

if __name__ == '__main__':
    check_connection()
