import os
import subprocess
import sys
import shutil

def build():
    print("🚀 Building Kriplani Backup Agent for Windows (Offline Bundle)...")
    
    # 1. Check for Credentials
    if not os.path.exists("serviceAccountKey.json"):
        print("❌ Error: serviceAccountKey.json missing! Cannot build without credentials.")
        sys.exit(1)

    # 2. Check for Rclone Binary
    # We expect the user to have downloaded rclone.exe and placed it in the agent folder
    if not os.path.exists("rclone.exe"):
        print("❌ Error: rclone.exe missing!")
        print("👉 Please download rclone-windows-amd64.zip, extract rclone.exe, and place it in this folder.")
        sys.exit(1)

    # Install PyInstaller if missing
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build Command
    # Bundle both the Key and the Rclone binary
    separator = ";" if os.name == 'nt' else ":"
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--console", 
        "--name", "KriplaniBackupAgent_Installer",
        f"--add-data", f"serviceAccountKey.json{separator}.",
        f"--add-data", f"rclone.exe{separator}.",
        "agent.py"
    ]
    
    print(f"🔨 Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    print("\n✅ Build Complete!")
    print(f"📂 Output: {os.path.abspath('dist/KriplaniBackupAgent_Installer.exe')}")
    print("👉 This .exe now contains Rclone inside it. No internet validation required on client.")

if __name__ == "__main__":
    build()
