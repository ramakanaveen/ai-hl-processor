#!/usr/bin/env python3
"""
One-command startup for Bloomberg-style News Ticker System
Starts API + Ticker UI + News Feed Service
"""

import subprocess
import time
import sys
import signal
import os
import requests

def check_port(port):
    """Check if a port is in use"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def wait_for_api(timeout=30):
    """Wait for API to be ready"""
    print("⏳ Waiting for API to start...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://localhost:8000/health", timeout=1)
            if response.status_code == 200:
                print("✅ API is ready!")
                return True
        except:
            pass
        time.sleep(1)

    return False

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   📺 Bloomberg-Style News Ticker - Complete System        ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

Starting all services...
""")

    processes = []

    try:
        # Check if ports are in use
        if check_port(8000):
            print("⚠️  Port 8000 is already in use. Attempting to clear...")
            os.system("lsof -ti :8000 | xargs kill -9 2>/dev/null")
            time.sleep(2)

        if check_port(8501):
            print("⚠️  Port 8501 is already in use. Attempting to clear...")
            os.system("lsof -ti :8501 | xargs kill -9 2>/dev/null")
            time.sleep(2)

        # Start API Service
        print("\n1️⃣  Starting API Service (http://localhost:8000)...")
        api_process = subprocess.Popen(
            ["python3", "api_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(("API", api_process))

        # Wait for API to be ready
        if not wait_for_api():
            print("❌ API failed to start")
            return

        # Start Streamlit Ticker UI
        print("\n2️⃣  Starting Ticker UI (http://localhost:8501)...")
        streamlit_process = subprocess.Popen(
            ["streamlit", "run", "streamlit_ticker_app.py", "--server.port=8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(("Streamlit", streamlit_process))

        time.sleep(3)

        # Start News Ticker Service
        print("\n3️⃣  Starting News Feed Service...")
        ticker_service_process = subprocess.Popen(
            ["python3", "news_ticker_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(("News Ticker", ticker_service_process))

        print("""
╔════════════════════════════════════════════════════════════╗
║                    ✅ ALL SERVICES RUNNING                 ║
╚════════════════════════════════════════════════════════════╝

📺 Bloomberg-Style Ticker UI:  http://localhost:8501
🔧 API Service:                http://localhost:8000
📚 API Docs:                   http://localhost:8000/docs

📡 Live news feed is monitoring:
   • Reuters Business News (RSS)
   • Yahoo Finance (RSS)
   • Bloomberg (RSS)
   • NewsAPI (if API key is set)

💡 Tips:
   • The ticker UI auto-updates every 2 seconds
   • New headlines appear at the top with analysis
   • API broadcasts to all connected browsers
   • Press Ctrl+C to stop all services

🔴 LIVE - Ticker is running!
""")

        # Define signal handler
        def signal_handler(sig, frame):
            print("\n\n⏹️  Stopping all services...")

            for name, process in processes:
                print(f"   Stopping {name}...")
                process.terminate()

            # Wait for graceful shutdown
            time.sleep(2)

            # Force kill if still running
            for name, process in processes:
                if process.poll() is None:
                    process.kill()

            print("✅ All services stopped\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # Keep main thread alive and show ticker output
        print("📰 News Feed Output:\n")
        print("="*80)

        # Stream output from ticker service
        while True:
            line = ticker_service_process.stdout.readline()
            if line:
                print(line.decode().strip())
            elif ticker_service_process.poll() is not None:
                break
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down...")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    finally:
        # Cleanup
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

        print("✅ Cleanup complete")


if __name__ == "__main__":
    main()
