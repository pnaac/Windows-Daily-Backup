# Windows Agent Deployment SOP

This document outlines the Standard Operating Procedure for installing, upgrading, and removing the Kriplani Backup Agent on Windows Servers.

## 📂 File Manifest

Ensure the following files are present in the Agent directory (e.g., `C:\KriplaniBackup`):

- `KriplaniBackupAgent.exe` (The Agent executable)
- `serviceAccountKey.json` (Google Cloud credentials)
- `rclone.exe` (Bundled or downloaded automatically)
- `install_service.bat` (Installer script)
- `uninstall_agent.bat` (Uninstaller script)

---

## 🚀 1. Installation / Upgrade Procedure

Use this process for **new installations** or **upgrading** to a new version.

1.  **Prepare the Environment**:

    - Create a folder (e.g., `C:\KriplaniBackup`).
    - Paste `KriplaniBackupAgent.exe`, `serviceAccountKey.json`, and the `.bat` scripts into this folder.

2.  **Clean Installation (Recommended)**:

    - If an older version is running, right-click **`uninstall_agent.bat`** and select **Run as Administrator**.
    - Wait for the "Cleanup finished" message.

3.  **Install Service**:

    - Right-click **`install_service.bat`** and select **Run as Administrator**.
    - The script will:
      - Stop any existing instances.
      - Create a **Windows Scheduled Task** named `KriplaniBackupAgent`.
      - Configure it to run with **Highest Privileges** (SYSTEM account).
      - Set it to start **On System Start** (automatically on boot, no login required).
      - Start the agent immediately.

4.  **Verify**:
    - Open **Task Manager** -> **Details** and verify `KriplaniBackupAgent.exe` is running.
    - Open `%APPDATA%\KriplaniBackup\agent.log` to confirm successful startup and connection.

---

## 🗑️ 2. Uninstallation Procedure

Use this to completely remove the agent.

1.  Navigate to the Agent folder.
2.  Right-click **`uninstall_agent.bat`** and select **Run as Administrator**.
3.  The script will:
    - Kill the running process.
    - Delete the Scheduled Task.
    - Remove legacy Registry keys.
4.  You may now delete the Agent folder.

---

## 🛠️ Troubleshooting

- **"Access Denied"**: Ensure you are right-clicking the `.bat` files and choosing "Run as Administrator".
- **Agent not starting**: Check `%APPDATA%\KriplaniBackup\agent.log` for error details.
- **Permissions**: The Agent runs as `SYSTEM`. Ensure `serviceAccountKey.json` is readable by the SYSTEM account (default behavior if file inheritance is on).
