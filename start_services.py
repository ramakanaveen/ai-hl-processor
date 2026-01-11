#!/usr/bin/env python3
"""
Startup script for AI Headline Impact Processor
Runs both FastAPI backend and Streamlit UI
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_banner():
    """Print startup banner"""
    banner = f"""
{BLUE}{BOLD}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   AI Headline Impact Processor - Phase 1                 ║
║   FastAPI Backend + Streamlit UI                         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{RESET}
"""
    print(banner)


def check_dependencies():
    """Check if required packages are installed"""
    print(f"{YELLOW}Checking dependencies...{RESET}")

    required_packages = ['fastapi', 'uvicorn', 'streamlit', 'requests']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ✗ {package} {RED}(missing){RESET}")

    if missing_packages:
        print(f"\n{RED}Missing packages found. Please install them:{RESET}")
        print(f"  pip install {' '.join(missing_packages)}")
        print(f"\n{YELLOW}Or install all requirements:{RESET}")
        print(f"  pip install -r requirements.txt")
        return False

    print(f"{GREEN}All dependencies satisfied!{RESET}\n")
    return True


def start_fastapi():
    """Start FastAPI backend"""
    print(f"{BLUE}Starting FastAPI backend on http://localhost:8000{RESET}")

    # Set environment variables
    env = os.environ.copy()
    env['API_PORT'] = '8000'

    # Start FastAPI with uvicorn
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'api_service:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    return process


def start_streamlit():
    """Start Streamlit UI"""
    print(f"{BLUE}Starting Streamlit UI on http://localhost:8501{RESET}")

    # Start Streamlit
    process = subprocess.Popen(
        [sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py', '--server.port', '8501'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    return process


def wait_for_api():
    """Wait for API to be ready"""
    import requests

    print(f"{YELLOW}Waiting for API to be ready...{RESET}")

    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get('http://localhost:8000/health', timeout=1)
            if response.status_code == 200:
                print(f"{GREEN}✓ API is ready!{RESET}\n")
                return True
        except:
            pass

        time.sleep(1)
        if (i + 1) % 5 == 0:
            print(f"  Still waiting... ({i + 1}/{max_retries})")

    print(f"{RED}✗ API failed to start{RESET}")
    return False


def print_instructions():
    """Print usage instructions"""
    instructions = f"""
{GREEN}{BOLD}Services are running!{RESET}

{BOLD}Access the application:{RESET}
  • Streamlit UI:  {BLUE}http://localhost:8501{RESET}
  • FastAPI Docs:  {BLUE}http://localhost:8000/docs{RESET}
  • API Health:    {BLUE}http://localhost:8000/health{RESET}

{BOLD}Example API usage:{RESET}
  curl -X POST http://localhost:8000/analyze \\
    -H "Content-Type: application/json" \\
    -d '{{"headline": "Fed raises interest rates", "min_confidence": 0.3}}'

{YELLOW}{BOLD}Press Ctrl+C to stop all services{RESET}
"""
    print(instructions)


def main():
    """Main startup function"""
    print_banner()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    processes = []

    try:
        # Start FastAPI
        api_process = start_fastapi()
        processes.append(('FastAPI', api_process))
        time.sleep(2)

        # Wait for API to be ready
        if not wait_for_api():
            print(f"{RED}Stopping services due to API startup failure{RESET}")
            api_process.terminate()
            sys.exit(1)

        # Start Streamlit
        streamlit_process = start_streamlit()
        processes.append(('Streamlit', streamlit_process))
        time.sleep(3)

        # Print instructions
        print_instructions()

        # Keep running and monitor processes
        while True:
            time.sleep(1)

            # Check if any process has died
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"{RED}✗ {name} process has stopped unexpectedly{RESET}")
                    raise KeyboardInterrupt

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Shutting down services...{RESET}")

        # Terminate all processes
        for name, proc in processes:
            print(f"  Stopping {name}...")
            proc.terminate()

            # Wait for process to terminate
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"  Force killing {name}...")
                proc.kill()

        print(f"{GREEN}All services stopped.{RESET}")

    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

        # Clean up processes
        for name, proc in processes:
            proc.terminate()

        sys.exit(1)


if __name__ == "__main__":
    main()
