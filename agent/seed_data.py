
import firebase_admin
from firebase_admin import credentials, db
import time
import os

# Check for service account key
cred_path = "serviceAccountkey.json"
if not os.path.exists(cred_path):
    # Try looking in parent or common locations if not here, 
    # but based on previous context, the user might have one. 
    # If not, we might have to skip or ask user.
    # For this environment, let's assume one exists or we Create a mock one? No.
    # We will try to find it.
    print(f"Error: {cred_path} not found.")
    exit(1)

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://kriplani-builders-default-rtdb.asia-southeast1.firebasedatabase.app' 
})

ref = db.reference('/')

system_id = "test-system-001"
print(f"Removing {system_id}...")

ref.child(f'systems/{system_id}').delete()

print("Done.")
