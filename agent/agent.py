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
import uuid
import platform
import socket
import traceback
import urllib.request
import zipfile
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
RCLONE_REMOTE = "gdrive"
RCLONE_VERSION = "v1.65.0"
RCLONE_URL = f"https://downloads.rclone.org/{RCLONE_VERSION}/rclone-{RCLONE_VERSION}-windows-amd64.zip"

# --- GLOBAL STATE ---
AGENT_ID = None
RCLONE_BIN = "rclone" # Default to PATH, updated by ensure_rclone

# 2. Identity Persistence (Crucial for preventing Ghost Agents)
# store in %APPDATA%/KriplaniBackup on Windows, or ~/.kriplanibackup on others
if platform.system() == "Windows":
    config_dir = os.path.join(os.getenv('APPDATA'), 'KriplaniBackup')
else:
    config_dir = os.path.join(os.path.expanduser('~'), '.kriplanibackup')

if not os.path.exists(config_dir):
    try:
        os.makedirs(config_dir)
    except:
        config_dir = os.getcwd() # Fallback

IDENTITY_FILE = os.path.join(config_dir, "agent_identity.json")

# --- RESOURCE HANDLING ---
def get_resource_path(relative_path): 

# --- DEPENDENCY MANAGEMENT ---
def ensure_rclone():
    """ 
    Checks if rclone is available. 
    1. Checks local folder (highest priority).
    2. Checks system PATH.
    3. Downloads if missing (Windows only logic mostly, but safe to have).
    """
    global RCLONE_BIN
    
    # 1. Check Bundled Resource (PyInstaller _MEIPASS)
    # When running as onefile, rclone.exe will be extracted to sys._MEIPASS
    bundled_bin = get_resource_path("rclone.exe")
    if os.path.exists(bundled_bin):
        print(f"✅ Found bundled Rclone: {bundled_bin}")
        RCLONE_BIN = bundled_bin
        return

    # 2. Check Local (Updates/Dev)
    local_bin = os.path.join(os.getcwd(), "rclone.exe" if platform.system() == "Windows" else "rclone")
    if os.path.exists(local_bin):
        print(f"✅ Found local rclone: {local_bin}")
        RCLONE_BIN = local_bin
        return

    # 2. Check PATH
    if shutil.which("rclone"):
        print(f"✅ Found rclone in PATH")
        RCLONE_BIN = "rclone"
        return

    # 3. Download (Windows Only for One-Click)
    if platform.system() == "Windows":
        print(f"⬇️ Rclone not found. Downloading {RCLONE_VERSION}...")
        try:
            zip_path = "rclone.zip"
            urllib.request.urlretrieve(RCLONE_URL, zip_path)
            
            print("📦 Extracting Rclone...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("rclone_temp")
            
            # Move binary to root
            extracted_folder = f"rclone-{RCLONE_VERSION}-windows-amd64"
            src = os.path.join("rclone_temp", extracted_folder, "rclone.exe")
            shutil.move(src, "rclone.exe")
            
            # Cleanup
            os.remove(zip_path)
            shutil.rmtree("rclone_temp")
            
            RCLONE_BIN = os.path.abspath("rclone.exe")
            print(f"✅ Rclone installed to: {RCLONE_BIN}")
        except Exception as e:
            print(f"❌ Failed to download rclone: {e}")
            print("⚠️ Please install rclone manually and add to PATH.")
    else:
         print("⚠️ Rclone not found in PATH. Please install it (brew install rclone / apt install rclone).")


# --- FIREBASE INIT ---
try:
    if not os.path.exists(KEY_PATH):
        print(f"❌ CRITICAL: serviceAccountKey.json not found at {KEY_PATH}")
        sys.exit(1)

    cred = credentials.Certificate(KEY_PATH)
    # NOTE: You must update the databaseURL to your specific project's URL if not already set correctly.
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://kriplani-builders-default-rtdb.asia-southeast1.firebasedatabase.app' 
    })
    print("✅ Connected to Firebase Command Center")
except Exception as e:
    print(f"❌ Failed to connect to Firebase: {e}")
    sys.exit(1)


