# Enterprise Build & Distribution Architecture

**Critique**: "Why can't I build the agent from the Web UI?"

## The Technical Reality
A Web Browser (Chrome/Edge) runs **JavaScript**. It is a lightweight viewing client.
A Windows Executable (`.exe`) is a binary file compiled from **Python**.
**A Browser cannot compile Python code into a Windows EXE.** It lacks the operating system libraries, the Python compiler, and the processing power to do so securely.

## The Solution: "Build Once, Deploy Infinite"

In an Enterprise Architecture, we separate **Build** from **Distribution**.

### 1. The Build Pipeline (The "Factory")

We don't build the car every time we sell it. We build it in a factory and ship it to the showroom.

*   **Tool**: GitHub Actions / Azure DevOps / Jenkins.
*   **Trigger**: When you push code changes.
*   **Action**: A secure cloud runner (Windows VM) runs `build_agent.py`.
*   **Output**: It produces `KriplaniBackupAgent_v2.exe`.
*   **Storage**: It uploads this file to **Firebase Storage** or a Release URL.

### 2. The Web UI (The "Showroom")

The Web Dashboard simply points to the latest artifact in the storage.

*   **Action**: Admin clicks **"Download Agent"**.
*   **Result**: The browser downloads the pre-built `KriplaniBackupAgent_v2.exe` from the cloud.

## Recommended Workflow for You

Since we are in a pilot phase without a full CI/CD pipeline:

1.  **Manual Build**: You (the Developer) run `build_agent.py` on your machine (or a Windows VM) **once**.
2.  **Upload**: You upload the resulting `.exe` to Firebase Hosting (e.g., in a `public/downloads` folder).
3.  **Distribution**: The Web UI has a static link to that file.

I will now implement the **"Download Agent"** button in the Fleet View to complete this UX loop.
