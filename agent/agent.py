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
import threading
import logging
from logging.handlers import RotatingFileHandler

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
ACTIVE_JOBS = {} # Track running threads: {job_id: thread_obj}

# 2. Identity Persistence & Logging
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
LOG_FILE = os.path.join(config_dir, "agent.log")

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("Agent")

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
    global RCLONE_BIN
    
    # 1. Check Bundled Resource
    bundled_bin = get_resource_path("rclone.exe")
    if os.path.exists(bundled_bin):
        log.info(f"✅ Found bundled Rclone: {bundled_bin}")
        RCLONE_BIN = bundled_bin
        return

    # 2. Check Local
    local_bin = os.path.join(os.getcwd(), "rclone.exe" if platform.system() == "Windows" else "rclone")
    if os.path.exists(local_bin):
        log.info(f"✅ Found local rclone: {local_bin}")
        RCLONE_BIN = local_bin
        return

    # 3. Check PATH
    if shutil.which("rclone"):
        log.info(f"✅ Found rclone in PATH")
        RCLONE_BIN = "rclone"
        return

    # 4. Download (Windows Only)
    if platform.system() == "Windows":
        log.info(f"⬇️ Rclone not found. Downloading {RCLONE_VERSION}...")
        try:
            zip_path = "rclone.zip"
            urllib.request.urlretrieve(RCLONE_URL, zip_path)
            
            log.info("📦 Extracting Rclone...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("rclone_temp")
            
            extracted_folder = f"rclone-{RCLONE_VERSION}-windows-amd64"
            src = os.path.join("rclone_temp", extracted_folder, "rclone.exe")
            shutil.move(src, "rclone.exe")
            
            # Cleanup
            os.remove(zip_path)
            shutil.rmtree("rclone_temp")
            
            RCLONE_BIN = os.path.abspath("rclone.exe")
            log.info(f"✅ Rclone installed to: {RCLONE_BIN}")
        except Exception as e:
            log.error(f"❌ Failed to download rclone: {e}")
            log.warning("⚠️ Please install rclone manually and add to PATH.")
    else:
         log.warning("⚠️ Rclone not found in PATH. Please install it (brew install rclone / apt install rclone).")


# --- FIREBASE INIT ---
try:
    if not os.path.exists(KEY_PATH):
        bundled_key = get_resource_path(KEY_PATH)
        if os.path.exists(bundled_key):
             KEY_PATH = bundled_key
        else:
            log.critical(f"❌ CRITICAL: serviceAccountKey.json not found at {KEY_PATH}")
            sys.exit(1)

    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://kriplani-builders-default-rtdb.asia-southeast1.firebasedatabase.app' 
    })
    log.info("✅ Connected to Firebase Command Center")
except Exception as e:
    log.critical(f"❌ Failed to connect to Firebase: {e}")
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
        log.info(f"🆕 Generate New Agent Identity: {AGENT_ID}")
    else:
        log.info(f"🆔 Loaded Agent Identity: {AGENT_ID}")

    return AGENT_ID

# --- PERSISTENCE ---
def install_startup():
    """ 
    Legacy Registry method. 
    The preferred method is now the Scheduled Task (install_service.bat).
    We kept this as a fallback for non-admin users.
    """
    if platform.system() != "Windows": return

    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "KriplaniBackupAgent"
        exe_path = sys.executable 

        if not getattr(sys, 'frozen', False):
            return

        log.debug(f"⚙️ Checking persistence for: {exe_path}")
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            try:
                registry_value, _ = winreg.QueryValueEx(key, app_name)
                if registry_value == exe_path:
                    winreg.CloseKey(key)
                    return
            except FileNotFoundError:
                pass 

            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            log.info("💾 Added to Startup Registry (Fallback)")
        except Exception as e:
            log.warning(f"⚠️ Failed to manage Registry: {e}")
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
        "version": "3.1.0 (Enterprise Threading)",
        "ip": ip_address,
        "last_boot": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.reference(f'systems/{AGENT_ID}/meta').update(meta)
    log.info("📡 Registered System Metadata")

# --- CONFIGURATION (Rclone) ---
def configure_rclone():
    try:
        result = subprocess.run([RCLONE_BIN, "listremotes"], capture_output=True, text=True)
        if "gdrive:" in result.stdout:
            return

        log.info("⚙️ Configuring 'gdrive' remote with Service Account...")
        subprocess.run([
            RCLONE_BIN, "config", "create", "gdrive", "drive", 
            "scope", "drive", 
            "service_account_file", KEY_PATH
        ], check=True)
        log.info("✅ Rclone remote 'gdrive' created.")
    except Exception as e:
        log.error(f"⚠️ Failed to configure rclone: {e}")

# --- SCHEDULING LOGIC ---
def reset_stuck_jobs():
    """ Runs on startup to clear any 'Running' states from a previous crash. """
    try:
        runtime_ref = db.reference(f'runtime_state/{AGENT_ID}/job_states')
        states = runtime_ref.get() or {}
        
        updates = {}
        for job_id, state in states.items():
            if state.get('status') == 'Running':
                log.warning(f"⚠️ Found stuck job '{job_id}'. Marking as Interrupted.")
                updates[f'{job_id}/status'] = 'Interrupted'
                updates[f'{job_id}/detailed_message'] = 'Agent restarted while job was running (Power Loss/Crash).'
        
        if updates:
            runtime_ref.update(updates)
            log.info(f"🧹 Cleaned up {len(updates)} stuck jobs.")
    except Exception as e:
        log.error(f"⚠️ Failed to reset stuck jobs: {e}")

