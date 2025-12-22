import firebase_admin
from firebase_admin import credentials, db
import time
import subprocess
import datetime
import os
import sys
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. SYSTEM CONFIGURATION
# ==========================================
KEY_PATH = "serviceAccountKey.json"
RCLONE_REMOTE = "gdrive"  # Must match your 'rclone config' name

# ==========================================
# 2. EMAIL CONFIGURATION (Gmail SMTP)
# ==========================================
# Generate App Password at: https://myaccount.google.com/apppasswords
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your.admin.email@gmail.com"  # <--- REPLACE THIS
SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"  # <--- REPLACE THIS

# ==========================================
# 3. FIREBASE INITIALIZATION
# ==========================================
try:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred, {
        # REPLACE WITH YOUR ACTUAL FIREBASE DB URL
        'databaseURL': 'https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com/'
    })
    root_ref = db.reference('/')
    print("✅ Connected to Firebase Command Center")
except Exception as e:
    print(f"❌ Failed to connect to Firebase: {e}")
    sys.exit(1)


# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================

def update_status(status, message=""):
    """Updates the UI Status Card"""
    try:
        root_ref.child('state').update({
            "status": status,
            "detailed_message": message
        })
    except:
        pass


def parse_rclone_size(bytes_int):
    """Converts raw bytes to human readable string (MB, GB)"""
    if bytes_int == 0: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_int < 1024:
            return f"{bytes_int:.2f} {unit}"
        bytes_int /= 1024
    return f"{bytes_int:.2f} PB"


