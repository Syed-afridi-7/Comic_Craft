"""ComicCraft Application Launcher.

Provides automatic environment checks, port cleanup, browser launch,
and Uvicorn ASGI server initialization.
"""

import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a network port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def kill_process_on_port(port: int) -> None:
    """Attempt to terminate any process currently listening on the specified port."""
    if sys.platform == "win32":
        try:
            import subprocess
            out = subprocess.check_output(
                f'netstat -ano | findstr /R /C:":{port} .*LISTENING"',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) > 0 and int(pid) != os.getpid():
                        print(f"[*] Freeing port {port} (terminating PID {pid})...")
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", pid],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
            time.sleep(1.0)
        except Exception:
            pass


def ensure_environment() -> None:
    """Verify and initialize required directories and .env configuration."""
    base_dir = Path(__file__).resolve().parent
    env_file = base_dir / ".env"
    example_file = base_dir / ".env.example"

    if not env_file.exists() and example_file.exists():
        print("[*] Creating .env from .env.example...")
        shutil.copy(example_file, env_file)

    panels_dir = base_dir / "static" / "panels"
    exports_dir = base_dir / "static" / "exports"
    panels_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)


def open_browser_when_ready(url: str, port: int) -> None:
    """Wait until the server responds on the port, then open the default web browser."""
    for _ in range(30):
        time.sleep(0.5)
        if is_port_in_use(port):
            time.sleep(0.5)
            print(f"[*] Opening browser to {url}...")
            webbrowser.open(url)
            break


def main() -> None:
    """Launch ComicCraft server."""
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    url = f"http://localhost:{port}"

    print("=" * 60)
    print("        ComicCraft: AI Comic Story Creator")
    print("=" * 60)

    ensure_environment()

    if is_port_in_use(port):
        print(f"[!] Port {port} is currently in use. Attempting to free port...")
        kill_process_on_port(port)

    # Start browser opener in background thread
    threading.Thread(
        target=open_browser_when_ready,
        args=(url, port),
        daemon=True,
    ).start()

    print(f"[*] Starting ComicCraft server on http://{host}:{port}")
    print(f"[*] Web Interface: {url}")
    print(f"[*] API Docs:      {url}/docs")
    print("[*] Press CTRL+C to stop the server.\n")

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
