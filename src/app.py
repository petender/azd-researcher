from flask import Flask, render_template, request, jsonify
from flask import Response
import threading
import subprocess
import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
import uuid
import time

from azure.storage.blob import BlobServiceClient as SyncBlobServiceClient

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")

# Globals to track multiple concurrent runs
run_lock = threading.Lock()
runs = {}  # mapping: run_id -> { thread, process, start, end, returncode, log, status }


def get_research_python() -> str:
    """Return a Python executable path to run the researcher script.

    Priority:
    1. RESEARCH_PYTHON env var (if exists)
    2. sys.executable (Azure App Service)
    3. Infer from installed azure.ai.agents module location
    """
    # 1) explicit env override
    env_path = os.getenv("RESEARCH_PYTHON")
    if env_path:
        p = Path(env_path)
        if p.exists():
            logger.info(f"Using RESEARCH_PYTHON: {env_path}")
            return str(p)

    # 2) Use sys.executable (works best in Azure App Service)
    python_exe = sys.executable
    logger.info(f"Using sys.executable: {python_exe}")
    return python_exe


def run_research_script(run_id: str, script_path: Path, log_path: Path, research_content: str = None) -> None:
    """Start the deep research script for a specific run_id and update runs metadata."""
    logger.info(f"Starting research script for run_id: {run_id}")
    logger.info(f"Script path: {script_path}")
    logger.info(f"Log path: {log_path}")
    logger.info(f"Research content length: {len(research_content) if research_content else 0}")
    
    try:
        with run_lock:
            runs[run_id]["start"] = datetime.now(timezone.utc).isoformat()
            runs[run_id]["end"] = None
            runs[run_id]["returncode"] = None
            runs[run_id]["status"] = "running"

        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write initial log entry
        with open(log_path, "w", encoding="utf-8") as log_fp:
            log_fp.write(f"Starting research run {run_id} at {datetime.now(timezone.utc).isoformat()}\n")
            log_fp.write(f"Python executable: {get_research_python()}\n")
            log_fp.write(f"Script path: {script_path}\n")
            log_fp.write(f"Working directory: {script_path.parent}\n")
            log_fp.write(f"Research content length: {len(research_content) if research_content else 0}\n")
            log_fp.write("=" * 80 + "\n")
            log_fp.flush()

        with open(log_path, "ab") as log_fp:
            python_exe = get_research_python()
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            # Build command with research content as argument if provided
            cmd = [python_exe, "-u", str(script_path)]
            if research_content:
                cmd.append(research_content)
            
            logger.info(f"Running command: {' '.join(cmd[:2])} [content]")

            proc = subprocess.Popen(
                cmd,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(script_path.parent),
                env=env,
                text=False  # Keep binary mode for consistent encoding
            )

            with run_lock:
                runs[run_id]["process"] = proc

            returncode = proc.wait()
            logger.info(f"Process finished with return code: {returncode}")

        with run_lock:
            runs[run_id]["end"] = datetime.now(timezone.utc).isoformat()
            runs[run_id]["returncode"] = returncode
            runs[run_id]["status"] = "completed" if returncode == 0 else "failed"
            
    except Exception as ex:
        logger.error(f"Exception in run_research_script: {ex}", exc_info=True)
        # record failure in the run metadata and write the exception to the log
        try:
            with open(log_path, "ab") as log_fp:
                error_msg = f"\nException while running researcher: {ex}\n"
                log_fp.write(error_msg.encode("utf-8", errors="replace"))
        except Exception as log_ex:
            logger.error(f"Failed to write error to log: {log_ex}")
        with run_lock:
            runs[run_id]["end"] = datetime.now(timezone.utc).isoformat()
            runs[run_id]["returncode"] = -1
            runs[run_id]["status"] = "failed"


def _get_sync_blob_service_client():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

    if not conn_str:
        if account_name and account_key:
            conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
        else:
            return None
    try:
        return SyncBlobServiceClient.from_connection_string(conn_str)
    except Exception:
        return None


@app.route("/", methods=["GET"])
def index():
    # Show whether any runs are currently running
    with run_lock:
        running = any((r.get("process") and getattr(r["process"], "poll", lambda: 1)() is None) for r in runs.values())
    return render_template("index.html", running=running, last_run=None)


