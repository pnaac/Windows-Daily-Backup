# Windows Agent Deployment SOP

This document outlines the **End-to-End Procedure** for building, deploying, and installing the Kriplani Backup Agent. It covers everything from fetching the code to the final "Enterprise Service" installation.

## 🏗️ Phase 1: Build (On Administrator/Developer Machine)
**Prerequisites**:
- Windows Machine (highly recommended for building .exe)
- [Python 3.11+](https://www.python.org/downloads/) installed and added to PATH.
- [Git](https://git-scm.com/downloads) installed.

### 1. Fetch the Code
Open PowerShell or Command Prompt.
```powershell
# Clone the repository (if first time)
git clone https://github.com/pnaac/Windows-Daily-Backup.git
cd Windows-Daily-Backup

# OR Pull the latest changes (if already cloned)
git pull origin main
```

### 2. Setup Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate

# Install dependencies
pip install -r agent/requirements.txt
```

### 3. Build the Executable
This step packages the Python code, `rclone.exe`, and all dependencies into a single `.exe` file.
```powershell
# Run the build script
python agent/build_agent.py
```
*   **Output**: check the `dist/` folder. You should see `KriplaniBackupAgent.exe`.

### 4. Prepare Deployment Package
Create a folder named `Deploy_Package` and copy these files into it:
1.  `dist/KriplaniBackupAgent.exe`
2.  `agent/serviceAccountKey.json` (Ensure this is the PROD key)
3.  `agent/install_service.bat`
4.  `agent/uninstall_agent.bat`
5.  *(Optional but recommended)* `rclone.exe` (The build script likely bundled it, but having it alongside is safe)

---

## 🚛 Phase 2: Deploy (On Client Machine / TallyServer)

### 1. Transfer Files
Copy the entire contents of your `Deploy_Package` to the server, e.g., to `C:\KriplaniBackup`.

### 2. Clean up Old Versions (If upgrading)
If an old version represents a different architecture (e.g., Python script vs Exe, or User App vs Service):
1.  Right-click `uninstall_agent.bat` -> **Run as Administrator**.
2.  Wait for it to stop processes and remove tasks.

### 3. Install the Enterprise Service
1.  Right-click `install_service.bat` -> **Run as Administrator**.
2.  **Verify**: The script should say `[SUCCESS] Task created`.

### 4. Verification Check
1.  **Process**: Open Task Manager -> Details tab. Look for `KriplaniBackupAgent.exe`.
2.  **Logs**: Open File Explorer and type `%APPDATA%\KriplaniBackup` in the address bar.
    *   Open `agent.log`.
    *   Look for lines like: `✅ Connected to Firebase` and `👀 Agent ... Active`.

---

## 🆘 Troubleshooting
*   **"Python not found"**: On the build machine, ensure you checked "Add Python to PATH" during installation.
*   **"Access Denied"**: You MUST right-click the `.bat` files and choose "Run as Administrator". Double-clicking is often not enough on Servers.
*   **"Missing serviceAccountKey.json"**: The agent will exit immediately if this file is missing. Check `agent.log`.
