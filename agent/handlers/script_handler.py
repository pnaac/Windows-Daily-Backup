import subprocess
import os
import tempfile
import datetime
from firebase_admin import db
from .base_handler import BaseHandler

class ScriptHandler(BaseHandler):
    def execute(self, job_id, job_config, global_config, agent_id, **kwargs):
        """
        Executes a script provided in the job configuration.
        """
        trigger_source = kwargs.get('trigger_source', 'manual')
        job_name = job_config.get('name', 'Unknown Script')
        payload = job_config.get('payload', {})
        interpreter = payload.get('interpreter', 'powershell').lower()
        script_content = payload.get('script_content', '')
        timeout = int(payload.get('timeout', 300))

        state_ref = db.reference(f'runtime_state/{agent_id}/job_states/{job_id}')
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n📜 Starting Script Job: {job_name} [Trigger: {trigger_source}]")
        state_ref.update({"status": "Running", "detailed_message": "Executing script...", "start_time": timestamp})

        if not script_content:
            err = "No script content provided."
            state_ref.update({"status": "Error", "detailed_message": err})
            return {"status": "Error", "detailed_message": err}

        # Determine file extension and execution command
        ext = ".ps1"
        cmd_prefix = ["powershell", "-ExecutionPolicy", "Bypass", "-File"]
        
        if interpreter == "python":
            ext = ".py"
            cmd_prefix = ["python"]
        elif interpreter == "cmd" or interpreter == "batch":
            ext = ".bat"
            cmd_prefix = ["cmd", "/c"]
        elif interpreter == "bash":
            ext = ".sh"
            cmd_prefix = ["bash"]

        # Create Temp File
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as tmp:
                tmp.write(script_content)
                tmp_path = tmp.name
            
            print(f"   Executing: {tmp_path} ({interpreter})")
            
            # Execute
            process = subprocess.run(
                cmd_prefix + [tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Cleanup
            try:
                os.remove(tmp_path)
            except:
                pass

            output = process.stdout.strip()
            error = process.stderr.strip()
            
            # Combined Output for logging
            logs = f"STDOUT:\n{output}\n\nSTDERR:\n{error}" if error else output

            if process.returncode == 0:
                print("✅ Script Finished Successfully")
                success_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result = {
                    "status": "Success",
                    "detailed_message": "Script execution successful.",
                    "last_run": success_time,
                    "last_run_timestamp": success_time,
                    "last_size": "N/A" # Scripts don't necessarily transfer data
                }

                if trigger_source == 'scheduled':
                    result["last_scheduled_run_timestamp"] = success_time

                state_ref.update(result)
                
                # Push Log
                db.reference(f'logs/{agent_id}').push({
                    "timestamp": success_time,
                    "job_name": job_name,
                    "status": "Success",
                    "type": "Scheduled" if trigger_source == 'scheduled' else "Manual",
                    "details": logs[:2000] # Truncate logs to avoid DB bloat
                })
                
                return result
            else:
                print(f"❌ Script Failed with Code {process.returncode}")
                # Log the error
                err_msg = f"Exit Code {process.returncode}. STDERR: {error[:500]}"
                state_ref.update({"status": "Error", "detailed_message": err_msg})
                
                db.reference(f'logs/{agent_id}').push({
                    "timestamp": timestamp,
                    "job_name": job_name,
                    "status": "Error",
                    "type": "Scheduled" if trigger_source == 'scheduled' else "Manual",
                    "details": logs[:2000]
                })

                return {"status": "Error", "detailed_message": err_msg}

        except subprocess.TimeoutExpired:
            print("❌ Script Timeout")
            err_msg = f"Script execution timed out after {timeout} seconds."
            state_ref.update({"status": "Error", "detailed_message": err_msg})
            return {"status": "Error", "detailed_message": err_msg}
            
        except Exception as e:
            print(f"❌ Script Execution Error: {e}")
            state_ref.update({"status": "Error", "detailed_message": str(e)})
            return {"status": "Error", "detailed_message": str(e)}