@app.route("/start", methods=["POST"])
def start():
    # Create a unique run id, prepare a per-run log file, and start the researcher in a background thread
    logger.info("Received start request")
    
    script_path = Path(__file__).resolve().parent / "split_deepresearcher_to_blob.py"
    logger.info(f"Script path: {script_path}")
    logger.info(f"Script exists: {script_path.exists()}")
    
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return jsonify({"status": "missing_script", "detail": str(script_path)}), 500

    # Get research content from JSON payload
    research_content = None
    if request.is_json:
        data = request.get_json()
        research_content = data.get('research_content', '').strip() if data else None
        logger.info(f"Received research content: {len(research_content) if research_content else 0} characters")
    
    if not research_content:
        logger.warning("No research content provided")
        return jsonify({"status": "missing_content", "detail": "Research content is required"}), 400

    # Use a more reliable temp directory for Azure App Service
    logs_dir = Path(os.getenv('TEMP', '/tmp')) / 'research_logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Logs directory: {logs_dir}")

    run_id = uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = logs_dir / f"{run_id}_{timestamp}.log"
    logger.info(f"Log file: {log_path}")

    with run_lock:
        runs[run_id] = {
            "thread": None,
            "process": None,
            "start": None,
            "end": None,
            "returncode": None,
            "log": str(log_path),
            "status": "queued",
            "research_content": research_content[:100] + "..." if len(research_content) > 100 else research_content,  # Store truncated version for logging
        }

    logger.info(f"Starting thread for run_id: {run_id}")
    thread = threading.Thread(target=run_research_script, args=(run_id, script_path, log_path, research_content), daemon=True)
    with run_lock:
        runs[run_id]["thread"] = thread
    thread.start()
    
    logger.info(f"Research started with run_id: {run_id}")
    return jsonify({"status": "started", "run_id": run_id, "log": str(log_path)}), 202


@app.route("/status", methods=["GET"])
def status():
    """Return status for a specific run if run_id provided, otherwise a summary of runs."""
    run_id = request.args.get("run_id")
    with run_lock:
        if run_id:
            meta = runs.get(run_id)
            if not meta:
                return jsonify({"error": "run_not_found"}), 404
            # Return a JSON-safe subset of metadata
            safe_meta = {k: v for k, v in meta.items() if k not in ("process", "thread")}
            # Determine running flag
            proc = meta.get("process")
            running = bool(proc and getattr(proc, "poll", lambda: 1)() is None)
            safe_meta.update({"running": running})
            return jsonify(safe_meta)

        # no run_id: return brief summary
        summary = {rid: {"status": r.get("status"), "start": r.get("start"), "log": r.get("log")} for rid, r in runs.items()}
    return jsonify({"runs": summary})


@app.route("/log", methods=["GET"])
def get_log_tail():
    """Return the tail (last N bytes) of the run-specific log file as plain text.
    Query params: run_id (required), bytes (optional, default=10000)
    """
    run_id = request.args.get("run_id")
    if not run_id:
        return jsonify({"error": "missing run_id"}), 400

    with run_lock:
        meta = runs.get(run_id)
        if not meta:
            return jsonify({"error": "run_not_found"}), 404
        log_path = meta.get("log")

    path = Path(log_path)
    logger.info(f"Reading log from: {path}")
    logger.info(f"Log file exists: {path.exists()}")
    
    if not path.exists():
        # Return helpful message instead of empty response
        return f"Log file not found: {path}\nRun status: {meta.get('status', 'unknown')}", 200, {"Content-Type": "text/plain; charset=utf-8"}

    try:
        tail_bytes = int(request.args.get("bytes", "10000"))
    except Exception:
        tail_bytes = 10000

    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - tail_bytes)
            f.seek(start)
            data = f.read().decode("utf-8", errors="replace")
        
        logger.info(f"Read {len(data)} characters from log file")
        return data, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as ex:
        logger.error(f"Error reading log file {path}: {ex}")
        return f"Error reading log: {ex}\nPath: {path}\nExists: {path.exists()}", 500


