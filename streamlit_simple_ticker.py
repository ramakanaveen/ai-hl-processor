"""
Simple News Ticker UI - Polling Version
Works reliably with Streamlit's auto-refresh
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="📺 News Ticker",
    page_icon="📺",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .ticker-header {
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .news-card {
        border-left: 5px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        background: #f8f9fa;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200, response.json()
    except:
        return False, None


def analyze_headline(headline, llm_provider="mock", min_confidence=0.3):
    """Analyze a single headline"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={
                "headline": headline,
                "llm_provider": llm_provider,
                "min_confidence": min_confidence
            },
            timeout=15
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Error: {response.status_code}"
    except Exception as e:
        return False, str(e)


# Initialize session state
if 'ticker_history' not in st.session_state:
    st.session_state.ticker_history = []

if 'last_headline' not in st.session_state:
    st.session_state.last_headline = ""

# Sidebar
with st.sidebar:
    st.header("⚙️ Controls")

    # API health check
    is_healthy, health_info = check_api_health()

    if is_healthy:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Not Available")
        st.warning("Start API:\n```bash\npython3 api_service.py\n```")
        st.stop()

    st.markdown("---")

    # Settings
    st.subheader("📺 Display")
    max_items = st.slider("Max headlines", 5, 30, 15)

    llm_provider = st.selectbox(
        "LLM Provider",
        ["mock", "gemini_flash", "claude"],
        format_func=lambda x: {
            "mock": "Mock (Fast)",
            "gemini_flash": "Gemini Flash",
            "claude": "Claude"
        }[x]
    )

    min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.3, 0.05)

    st.markdown("---")

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.ticker_history = []
        st.rerun()

    st.caption(f"📊 {len(st.session_state.ticker_history)} headlines in history")

# Main header
st.markdown('<div class="ticker-header">📺 NEWS TICKER</div>', unsafe_allow_html=True)

# Input section
col1, col2 = st.columns([4, 1])

with col1:
    headline_input = st.text_input(
        "Add headline to ticker:",
        placeholder="Enter a news headline...",
        key="headline_input"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_button = st.button("📤 Analyze", use_container_width=True)

# Quick examples
st.markdown("**💡 Quick Examples:**")
example_cols = st.columns(4)

examples = [
    "Federal Reserve raises rates",
    "ECB bond buying program",
    "UK tax increase",
    "OPEC production cut"
]

for i, (col, example) in enumerate(zip(example_cols, examples)):
    with col:
        if st.button(f"📰 {example[:20]}...", key=f"ex{i}", use_container_width=True):
            headline_input = example
            analyze_button = True

# Process headline
if analyze_button and headline_input:
    # Avoid duplicates
    if headline_input != st.session_state.last_headline:
        with st.spinner("🔄 Analyzing..."):
            success, result = analyze_headline(headline_input, llm_provider, min_confidence)

        if success:
            # Add to history
            result['added_at'] = datetime.now().isoformat()
            st.session_state.ticker_history.insert(0, result)
            st.session_state.last_headline = headline_input

            # Limit history
            if len(st.session_state.ticker_history) > max_items:
                st.session_state.ticker_history = st.session_state.ticker_history[:max_items]

            st.success(f"✅ Added to ticker!")
            st.rerun()
        else:
            st.error(f"❌ Analysis failed: {result}")

st.markdown("---")

# Display ticker
st.subheader(f"📊 Live Ticker ({len(st.session_state.ticker_history)} headlines)")

if not st.session_state.ticker_history:
    st.info("""
    ⏳ **Ticker is empty**

    **Quick Start:**
    1. Click one of the example buttons above, OR
    2. Type a headline and click "Analyze", OR
    3. Run the test script in another terminal:
       ```bash
       python3 test_ticker_now.py
       ```
    """)
else:
    for i, item in enumerate(st.session_state.ticker_history):
        headline = item.get('headline', 'Unknown')
        entities = item.get('impacted_entities', [])
        processing_time = item.get('processing_time_ms', 0)
        added_at = item.get('added_at', '')

        # Parse timestamp
        try:
            dt = datetime.fromisoformat(added_at)
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = "N/A"

        with st.container():
            st.markdown(f"""
            <div class="news-card">
                <div style="font-size: 1.1rem; font-weight: bold; color: #1f77b4;">
                    📰 {headline}
                </div>
                <div style="color: #7f8c8d; font-size: 0.9rem; margin-top: 0.3rem;">
                    ⏰ {time_str} | ⚡ {processing_time:.0f}ms
                </div>
            </div>
            """, unsafe_allow_html=True)

            if entities:
                # Show currency impacts
                cols = st.columns(min(len(entities), 4))

                for j, entity in enumerate(entities[:4]):
                    with cols[j]:
                        confidence = entity.get('confidence', 'low')
                        currency = entity.get('currency', 'Unknown')
                        score = entity.get('confidence_score', 0)

                        # Badge color
                        if confidence == 'high':
                            badge_color = "#2ecc71"
                            emoji = "🟢"
                        elif confidence == 'medium':
                            badge_color = "#f39c12"
                            emoji = "🟡"
                        else:
                            badge_color = "#e74c3c"
                            emoji = "🔴"

                        st.markdown(f"""
                        <div style='text-align: center; padding: 0.5rem; background: white; border-radius: 5px; border: 2px solid {badge_color};'>
                            <div style='font-size: 1.3rem; font-weight: bold;'>{currency}</div>
                            <div style='color: {badge_color}; font-weight: bold;'>{emoji} {confidence.upper()}</div>
                            <div style='font-size: 0.85rem; color: #7f8c8d;'>{score:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                # Show reasoning
                with st.expander("💡 Analysis Details"):
                    for entity in entities[:3]:
                        st.markdown(f"**{entity['currency']}** ({entity['confidence'].upper()})")
                        st.caption(entity.get('reasoning', 'No reasoning'))
            else:
                st.caption("No significant impacts detected")

            st.markdown("---")

# Auto-refresh info
st.sidebar.markdown("---")
st.sidebar.info(f"🔄 Page refreshes when you add headlines\n\n💡 Run test script to add headlines automatically!")

# Instructions at bottom
with st.expander("📖 How to Use"):
    st.markdown("""
    ### Manual Mode:
    1. Type a headline or click an example
    2. Click "Analyze"
    3. See it appear in the ticker below

    ### Automatic Mode (Recommended):
    **In another terminal, run:**
    ```bash
    python3 test_ticker_now.py
    ```

    This will send 5 test headlines. After running:
    1. Come back to this page
    2. **Refresh your browser (F5 or Cmd+R)**
    3. You'll see all 5 headlines!

    ### Why Not Auto-Refresh?
    Streamlit doesn't support true WebSocket streaming (yet).
    But you can manually refresh to see new headlines!

    **Pro Tip:** Use the original `streamlit_app.py` for request/response mode!
    """)