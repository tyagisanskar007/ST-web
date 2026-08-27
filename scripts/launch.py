import os
import sys
import time
import subprocess
import webbrowser
import urllib.request

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, APP_DIR)

PYTHON_EXE = r"C:\Users\HP\python311\python.exe"
PYTHONW_EXE = r"C:\Users\HP\python311\pythonw.exe"

if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable
if not os.path.exists(PYTHONW_EXE):
    PYTHONW_EXE = PYTHON_EXE

def is_server_running():
    try:
        req = urllib.request.urlopen("http://127.0.0.1:5000", timeout=1.5)
        return req.getcode() == 200
    except Exception:
        return False

def start_server_if_needed():
    if is_server_running():
        return True
    
    app_py = os.path.join(APP_DIR, "app.py")
    # Start Flask server in background with no terminal window
    subprocess.Popen(
        [PYTHONW_EXE, app_py],
        cwd=APP_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    
    # Wait for server to become ready
    for _ in range(25):
        time.sleep(0.4)
        if is_server_running():
            return True
    return False

def main():
    target = "http://127.0.0.1:5000"
    if len(sys.argv) > 1 and sys.argv[1] == "--admin":
        target = "http://127.0.0.1:5000/admin/login"
    
    start_server_if_needed()
    webbrowser.open(target)

if __name__ == '__main__':
    main()