def send_email_alert(subject, status, details_html, recipients_str):
    """Sends HTML Email to configured recipients"""
    if not recipients_str or not SENDER_PASSWORD or "xxxx" in SENDER_PASSWORD:
        print("⚠️ Email skipped: Credentials or recipients not configured.")
        return

    recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]
    if not recipients: return

    msg = MIMEMultipart()
    msg['From'] = f"Backup Controller <{SENDER_EMAIL}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = f"[{status}] {subject}"

    color = "#10B981" if status == "SUCCESS" else "#EF4444"

    body = f"""
    <html>
      <body style="font-family: sans-serif; color: #333;">
        <div style="border: 1px solid #ddd; border-radius: 8px; overflow: hidden; max-width: 600px;">
          <div style="background-color: {color}; padding: 15px; color: white; text-align: center;">
            <h2 style="margin:0;">Backup {status}</h2>
          </div>
          <div style="padding: 20px;">
            <p><strong>Time:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")}</p>
            <table style="width: 100%; border-collapse: collapse;">
                {details_html}
            </table>
            <p style="font-size: 12px; color: #999; margin-top: 20px;">Automated Alert from Agent.</p>
          </div>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        print(f"📧 Email sent to {len(recipients)} recipients.")
    except Exception as e:
        print(f"❌ Email Failed: {e}")


def enforce_retention(remote_folder_root, config):
    """
    Lists folders on Google Drive and deletes those older than 'keep_daily_days'.
    """
    try:
        policy = config.get('retention_policy', {})
        keep_daily_days = int(policy.get('keep_daily_days', 60))

        print(f"🧹 Retention Check: Keeping last {keep_daily_days} days.")

        # 1. List folders using Rclone
        # Output format example: " -1 2025-12-22 15:30:00 -1 Backup_2025-12-22_15-30"
        result = subprocess.run(
            ["rclone", "lsd", f"{RCLONE_REMOTE}:{remote_folder_root}"],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print("⚠️ Retention skipped: Could not list folders.")
            return

        now = datetime.datetime.now()
        folders_deleted = 0

        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if not parts: continue
            folder_name = parts[-1]  # The last part is the folder name

            # Safety Check: Never delete the Mirror
            if folder_name == "Current_Mirror": continue

            # Regex to parse date from "Backup_2025-12-22_09-00"
            match = re.search(r"Backup_(\d{4}-\d{2}-\d{2})", folder_name)
            if match:
                date_str = match.group(1)
                try:
                    folder_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    age_days = (now - folder_date).days

                    if age_days > keep_daily_days:
                        print(f"   🗑️ PURGING: {folder_name} ({age_days} days old)...")
                        subprocess.run(
                            ["rclone", "purge", f"{RCLONE_REMOTE}:{remote_folder_root}/{folder_name}"],
                            check=True
                        )
                        folders_deleted += 1
                except ValueError:
                    continue

        if folders_deleted > 0:
            print(f"   ✅ Deleted {folders_deleted} old backups.")
        else:
            print("   ✅ No old backups found to delete.")

    except Exception as e:
        print(f"⚠️ Retention Error: {e}")


# ==========================================
# 5. CORE BACKUP LOGIC
# ==========================================

def perform_backup(config):
    start_time = time.time()

    # Read Config
    source_folder = config.get('source_path', r"D:\TallyData")
    remote_folder_root = config.get('remote_folder', "Kriplani_Backups")
    email_recipients = config.get('email_recipients', "")

    print(f"\n🚀 Starting Backup Workflow...")
    print(f"   Source: {source_folder}")

    if not os.path.exists(source_folder):
        err = f"Source folder not found: {source_folder}"
        update_status("Error", err)
        send_email_alert("Backup Failed", "FAILURE", f"<tr><td>Error:</td><td>{err}</td></tr>", email_recipients)
        return

    update_status("Running", "Syncing & Calculating Delta...")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"{remote_folder_root}/Backup_{timestamp}"
    mirror_path = f"{remote_folder_root}/Current_Mirror"
    bytes_transferred = 0

    try:
        # --- STEP A: SYNC (Mirroring) ---
        # We use --use-json-log to capture the exact bytes transferred for the chart
        print("   1️⃣  Syncing to Cloud Mirror...")
        process = subprocess.Popen(
            ["rclone", "sync", source_folder, f"{RCLONE_REMOTE}:{mirror_path}",
             "--transfers", "8", "--use-json-log", "--stats", "1s"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Parse live logs for stats
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None: break
            if line:
                try:
                    log_entry = json.loads(line)
                    if 'stats' in log_entry:
                        bytes_transferred = log_entry['stats'].get('bytes', 0)
                except:
                    pass

        if process.returncode != 0:
            raise Exception("Rclone Sync process returned error code.")

        # --- STEP B: SNAPSHOT (Server Side Copy) ---
        print("   2️⃣  Creating Immutable Snapshot...")
        update_status("Running", "Creating immutable snapshot...")
        subprocess.run([
            "rclone", "copy", f"{RCLONE_REMOTE}:{mirror_path}", f"{RCLONE_REMOTE}:{backup_name}",
            "--server-side-across-configs"
        ], check=True)

        # --- STEP C: RETENTION ---
        print("   3️⃣  Checking Retention Policy...")
        enforce_retention(remote_folder_root, config)

        # --- STEP D: METRICS & REPORTING ---
        end_time = time.time()
        duration_str = f"{int(end_time - start_time)}s"
        size_str = parse_rclone_size(bytes_transferred)
        success_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Update Firebase Stats
        root_ref.child('stats').update({
            "last_run_date": success_date,
            "last_duration_str": duration_str,
            "last_data_transferred_str": size_str
        })

        # Add to History Log
        root_ref.child('history').push({
            "timestamp": success_date,
            "status": "Success",
            "duration": duration_str,
            "size": size_str,
            "type": "Scheduled" if not config.get('trigger_now') else "Manual"
        })

        print(f"✅ Backup Complete. Delta: {size_str}")
        update_status("Idle", f"Success. Uploaded: {size_str}")

        # Send Success Email
        details = f"""
        <tr><td style='padding:5px;'><strong>Duration:</strong></td><td>{duration_str}</td></tr>
        <tr><td style='padding:5px;'><strong>Data Uploaded:</strong></td><td>{size_str}</td></tr>
        <tr><td style='padding:5px;'><strong>Source:</strong></td><td>{source_folder}</td></tr>
        <tr><td style='padding:5px;'><strong>Cloud Folder:</strong></td><td>{backup_name}</td></tr>
        """
        send_email_alert("Daily Backup Success", "SUCCESS", details, email_recipients)

        # Shutdown if configured
        if config.get('shutdown_after_backup') == True:
            print("💤 Shutdown requested.")
            os.system("shutdown /s /t 60")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}")
        update_status("Error", str(e))
        send_email_alert("Backup Failed", "FAILURE", f"<tr><td>Error:</td><td>{str(e)}</td></tr>", email_recipients)


# ==========================================
# 6. MAIN LISTENER LOOP
# ==========================================
print("👀 Agent Active. Waiting for commands...")

while True:
    try:
        # 1. Send Heartbeat (Epoch Time)
        current_epoch = int(time.time())
        root_ref.child('state').update({"agent_heartbeat_epoch": current_epoch})

        # 2. Read Configuration
        full_db = root_ref.get()
        if not full_db:
            time.sleep(5)
            continue

        config = full_db.get('config', {})
        control = full_db.get('control', {})
        state = full_db.get('state', {})

        # 3. Check Manual Trigger
        if control.get('trigger_now') == True:
            root_ref.child('control').update({"trigger_now": False})
            perform_backup(config)

        # 4. Check Schedule
        current_hhmm = datetime.datetime.now().strftime("%H:%M")
        scheduled_time = config.get('schedule_time', '21:00')

        # Debounce logic: Only run if Idle and within first 10s of the minute
        if current_hhmm == scheduled_time and state.get('status') == "Idle":
            if datetime.datetime.now().second < 10:
                perform_backup(config)
                time.sleep(60)  # Wait to avoid double run

        time.sleep(5)  # Poll every 5 seconds

    except KeyboardInterrupt:
        print("\n🛑 Agent stopping...")
        break
    except Exception as e:
        print(f"⚠️ Connection Glitch: {e}")
        time.sleep(10)