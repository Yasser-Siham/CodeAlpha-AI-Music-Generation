from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import subprocess
import sys
import threading
import os

ROOT = Path(__file__).resolve().parent
STATE = {"running": False, "log": "Ready. Prepare demo data or train with your own MIDI files.", "result": None}
LOCK = threading.Lock()

def run(command, action):
    try:
        process = subprocess.Popen([sys.executable, "-u", *command], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            with LOCK:
                STATE["log"] = (STATE["log"] + line)[-18000:]
        code = process.wait()
        with LOCK:
            STATE["log"] += "\nCompleted successfully." if code == 0 else "\nFailed. Check the details above."
            if action == "generate" and code == 0:
                STATE["result"] = "/output/generated_music.mid"
    except Exception as exc:
        with LOCK:
            STATE["log"] += str(exc)
    finally:
        with LOCK:
            STATE["running"] = False

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            with LOCK:
                payload = dict(STATE)
            payload["model"] = (ROOT / "models/music_lstm.keras").exists()
            payload["files"] = len(list((ROOT / "data/midi").rglob("*.mid"))) + len(list((ROOT / "data/midi").rglob("*.midi")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())
        else:
            if self.path == "/":
                self.path = "/web/index.html"
            super().do_GET()

    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 4096)))
            action = data["action"]
            if action == "demo":
                command = ["prepare_demo_data.py"]
            elif action == "train":
                epochs = int(data["epochs"])
                if not 1 <= epochs <= 1000: raise ValueError("Epochs must be 1–1000.")
                command = ["train.py", "--epochs", str(epochs)]
            elif action == "generate":
                length, temperature = int(data["length"]), float(data["temperature"])
                if not 1 <= length <= 5000 or not 0.1 <= temperature <= 2: raise ValueError("Invalid generation settings.")
                command = ["generate.py", "--length", str(length), "--temperature", str(temperature)]
            else:
                raise ValueError("Unknown action.")
            with LOCK:
                if STATE["running"]: raise ValueError("A task is already running.")
                STATE.update(running=True, log="Starting " + action + "…\n")
                if action == "generate": STATE["result"] = None
            threading.Thread(target=run, args=(command, action), daemon=True).start()
            self.send_response(202)
            self.end_headers()
        except (ValueError, KeyError) as exc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(exc).encode())

if __name__ == "__main__":
    os.chdir(ROOT)
    print("Music Studio: http://127.0.0.1:8000", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