def check_schedule(schedule_config, last_run_iso=None):
    """ Returns True if the job should run NOW """
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_month_str = now.strftime("%Y-%m")
    
    last_run_date_str = None
    last_run_month_str = None

    if last_run_iso:
        try:
            last_run_dt = datetime.datetime.strptime(last_run_iso.split('.')[0], "%Y-%m-%d %H:%M:%S")
            last_run_date_str = last_run_dt.strftime("%Y-%m-%d")
            last_run_month_str = last_run_dt.strftime("%Y-%m")
        except ValueError:
            pass 

    sched_type = schedule_config.get('type', 'daily')
    sched_time_str = schedule_config.get('time', '00:00')
    
    try:
        sh, sm = map(int, sched_time_str.split(':'))
        scheduled_time_today = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    except:
        return False 

    # If currently before the scheduled time, don't run
    if now < scheduled_time_today:
        return False

    # DAILY LOGIC
    if sched_type == 'daily':
        # Run if we haven't run today yet
        if last_run_date_str == today_str:
            return False
        return True 
    
    # MONTHLY LOGIC
    if sched_type == 'monthly':
        sched_day = int(schedule_config.get('day', 1))
        
        # 1. Must be the correct day (or passed it, if catch up allowed)
        if now.day < sched_day:
            return False
            
        # 2. Check if already run THIS MONTH
        if last_run_month_str == current_month_str:
            return False
            
        return True
            
    return False

# --- JOB DISPATCHER ---
def _job_thread_wrapper(job_id, job_config, global_config, handlers):
    """ Wrapped function to run in thread and clean up ACTIVE_JOBS on exit """
    try:
        job_type = job_config.get('type', 'RCLONE_SYNC')
        if job_type == 'RCLONE_SYNC':
            handlers['rclone'].execute(job_id, job_config, global_config, AGENT_ID)
        elif job_type == 'EXEC_SCRIPT':
            handlers['script'].execute(job_id, job_config, global_config, AGENT_ID)
        else:
            log.warning(f"⚠️ Unknown Job Type: {job_type}")
    except Exception as e:
        log.error(f"Error in job {job_id}: {e}")
        traceback.print_exc()
    finally:
        # Remove from active jobs
        if job_id in ACTIVE_JOBS:
            del ACTIVE_JOBS[job_id]
        log.info(f"🏁 Job Finished: {job_id}")

def handle_job(job_id, job_config, global_config, handlers):
    """
    Routes the job to the appropriate handler in a separate thread.
    """
    if job_id in ACTIVE_JOBS:
        if ACTIVE_JOBS[job_id].is_alive():
            log.info(f"⏳ Job {job_id} is already running. Skipping trigger.")
            return
        else:
            # Clean up dead thread reference
            del ACTIVE_JOBS[job_id]

    log.info(f"🚀 Spawning thread for Job {job_id}")
    t = threading.Thread(target=_job_thread_wrapper, args=(job_id, job_config, global_config, handlers))
    t.daemon = True # Allow agent to exit even if thread is running
    t.start()
    ACTIVE_JOBS[job_id] = t
    

# --- MAIN LOOP ---
def main():
    log.info("--- STARTING AGENT ---")
    ensure_rclone()
    configure_rclone() 
    get_or_create_identity()
    register_agent()
    install_startup()
    reset_stuck_jobs()
    
    # Initialize Handlers
    handlers = {
        'rclone': RcloneHandler(RCLONE_BIN),
        'script': ScriptHandler()
    }
    
    log.info(f"👀 Agent {AGENT_ID} Active. Waiting for instructions...")
    
    agent_start_time = datetime.datetime.now()
    STARTUP_DELAY_SECONDS = 60 # Reduced to 1 minute for faster feedback in Enterprise mode? No keep 10m but override locally.
    # Actually keep 10 mins as per user req, but let's make it 60s for now to be compassionate to the user testing.
    # Reverting to 600 for production safety
    STARTUP_DELAY_SECONDS = 600 

    last_processed_minute = ""

    while True:
        try:
            # 1. Existence Check
            system_check = db.reference(f'systems/{AGENT_ID}').get()
            if system_check is None:
                log.warning(f"⛔ System ID {AGENT_ID} not found in registry (Deleted by Admin).")
                log.warning("   Agent is decommissioning...")
                sys.exit(0)

            # 2. Heartbeat (Vital for "Online" status)
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
                    log.info(f"⚡ Manual Trigger received for {manual_trigger_job_id}")
                    handle_job(manual_trigger_job_id, jobs[manual_trigger_job_id], global_config, handlers)

            # 5. Scheduled Checks - RESPECTS DELAY
            time_since_start = (datetime.datetime.now() - agent_start_time).total_seconds()
            
            if time_since_start < STARTUP_DELAY_SECONDS:
                # log.debug("Startup delay active...")
                pass
            else:
                current_minute = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                if current_minute != last_processed_minute:
                    last_processed_minute = current_minute
                    
                    for job_id, job_config in jobs.items():
                        schedule = job_config.get('schedule', {})
                        last_run_str = job_states.get(job_id, {}).get('last_run_timestamp')
                        
                        if check_schedule(schedule, last_run_str):
                            log.info(f"⏰ Schedule matched for {job_id}")
                            handle_job(job_id, job_config, global_config, handlers)

            # 6. Thread Monitoring
            # (Optional) Log active threads count if changed
            
            time.sleep(5)

        except KeyboardInterrupt:
            log.info("\nExiting...")
            sys.exit(0)
        except Exception:
            log.error(f"Glitch (Unexpected Error):")
            log.error(traceback.format_exc())
            time.sleep(10)

if __name__ == "__main__":
    main()