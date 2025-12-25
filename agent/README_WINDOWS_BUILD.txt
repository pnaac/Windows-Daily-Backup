=== BUILDING THE KRIPLANI BACKUP AGENT (WINDOWS) ===

1.  **Prerequisites**:
    -   A machine running Windows 10 or 11.
    -   Python installed (Make sure to check "Add Python to PATH" during install).

2.  **Setup**:
    -   Copy this entire `agent` folder to the Windows machine.
    -   Open a terminal (Command Prompt or PowerShell) inside this folder.

3.  **Get Rclone**:
    -   Download Rclone from: https://downloads.rclone.org/v1.65.0/rclone-v1.65.0-windows-amd64.zip
    -   Extract `rclone.exe` from the zip.
    -   Place `rclone.exe` in this `agent` folder (next to `agent.py`).

4.  **Install Dependencies**:
    -   Run: `pip install -r requirements.txt`

5.  **Build**:
    -   Run the build script:
        python build_agent.py

5.  **Output**:
    -   The script will create a `dist` folder.
    -   Inside `dist`, you will find `KriplaniBackupAgent_Installer.exe`.

6.  **Distribution**:
    -   Take that .exe file.
    -   Upload it to your Web Server (or Firebase Storage).
    -   Update the download link in the Frontend if you change the filename.
