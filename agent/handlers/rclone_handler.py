from .base_handler import BaseHandler
import subprocess
import os
import json
import datetime
import re
import shutil
import urllib.request
import zipfile
import platform
from firebase_admin import db
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class RcloneHandler(BaseHandler):
    def __init__(self, rclone_bin_path):
        self.RCLONE_BIN = rclone_bin_path

    # --- HELPER METHODS ---
    def _parse_rclone_size(self, bytes_int):
        if bytes_int == 0: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_int < 1024:
                return f"{bytes_int:.2f} {unit}"
            bytes_int /= 1024
        return f"{bytes_int:.2f} PB"

    def _send_email_alert(self, job_name, status, details_html, recipients_str, smtp_settings):
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

    def _enforce_retention(self, base_remote, start_remote_path, retention_days):
        if not retention_days: return
        try:
            keep_days = int(retention_days)
            print(f"🧹 Retention Check: {start_remote_path} (Keep {keep_days} days)")
            
            # List directories
            cmd = [self.RCLONE_BIN, "lsd", f"{base_remote}{start_remote_path}"]
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
                            subprocess.run([self.RCLONE_BIN, "purge", f"{base_remote}{start_remote_path}/{folder_name}"], check=True)
                    except ValueError:
                        continue
        except Exception as e:
            print(f"⚠️ Retention Error: {e}")

    def _resolve_remote_path(self, remote_folder):
        # 1. Detect GCS Bucket (contains hyphens/dots, strictly lowercase usually)
        if "-" in remote_folder or "." in remote_folder or "kriplani" in remote_folder:
             print(f"☁️ Detected GCS Bucket: {remote_folder}")
             return f"gcs:{remote_folder}", ""

        # 2. Detect Google Drive Folder ID (Long alphanumeric, no spaces)
        # Note: GDrive IDs are usually mixed case, GCS is lowercase.
        if len(remote_folder) > 15 and "/" not in remote_folder and " " not in remote_folder:
            print(f"🔗 Detected Folder ID: {remote_folder}")
            return f"gdrive,root_folder_id={remote_folder}:", ""
            
        # 3. Default to GDrive Path
        return "gdrive:", remote_folder

    # --- EXECUTE ---
    def execute(self, job_id, job_config, global_config, agent_id, **kwargs):
        trigger_source = kwargs.get('trigger_source', 'manual')
        job_name = job_config.get('name', 'Unknown Job')
        source_path = job_config.get('source_path')
        state_ref = db.reference(f'runtime_state/{agent_id}/job_states/{job_id}')

        if not source_path:
            err = "Configuration Error: Local Source Path is missing."
            print(f"⚠️ Error: Job '{job_name}' has no Local Source Path configured. Skipping.")
            state_ref.update({"status": "Error", "detailed_message": err})
            return {"status": "Error", "detailed_message": err}
        
        base_remote, remote_root = self._resolve_remote_path(job_config.get('remote_folder', 'Backups'))

        destination_subfolder = job_config.get('destination_subfolder', job_name.replace(" ", "_"))
        full_remote_path = f"{remote_root}/{destination_subfolder}".strip("/") 
        mirror_path = f"{full_remote_path}/Current_Mirror"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = f"{full_remote_path}/Backup_{timestamp}"

        print(f"\n🚀 Starting Job: {job_name} ({source_path}) [Trigger: {trigger_source}]")
        print(f"   Destination: {base_remote}{backup_path}")

        # Update Job State -> Running
        state_ref.update({"status": "Running", "detailed_message": "Syncing...", "start_time": timestamp})

        if not os.path.exists(source_path):
            err = f"Source not found: {source_path}"
            state_ref.update({"status": "Error", "detailed_message": err})
            return {"status": "Error", "detailed_message": err}

        bytes_transferred = 0
        try:
            # 1. Sync
            process = subprocess.Popen(
                [self.RCLONE_BIN, "sync", source_path, f"{base_remote}{mirror_path}",
                 "--transfers", "8", "--use-json-log", "--stats", "1s", 
                 "--retries", "5", "--retries-sleep", "30s"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            
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
                            last_error_lines.append(log_entry.get('msg', ''))
                    except ValueError:
                        last_error_lines.append(line.strip())
            
            if process.returncode != 0: 
                error_msg = "; ".join(last_error_lines[-3:])
                if not error_msg: error_msg = "Rclone Sync Failed (Unknown Error)"
                raise RuntimeError(error_msg)

            # 2. Snapshot
            state_ref.update({"detailed_message": f"Creating Snapshot: Backup_{timestamp}..."})
            subprocess.run([self.RCLONE_BIN, "copy", f"{base_remote}{mirror_path}", f"{base_remote}{backup_path}",
                            "--server-side-across-configs"], check=True)

            # 3. Retention
            retention = job_config.get('retention', {}).get('days', 60)
            self._enforce_retention(base_remote, full_remote_path, retention)

            # Success
            size_str = self._parse_rclone_size(bytes_transferred)
            success_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            result = {
                "status": "Success", 
                "detailed_message": f"Done. {size_str} uploaded to Backup_{timestamp}",
                "last_run": success_time,
                "last_run_timestamp": success_time,
                "last_size": size_str
            }

            # ONLY update last_scheduled_run if this was a scheduled trigger
            if trigger_source == 'scheduled':
                result["last_scheduled_run_timestamp"] = success_time

            state_ref.update(result)
            
            # Logs
            log_entry = {
                "timestamp": success_time,
                "job_id": job_id,
                "job_name": job_name,
                "status": "Success",
                "size": size_str,
                "type": "Scheduled" if trigger_source == 'scheduled' else "Manual"
            }
            db.reference(f'logs/{agent_id}').push(log_entry)

            # Email
            email_recipients = job_config.get('email_recipients', global_config.get('default_email_recipients', ''))
            smtp_settings = global_config.get('smtp', {})
            details = f"<tr><td>Job:</td><td>{job_name}</td></tr><tr><td>Data:</td><td>{size_str}</td></tr>"
            self._send_email_alert(job_name, "SUCCESS", details, email_recipients, smtp_settings)

            return result

        except Exception as e:
            print(f"❌ Job Failed: {e}")
            state_ref.update({"status": "Error", "detailed_message": str(e)})
            
            email_recipients = job_config.get('email_recipients', global_config.get('default_email_recipients', ''))
            smtp_settings = global_config.get('smtp', {})
            self._send_email_alert(job_name, "FAILURE", f"<tr><td>Error:</td><td>{str(e)}</td></tr>", email_recipients, smtp_settings)
            
            return {"status": "Error", "detailed_message": str(e)}
