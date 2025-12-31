import firebase_admin
from firebase_admin import credentials, db
import time
import subprocess
import datetime
import os
import sys
import json
import uuid
import platform
import socket
import traceback
import urllib.request
import zipfile
import shutil

# Import Handlers
from handlers.rclone_handler import RcloneHandler
from handlers.script_handler import ScriptHandler

# --- CONFIGURATION ---
RCLONE_REMOTE = "gdrive"
RCLONE_VERSION = "v1.65.0"
RCLONE_URL = f"https://downloads.rclone.org/{RCLONE_VERSION}/rclone-{RCLONE_VERSION}-windows-amd64.zip"

# --- GLOBAL STATE ---
AGENT_ID = None
RCLONE_BIN = "rclone" # Default to PATH, updated by ensure_rclone
KEY_PATH = "serviceAccountKey.json"

# 2. Identity Persistence
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
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- DEPENDENCY MANAGEMENT ---
def ensure_rclone():
    """ 
    Checks if rclone is available. 
    1. Checks bundled resource.
    2. Checks local folder.
    3. Checks system PATH.
    4. Downloads if missing (Windows only).
    """
    global RCLONE_BIN
    
    # 1. Check Bundled Resource
    bundled_bin = get_resource_path("rclone.exe")
    if os.path.exists(bundled_bin):
        print(f"✅ Found bundled Rclone: {bundled_bin}")
        RCLONE_BIN = bundled_bin
        return

    # 2. Check Local
    local_bin = os.path.join(os.getcwd(), "rclone.exe" if platform.system() == "Windows" else "rclone")
    if os.path.exists(local_bin):
        print(f"✅ Found local rclone: {local_bin}")
        RCLONE_BIN = local_bin
        return

    # 3. Check PATH
    if shutil.which("rclone"):
        print(f"✅ Found rclone in PATH")
        RCLONE_BIN = "rclone"
        return

    # 4. Download (Windows Only)
    if platform.system() == "Windows":
        print(f"⬇️ Rclone not found. Downloading {RCLONE_VERSION}...")
        try:
            zip_path = "rclone.zip"
            urllib.request.urlretrieve(RCLONE_URL, zip_path)
            
            print("📦 Extracting Rclone...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("rclone_temp")
            
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
        # Check bundled path just in case
        bundled_key = get_resource_path(KEY_PATH)
        if os.path.exists(bundled_key):
             KEY_PATH = bundled_key
        else:
            print(f"❌ CRITICAL: serviceAccountKey.json not found at {KEY_PATH}")
            sys.exit(1)

    cred = credentials.Certificate(KEY_PATH)
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

        if not getattr(sys, 'frozen', False):
            return

        print(f"⚙️ Checking persistence for: {exe_path}")
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            try:
                registry_value, _ = winreg.QueryValueEx(key, app_name)
                if registry_value == exe_path:
                    # print("✅ Already in Startup")
                    winreg.CloseKey(key)
                    return
            except FileNotFoundError:
                pass 

            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            print("💾 Added to Startup Registry")
        except Exception as e:
            print(f"⚠️ Failed to manage Registry: {e}")
    except ImportError:
        pass

def register_agent():
    """Updates the systems/{uuid}/meta node with host info."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception:
        ip_address = socket.gethostbyname(socket.gethostname())

    meta = {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "version": "3.0.0 (Cloud Control)",
        "ip": ip_address,
        "last_boot": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.reference(f'systems/{AGENT_ID}/meta').update(meta)
    print("📡 Registered System Metadata")

# --- CONFIGURATION (Rclone) ---
def configure_rclone():
    """Confirms 'gdrive' remote exists in rclone.conf, creates it if missing."""
    try:
        result = subprocess.run([RCLONE_BIN, "listremotes"], capture_output=True, text=True)
        if "gdrive:" in result.stdout:
            # print("✅ Rclone remote 'gdrive' found.")
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
    """ Returns True if the job should run NOW """
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    if last_run_iso:
        try:
            last_run_dt = datetime.datetime.strptime(last_run_iso.split('.')[0], "%Y-%m-%d %H:%M:%S")
            last_run_date_str = last_run_dt.strftime("%Y-%m-%d")
            
            if last_run_date_str == today_str:
                return False 
        except ValueError:
            pass 

    sched_type = schedule_config.get('type', 'daily')
    sched_time_str = schedule_config.get('time', '00:00')
    
    try:
        sh, sm = map(int, sched_time_str.split(':'))
        scheduled_time_today = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    except:
        return False 

    if now < scheduled_time_today:
        return False

    if sched_type == 'daily':
        return True 
    
    if sched_type == 'monthly':
        sched_day = int(schedule_config.get('day', 1))
        # Logic: If today is the day, RUN.
        if now.day == sched_day:
            return True
            
    return False

# --- JOB DISPATCHER ---
def handle_job(job_id, job_config, global_config, handlers):
    """
    Routes the job to the appropriate handler based on 'type'.
    """
    job_type = job_config.get('type', 'RCLONE_SYNC') # Default to existing behavior
    
    if job_type == 'RCLONE_SYNC':
        return handlers['rclone'].execute(job_id, job_config, global_config, AGENT_ID)
    elif job_type == 'EXEC_SCRIPT':
        return handlers['script'].execute(job_id, job_config, global_config, AGENT_ID)
    else:
        print(f"⚠️ Unknown Job Type: {job_type}")
        return {"status": "Error", "detailed_message": f"Unknown Job Type: {job_type}"}

# --- MAIN LOOP ---
def main():
    ensure_rclone()
    configure_rclone() 
    get_or_create_identity()
    register_agent()
    install_startup()
    
    # Initialize Handlers
    handlers = {
        'rclone': RcloneHandler(RCLONE_BIN),
        'script': ScriptHandler()
    }
    
    print(f"👀 Agent {AGENT_ID} Active. Waiting for instructions...")
    
    agent_start_time = datetime.datetime.now()
    STARTUP_DELAY_SECONDS = 600 # 10 Minutes
    last_processed_minute = ""

    while True:
        try:
            # 1. Existence Check
            system_check = db.reference(f'systems/{AGENT_ID}').get()
            if system_check is None:
                print(f"⛔ System ID {AGENT_ID} not found in registry (Deleted by Admin).")
                print("   Agent is decommissioning...")
                sys.exit(0)

            # 2. Heartbeat
            db.reference(f'systems/{AGENT_ID}/heartbeat').set(int(time.time()))

            # 3. Fetch Configuration
            global_config = db.reference(f'global_config').get() or {}
            jobs = db.reference(f'configurations/{AGENT_ID}').get() or {}
            job_states = db.reference(f'runtime_state/{AGENT_ID}/job_states').get() or {}

            # 4. Check Manual Triggers (Control) - BYPASSES DELAY
            manual_trigger_job_id = db.reference(f'control/{AGENT_ID}/trigger_now').get()
            if manual_trigger_job_id:
                db.reference(f'control/{AGENT_ID}/trigger_now').delete()
                
                if manual_trigger_job_id == "ALL":
                    for jid, jconf in jobs.items():
                        handle_job(jid, jconf, global_config, handlers)
                elif manual_trigger_job_id in jobs:
                    print(f"⚡ Manual Trigger received for {manual_trigger_job_id}")
                    handle_job(manual_trigger_job_id, jobs[manual_trigger_job_id], global_config, handlers)
                else:
                    # Could be ad-hoc job payload? For now only configured jobs.
                    pass

            # 5. Scheduled Checks - RESPECTS DELAY
            time_since_start = (datetime.datetime.now() - agent_start_time).total_seconds()
            
            if time_since_start < STARTUP_DELAY_SECONDS:
                pass
            else:
                current_minute = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                if current_minute != last_processed_minute:
                    last_processed_minute = current_minute
                    
                    for job_id, job_config in jobs.items():
                        schedule = job_config.get('schedule', {})
                        last_run_str = job_states.get(job_id, {}).get('last_run_timestamp')
                        
                        if check_schedule(schedule, last_run_str):
                            print(f"⏰ Schedule matched for {job_id}")
                            handle_job(job_id, job_config, global_config, handlers)

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