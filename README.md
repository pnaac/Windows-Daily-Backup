# Kriplani Backup Control System
### Next-Gen Decentralized Backup Orchestration

> **Version**: 3.0.0 (Cloud-Controlled Architecture)
> **Status**: Production Ready
> **Maintained By**: PNAAC IT LABS


---

## 🎯 Executive Summary (For CxOs & Leadership)
**Kriplani Backup Control** is a centralized command center for decentralized data protection. It solves the critical challenge of managing backups across a fragmented fleet of workstations without imposing heavy infrastructure costs.

### Key Value Propositions
*   **Zero-Infrastructure Cost**: Leverages existing Google Drive/Storage and local compute. No expensive central backup servers.
*   **Centralized Governance**: A single "Single Pane of Glass" dashboard to view the health of the entire fleet.
*   **Audit & Compliance**: integrated **Immutable Audit Logs** track every system change, deletion, and access event, ensuring accountability.
*   **Agility**: The new **Cloud-Controlled Agent** allows IT Ops to push new capabilities (e.g., "Run SQL Dump", "Patch System") instantly without manually reinstalling software on hundreds of machines.

---

## 🚀 Product Overview (For Product Managers)
The system consists of three core components working in harmony:

### 1. The Dashboard (Command Center)
*   **Fleet View**: Real-time status of all active agents (Online/Offline, Last Backup Size).
*   **System Detail**: Granular control over specific machines. Trigger backups manually, view specific logs.
*   **Job Editor**: A flexible UI to define *what* gets backed up (Files, SQL Dumps) and *where*.
*   **Audit Logs**: Searchable, exportable history of all administrative actions.

### 2. The Cloud-Controlled Agent (Endpoint)
*   **Smart Dispatcher**: A lightweight Python service running on client machines.
*   **Auto-Update Logic**: Receives instructions from the cloud. Can execute file syncs (Rclone) or arbitrary scripts (Python/Powershell) dynamically.
*   **Resiliency**: Built-in "Boot Storm" protection (randomized startup delays) and robust retry mechanisms.

### 3. The Backend (Firebase)
*   **Real-time Database**: Acts as the nervous system, syncing state between Agents and Dashboard instantly.
*   **Authentication**: Google Workspace integration for secure Single Sign-On (SSO).

---

## 💻 Developer Guide (For Engineering)

### Architecture
*   **Frontend**: Svelte 5 + Vite + TailwindCSS (DaisyUI). Fast, reactive, compiled.
*   **Agent**: Python 3.12.
    *   **Handlers**: Modular architecture (`rclone_handler.py`, `script_handler.py`).
    *   **Persistence**: Windows Registry / Systemd integration.
*   **Backend**: Firebase (Auth, Realtime DB). Serverless.

### Setup & Installation
#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Agent (Development)
```bash
cd agent
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
python agent.py
```

### 📦 Deployment: Building for Windows
To deploy to end-user machines, you must build a standalone Executable (`.exe`).

**Prerequisites:**
1.  A Windows Machine (or VM) with Python 3.10+ installed.
2.  `agent/serviceAccountKey.json` (Production Credentials) present.
3.  `agent/rclone.exe` (Download from rclone.org) present in the same folder.

**Build Steps:**
1.  Open PowerShell as Administrator.
2.  Navigate to the `agent` directory.
3.  Run the build script:
    ```powershell
    python build_agent.py
    ```
4.  **Result**: A file named `KriplaniBackupAgent_Installer.exe` will be created in the `dist` folder.

### 💿 Installation on Client Machine
1.  **Copy**: Transfer `KriplaniBackupAgent_Installer.exe` to the target machine (e.g., `C:\Program Files\KriplaniBackup`).
2.  **Run**: Double-click the `.exe` to start it.
    *   *First Run*: It will register itself in the Windows Registry for **Startup Persistence**.
    *   *Background*: It runs silently. You can verify it in Task Manager (`KriplaniBackupAgent`).
3.  **Verify**: Log in to the Web Dashboard. The new agent should appear in the **Fleet View** within 1 minute.

---

## 👤 End User Guide (For Staff)

### How it Works
1.  **Invisible Protection**: The backup agent runs silently in the background. You do not need to do anything.
2.  **Performance Friendly**: The system waits 10 minutes after you turn on your computer before starting any heavy work to ensure your PC remains fast during startup.
3.  **Status**: You can view the backup status in the **Kriplani Backup Dashboard** (ask IT for the link).

### FAQ
*   **"My computer is slow."**
    *   The agent is designed to be low-priority. If you strictly need full performance, contact IT to pause your schedule.
*   **"I deleted a file by accident."**
    *   Contact the IT Administrator immediately. We utilize "Snapshot" backups, so we likely have a copy from yesterday.
