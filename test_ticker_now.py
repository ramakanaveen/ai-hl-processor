#!/usr/bin/env python3
"""
Quick Test - Send test headlines to ticker and see them appear immediately
Run this AFTER starting the services to see instant results
"""

import requests
import time
import json

print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🧪 Ticker Test - Send Test Headlines                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")

# Check if API is running
print("1️⃣  Checking API service...")
try:
    response = requests.get("http://localhost:8000/health", timeout=2)
    if response.status_code == 200:
        print("   ✅ API is running!\n")
    else:
        print("   ❌ API is not responding properly")
        print("   Please start API first: python3 api_service.py\n")
        exit(1)
except Exception as e:
    print("   ❌ Cannot connect to API")
    print("   Please start API first: python3 api_service.py\n")
    exit(1)

# Check if ticker UI is accessible
print("2️⃣  Checking Streamlit UI...")
try:
    response = requests.get("http://localhost:8501", timeout=2)
    print("   ✅ UI is accessible at http://localhost:8501\n")
except:
    print("   ⚠️  UI might not be running")
    print("   Start it with: streamlit run streamlit_ticker_app.py\n")

# Send test headlines
test_headlines = [
    "Federal Reserve raises interest rates by 0.75 percentage points",
    "ECB President announces emergency bond buying program",
    "Bank of England intervenes in UK gilt market",
    "Japan central bank conducts currency intervention as yen weakens",
    "US jobs report shows unexpected surge in unemployment rate"
]

print("3️⃣  Sending test headlines to ticker...\n")
print("="*80)

for i, headline in enumerate(test_headlines, 1):
    print(f"\n📰 Sending headline #{i}:")
    print(f"   {headline[:70]}...")

    try:
        response = requests.post(
            "http://localhost:8000/broadcast",
            json={
                "headline": headline,
                "llm_provider": "mock",
                "min_confidence": 0.3
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            clients_notified = result.get("clients_notified", 0)
            analysis = result.get("result", {})
            entities = analysis.get("impacted_entities", [])

            print(f"   ✅ Broadcast successful!")
            print(f"   📡 {clients_notified} clients notified")
            print(f"   💱 {len(entities)} currencies impacted")

            if entities:
                for j, entity in enumerate(entities[:2], 1):
                    conf = entity.get("confidence", "low").upper()
                    curr = entity.get("currency", "???")
                    score = entity.get("confidence_score", 0)
                    print(f"      #{j} {curr}: {conf} ({score:.2f})")

            print(f"   👀 Check your browser - headline should appear NOW!")

        else:
            print(f"   ❌ Broadcast failed: HTTP {response.status_code}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Wait between headlines
    if i < len(test_headlines):
        print(f"\n   ⏳ Waiting 3 seconds before next headline...")
        time.sleep(3)

print("\n" + "="*80)
print("""
✅ Test complete!

👀 Check your browser at http://localhost:8501

You should see all 5 headlines with their currency impacts!

💡 Tips:
   • Headlines appear newest first (at the top)
   • Each headline shows impacted currencies
   • Click "Analysis Details" to see reasoning
   • Try adjusting settings in the sidebar

🔄 Run this script anytime to send more test headlines!
""")