# --- IDENTITY MANAGEMENT ---
def get_or_create_identity():
    global AGENT_ID
    if os.path.exists(IDENTITY_FILE):
        try:
            with open(IDENTITY_FILE, "r") as f:
                data = json.load(f)
                AGENT_ID = data.get("uuid")
        except:
            pass
    
    if not AGENT_ID:
        AGENT_ID = str(uuid.uuid4())
        with open(IDENTITY_FILE, "w") as f:
            json.dump({"uuid": AGENT_ID}, f)
        print(f"🆕 Generate New Agent Identity: {AGENT_ID}")
    else:
        print(f"🆔 Loaded Agent Identity: {AGENT_ID}")

    return AGENT_ID

# --- PERSISTENCE ---
def install_startup():
    """ Adds the current executable to Windows Startup Registry """
    if platform.system() != "Windows": return

    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "KriplaniBackupAgent"
        exe_path = sys.executable 

        # If running as script (dev), don't install
        if not getattr(sys, 'frozen', False):
            return

        print(f"⚙️ Checking persistence for: {exe_path}")
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            try:
                registry_value, _ = winreg.QueryValueEx(key, app_name)
                if registry_value == exe_path:
                    print("✅ Already in Startup")
                    winreg.CloseKey(key)
                    return
            except FileNotFoundError:
                pass # Key doesn't exist, proceed to write

            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            print("💾 Added to Startup Registry")
        except Exception as e:
            print(f"⚠️ Failed to manage Registry: {e}")
    except ImportError:
        pass