@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to help diagnose Azure App Service issues."""
    info = {
        'python_executable': sys.executable,
        'working_directory': os.getcwd(),
        'app_file_location': str(Path(__file__).resolve()),
        'script_path': str(Path(__file__).resolve().parent / "split_deepresearcher_to_blob.py"),
        'script_exists': (Path(__file__).resolve().parent / "split_deepresearcher_to_blob.py").exists(),
        'temp_dir': os.getenv('TEMP', '/tmp'),
        'environment_vars': {
            'PROJECT_ENDPOINT': os.getenv('PROJECT_ENDPOINT', 'Not set'),
            'AZURE_STORAGE_ACCOUNT_NAME': os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'Not set'),
            'BING_RESOURCE_NAME': os.getenv('BING_RESOURCE_NAME', 'Not set'),
            'MODEL_DEPLOYMENT_NAME': os.getenv('MODEL_DEPLOYMENT_NAME', 'Not set'),
            'DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME': os.getenv('DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME', 'Not set'),
        },
        'active_runs': len(runs),
        'runs_summary': {run_id: {'status': meta.get('status'), 'start': meta.get('start')} for run_id, meta in runs.items()}
    }
    return jsonify(info)


@app.route('/blobs', methods=['GET'])
def list_blobs():
    run_folder = request.args.get('run_folder')
    if not run_folder:
        return jsonify({'error': 'missing run_folder'}), 400

    client = _get_sync_blob_service_client()
    if not client:
        return jsonify({'error': 'no_storage_credentials'}), 500

    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'research-summaries')
    container_client = client.get_container_client(container_name)

    items = []
    try:
        for blob in container_client.list_blobs(name_starts_with=f"{run_folder}/"):
            items.append({'name': blob.name, 'size': getattr(blob, 'size', None), 'last_modified': getattr(blob, 'last_modified', None).isoformat() if getattr(blob, 'last_modified', None) else None})
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500

    return jsonify({'blobs': items})


@app.route('/blob/download', methods=['GET'])
def download_blob():
    name = request.args.get('name')
    if not name:
        return jsonify({'error': 'missing name'}), 400

    client = _get_sync_blob_service_client()
    if not client:
        return jsonify({'error': 'no_storage_credentials'}), 500

    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'research-summaries')
    container_client = client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(name)

    try:
        stream = blob_client.download_blob()
        data = stream.readall()
        return Response(data, mimetype='text/markdown; charset=utf-8', headers={"Content-Disposition": f"attachment; filename={Path(name).name}"})
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


def start_cleanup_thread():
    """Start a background daemon thread that removes runs (and their logs) older than RUN_CLEANUP_HOURS.

    Environment variables:
    - RUN_CLEANUP_HOURS (default 24)
    - RUN_CLEANUP_INTERVAL_SECONDS (default 3600)
    """
    def _cleanup_worker(max_age_seconds: int, interval_seconds: int):
        while True:
            now = datetime.now(timezone.utc)
            to_remove = []
            with run_lock:
                for rid, meta in list(runs.items()):
                    status = meta.get("status")
                    # skip active runs
                    if status in ("running", "queued"):
                        continue

                    ts_str = meta.get("end") or meta.get("start")
                    if not ts_str:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_str)
                    except Exception:
                        continue

                    age = (now - ts).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(rid)

                for rid in to_remove:
                    meta = runs.pop(rid, None)
                    if not meta:
                        continue
                    # delete log file if present
                    try:
                        logp = Path(meta.get("log" or ""))
                        if logp and logp.exists():
                            logp.unlink()
                    except Exception as e:
                        print(f"cleanup: failed to delete log for {rid}: {e}")

            time.sleep(interval_seconds)

    hours = int(os.getenv("RUN_CLEANUP_HOURS", "24"))
    interval = int(os.getenv("RUN_CLEANUP_INTERVAL_SECONDS", "3600"))
    t = threading.Thread(target=_cleanup_worker, args=(hours * 3600, interval), daemon=True)
    t.start()
    return t


# Start cleanup thread on import so old runs/logs are pruned automatically
start_cleanup_thread()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