def register_agent():
    """Updates the systems/{uuid}/meta node with host info."""
    
    # Improve IP detection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # doesn't even have to be reachable
        s.connect(('8.8.8.8', 1))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception:
        ip_address = socket.gethostbyname(socket.gethostname())

    meta = {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "version": "2.2.0 (Stable Identity)",
        "ip": ip_address,
        "last_boot": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.reference(f'systems/{AGENT_ID}/meta').update(meta)
    print("📡 Registered System Metadata")

# --- HELPER FUNCTIONS ---

def parse_rclone_size(bytes_int):
    if bytes_int == 0: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_int < 1024:
            return f"{bytes_int:.2f} {unit}"
        bytes_int /= 1024
    return f"{bytes_int:.2f} PB"


def send_email_alert(job_name, status, details_html, recipients_str, smtp_settings):
    """
    Sends email using provided SMTP settings. 
    smtp_settings should be a dict: {server, port, email, password}
    """
    if not recipients_str or not smtp_settings or "xxxx" in smtp_settings.get('password', ''):
        return

    recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]
    if not recipients: return

    sender_email = smtp_settings.get('email')
    sender_password = smtp_settings.get('password')
    smtp_server = smtp_settings.get('server', 'smtp.gmail.com')
    smtp_port = int(smtp_settings.get('port', 587))

    msg = MIMEMultipart()
    msg['From'] = f"Backup Agent <{sender_email}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = f"[{status}] {job_name} - {socket.gethostname()}"

    color = "#10B981" if status == "SUCCESS" else "#EF4444"
    body = f"""
    <html><body style="font-family: sans-serif; color: #333;">
        <div style="border: 1px solid #ddd; border-radius: 8px; overflow: hidden; max-width: 600px;">
          <div style="background-color: {color}; padding: 15px; color: white; text-align: center;">
            <h2 style="margin:0;">{job_name}: {status}</h2>
          </div>
          <div style="padding: 20px;">
            <p><strong>System:</strong> {socket.gethostname()}</p>
            <p><strong>Time:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")}</p>
            <table style="width: 100%; border-collapse: collapse;">{details_html}</table>
          </div>
        </div>
    </body></html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"❌ Email Failed: {e}")





# --- CONFIGURATION ---
def configure_rclone():
    """Confirms 'gdrive' remote exists in rclone.conf, creates it if missing."""
    try:
        # Check if remote exists
        result = subprocess.run([RCLONE_BIN, "listremotes"], capture_output=True, text=True)
        if "gdrive:" in result.stdout:
            print("✅ Rclone remote 'gdrive' found.")
            return

        print("⚙️ Configuring 'gdrive' remote with Service Account...")
        subprocess.run([
            RCLONE_BIN, "config", "create", "gdrive", "drive", 
            "scope", "drive", 
            "service_account_file", KEY_PATH
        ], check=True)
        print("✅ Rclone remote 'gdrive' created.")
    except Exception as e:
        print(f"⚠️ Failed to configure rclone: {e}")

# --- SCHEDULING LOGIC ---
def check_schedule(schedule_config, last_run_iso=None):
    """
    Returns True if the job should run NOW (or needs catch-up).
    
    Args:
        schedule_config: { "type": "daily/monthly", "time": "HH:MM", "day": 1 }
        last_run_iso: ISO format string of last successful run (e.g., "2023-10-27 21:00:00")
        
    Logic:
    1. If run today? -> False
    2. If not run today:
       - Is Now >= Scheduled Time? -> True (Catch-up)
    """
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # 1. Check if already run today
    if last_run_iso:
        try:
            # Parse ISO string "YYYY-MM-DD HH:MM:SS"
            # We only care about the DATE part for "Daily/Monthly" frequency validation
            last_run_dt = datetime.datetime.strptime(last_run_iso.split('.')[0], "%Y-%m-%d %H:%M:%S")
            last_run_date_str = last_run_dt.strftime("%Y-%m-%d")
            
            if last_run_date_str == today_str:
                return False # Already ran today
        except ValueError:
            pass # Invalid format, treat as never run

    # 2. Check Schedule Match
    sched_type = schedule_config.get('type', 'daily')
    sched_time_str = schedule_config.get('time', '00:00')
    
    # Parse Schedule Time
    try:
        sh, sm = map(int, sched_time_str.split(':'))
        scheduled_time_today = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    except:
        return False # Invalid config

    # Is it time yet? (Standard + Catch-up)
    # If now < scheduled_time, we wait.
    if now < scheduled_time_today:
        return False

    if sched_type == 'daily':
        return True # Not run today + Time is passed -> RUN!
    
    if sched_type == 'monthly':
        sched_day = int(schedule_config.get('day', 1))
        
        # Handle "End of Month" logic
        # If user picks 31, and today is Feb 28 (and it's the last day), maybe we run?
        # User requirement: "Warn user... but implement logic".
        # Current Logic: STRICT match on day.
        # If sched_day is 31, and today is Feb 28, it WON'T match.
        
        if now.day == sched_day:
            return True
            
    return False

def perform_backup(job_id, job_config, global_config):
    job_name = job_config.get('name', 'Unknown Job')
    source_path = job_config.get('source_path')

    if not source_path:
        print(f"⚠️ Error: Job '{job_name}' has no Local Source Path configured. Skipping.")
        db.reference(f'runtime_state/{AGENT_ID}/job_states/{job_id}').update({
            "status": "Error",
            "detailed_message": "Configuration Error: Local Source Path is missing."
        })
        return
    
    # Handle Remote Configuration (Folder Path vs Folder ID)
    raw_remote = job_config.get('remote_folder', 'Backups')
    
    # If remote looks like a Google Drive ID (alphanumeric, long, no spaces/slashes usually)
    # 1. Folder IDs are usually ~33 chars.
    # 2. Shared Drive Root IDs are usually ~19 chars (starts with 0A).
    # We use backend connection string syntax: gdrive,root_folder_id=XXX:
    if len(raw_remote) > 15 and "/" not in raw_remote and " " not in raw_remote:
        print(f"🔗 Detected Folder ID: {raw_remote}")
        base_remote = f"gdrive,root_folder_id={raw_remote}:"
        remote_root = "" # Root is determined by ID
    else:
        base_remote = "gdrive:"
        remote_root = raw_remote

    destination_subfolder = job_config.get('destination_subfolder', job_name.replace(" ", "_"))
    
    # Construct paths
    # If base_remote has ID, we append path directly. 
    # e.g. gdrive,root_folder_id=XXX:/Marketing/Current_Mirror
    full_remote_path = f"{remote_root}/{destination_subfolder}".strip("/") 
    
    mirror_path = f"{full_remote_path}/Current_Mirror"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = f"{full_remote_path}/Backup_{timestamp}"

    print(f"\n🚀 Starting Job: {job_name} ({source_path})")
    print(f"   Destination: {base_remote}{backup_path}")

    # Update Job State -> Running
    state_ref = db.reference(f'runtime_state/{AGENT_ID}/job_states/{job_id}')
    state_ref.update({"status": "Running", "detailed_message": "Syncing...", "start_time": timestamp})

    if not os.path.exists(source_path):
        err = f"Source not found: {source_path}"
        state_ref.update({"status": "Error", "detailed_message": err})
        return

    bytes_transferred = 0
    try:
        # 1. Sync
        # We assume the user wants 'Snapshot' style history.
        # Strategy: Sync to Mirror (Incremental), then Copy Mirror to Backup_Timestamp (Server-Side)
        
        process = subprocess.Popen(
            [RCLONE_BIN, "sync", source_path, f"{base_remote}{mirror_path}",
             "--transfers", "8", "--use-json-log", "--stats", "1s"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        # Simple stats monitoring
        last_error_lines = []
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None: break
            if line:
                try:
                    log_entry = json.loads(line)
                    if 'stats' in log_entry: 
                        bytes_transferred = log_entry['stats'].get('bytes', 0)
                    elif 'level' in log_entry and log_entry['level'] == 'error':
                        # Capture structured rclone errors
                        last_error_lines.append(log_entry.get('msg', ''))
                except:
                    # Capture raw non-JSON errors (like auth failure)
                    last_error_lines.append(line.strip())
                    pass
        
        if process.returncode != 0: 
            error_msg = "; ".join(last_error_lines[-3:]) # Last 3 errors
            if not error_msg: error_msg = "Rclone Sync Failed (Unknown Error)"
            raise Exception(error_msg)

        # 2. Snapshot (Copy)
        state_ref.update({"detailed_message": f"Creating Snapshot: Backup_{timestamp}..."})
        subprocess.run([RCLONE_BIN, "copy", f"{base_remote}{mirror_path}", f"{base_remote}{backup_path}",
                        "--server-side-across-configs"], check=True)

        # 3. Retention
        retention = job_config.get('retention', {}).get('days', 60)
        # Note: Retention check needs to run differently if using dynamic connection string?
        # Actually, rclone lsd supports it.
        # We pass the full path relative to the base connection
        enforce_retention(base_remote, full_remote_path, retention)

        # Success
        size_str = parse_rclone_size(bytes_transferred)
        success_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        state_ref.update({
            "status": "Success", 
            "detailed_message": f"Done. {size_str} uploaded to Backup_{timestamp}",
            "last_run": success_time,
            "last_run_timestamp": success_time, # Used for robust scheduling
            "last_size": size_str
        })
        
        # Logs
        log_entry = {
            "timestamp": success_time,
            "job_name": job_name,
            "status": "Success",
            "size": size_str,
            "type": "Scheduled"
        }
        db.reference(f'logs/{AGENT_ID}').push(log_entry)

        # Email
        email_recipients = job_config.get('email_recipients', global_config.get('default_email_recipients', ''))
        smtp_settings = global_config.get('smtp', {})
        details = f"<tr><td>Job:</td><td>{job_name}</td></tr><tr><td>Data:</td><td>{size_str}</td></tr>"
        send_email_alert(job_name, "SUCCESS", details, email_recipients, smtp_settings)

    except Exception as e:
        print(f"❌ Job Failed: {e}")
        state_ref.update({"status": "Error", "detailed_message": str(e)})
        
        # Email Failure
        email_recipients = job_config.get('email_recipients', global_config.get('default_email_recipients', ''))
        smtp_settings = global_config.get('smtp', {})
        send_email_alert(job_name, "FAILURE", f"<tr><td>Error:</td><td>{str(e)}</td></tr>", email_recipients, smtp_settings)

def enforce_retention(base_remote, start_remote_path, retention_days):
    if not retention_days: return
    try:
        keep_days = int(retention_days)
        print(f"🧹 Retention Check: {start_remote_path} (Keep {keep_days} days)")
        
        # List directories
        # Path is {base_remote}{start_remote_path}
        cmd = [RCLONE_BIN, "lsd", f"{base_remote}{start_remote_path}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0: return

        now = datetime.datetime.now()
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if not parts: continue
            folder_name = parts[-1]
            if folder_name == "Current_Mirror": continue

            # Match Backup_YYYY-MM-DD...
            match = re.search(r"Backup_(\d{4}-\d{2}-\d{2})", folder_name)
            if match:
                try:
                    folder_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d")
                    age_days = (now - folder_date).days
                    if age_days > keep_days:
                        print(f"   🗑️ PURGING: {folder_name} ({age_days} days old)...")
                        subprocess.run([RCLONE_BIN, "purge", f"{base_remote}{start_remote_path}/{folder_name}"], check=True)
                except ValueError:
                    continue
    except Exception as e:
        print(f"⚠️ Retention Error: {e}")

# --- MAIN LOOP ---

def main():
    ensure_rclone()
    configure_rclone() # Auto-config gdrive
    get_or_create_identity()
    register_agent()
    install_startup()
    
    print(f"👀 Agent {AGENT_ID} Active. Waiting for instructions...")
    
    # --- STARTUP DELAY ---
    # Protection against Boot Storms.
    # We wait 10 minutes before running any AUTOMATED jobs.
    # Manual triggers will still bypass this because they are checked in the loop.
    print(f"⏳ Agent Startup Delay: Waiting 600s (10m) to allow system to settle...")
    # We break this into chunks so we can still print heartbeats or check manual triggers?
    # For simplicity, let's just sleep, but keep heartbeats triggered? 
    # Actually, user said "cannot Keep the machine inaccessible". 
    # If we sleep 10m, we can't run Manual Jobs.
    # Better approach: Record start_time and enforce delay only on SCHEDULED checks.
    
    agent_start_time = datetime.datetime.now()
    STARTUP_DELAY_SECONDS = 600 # 10 Minutes

    last_processed_minute = ""

    while True:
        try:
            # 1. Existence Check (Kill Switch)
            # If the system node has been deleted by Admin, the agent should decommission itself.
            system_check = db.reference(f'systems/{AGENT_ID}').get()
            if system_check is None:
                print(f"⛔ System ID {AGENT_ID} not found in registry (Deleted by Admin).")
                print("   Agent is decommissioning...")
                sys.exit(0)

            # 2. Heartbeat (Only if system exists)
            db.reference(f'systems/{AGENT_ID}/heartbeat').set(int(time.time()))

            # 3. Fetch Configuration
            global_config = db.reference(f'global_config').get() or {}
            jobs = db.reference(f'configurations/{AGENT_ID}').get() or {}
            
            # Fetch Runtime State to know last run times
            job_states = db.reference(f'runtime_state/{AGENT_ID}/job_states').get() or {}

            # 4. Check Manual Triggers (Control) - BYPASSES DELAY
            manual_trigger_job_id = db.reference(f'control/{AGENT_ID}/trigger_now').get()
            if manual_trigger_job_id:
                # Clear trigger immediately to acknowledge
                db.reference(f'control/{AGENT_ID}/trigger_now').delete()
                if manual_trigger_job_id in jobs:
                    print(f"⚡ Manual Trigger received for {manual_trigger_job_id}")
                    perform_backup(manual_trigger_job_id, jobs[manual_trigger_job_id], global_config)
                elif manual_trigger_job_id == "ALL":
                    for jid, jconf in jobs.items():
                        perform_backup(jid, jconf, global_config)

            # 5. Scheduled Checks - RESPECTS DELAY
            time_since_start = (datetime.datetime.now() - agent_start_time).total_seconds()
            
            if time_since_start < STARTUP_DELAY_SECONDS:
                # Still in startup grace period.
                # We skip schedule checks, but we loop to keep Heartbeat alive.
                # We can print a countdown every minute?
                pass
            else:
                current_minute = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                if current_minute != last_processed_minute:
                    # New minute, check schedules
                    last_processed_minute = current_minute
                    
                    for job_id, job_config in jobs.items():
                        schedule = job_config.get('schedule', {})
                        
                        # Get Last Run for this specific job
                        last_run_str = job_states.get(job_id, {}).get('last_run_timestamp')
                        
                        if check_schedule(schedule, last_run_str):
                            print(f"⏰ Schedule matched for {job_id}")
                            perform_backup(job_id, job_config, global_config)

            # Shorter sleep to be responsive to Manual Triggers
            time.sleep(5)

        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception:
            print(f"Glitch (Unexpected Error):")
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    main()