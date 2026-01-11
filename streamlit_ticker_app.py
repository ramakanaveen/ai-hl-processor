"""
Bloomberg-Style News Ticker UI
Auto-updating display of real-time news analysis
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import websocket
import threading
from queue import Queue

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_TICKER_URL = "ws://localhost:8000/ws/ticker"

# Page configuration
st.set_page_config(
    page_title="📺 Bloomberg-Style News Ticker",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Bloomberg-style ticker
st.markdown("""
<style>
    .ticker-header {
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .news-card {
        border-left: 5px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        background: #f8f9fa;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .news-headline {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .impact-high {
        color: #2ecc71;
        font-weight: bold;
    }
    .impact-medium {
        color: #f39c12;
        font-weight: bold;
    }
    .impact-low {
        color: #e74c3c;
        font-weight: bold;
    }
    .timestamp {
        color: #7f8c8d;
        font-size: 0.9rem;
    }
    .live-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #2ecc71;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
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


def format_timestamp(ts_str):
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime("%H:%M:%S")
    except:
        return ts_str


# Initialize session state
if 'ticker_messages' not in st.session_state:
    st.session_state.ticker_messages = []

if 'ws_connected' not in st.session_state:
    st.session_state.ws_connected = False

if 'message_queue' not in st.session_state:
    st.session_state.message_queue = Queue()


# Sidebar
with st.sidebar:
    st.header("⚙️ Ticker Controls")

    # API health check
    is_healthy, health_info = check_api_health()

    if is_healthy:
        st.success("✅ API Connected")
        if health_info:
            st.info(f"**Environment:** {health_info.get('environment', 'N/A')}")
    else:
        st.error("❌ API Not Available")
        st.warning("Please start:\n```bash\npython3 api_service.py\n```")

    st.markdown("---")

    # Display settings
    st.subheader("📺 Display Settings")
    max_messages = st.slider(
        "Max messages to display",
        min_value=5,
        max_value=50,
        value=20,
        help="Maximum number of news items to show in ticker"
    )

    show_low_confidence = st.checkbox(
        "Show low confidence impacts",
        value=False,
        help="Display currency impacts with low confidence"
    )

    st.markdown("---")

    # Connection status
    st.subheader("🔌 Connection Status")

    if st.session_state.ws_connected:
        st.markdown('<div class="live-indicator"></div> <b>LIVE</b>', unsafe_allow_html=True)
        st.caption(f"Messages received: {len(st.session_state.ticker_messages)}")
    else:
        st.warning("⏸️ Not Connected")

    if st.button("🔄 Reconnect", use_container_width=True):
        st.session_state.ws_connected = False
        st.rerun()

    if st.button("🗑️ Clear Ticker", use_container_width=True):
        st.session_state.ticker_messages = []
        st.rerun()


# Main content
st.markdown('<div class="ticker-header">📺 LIVE NEWS TICKER</div>', unsafe_allow_html=True)

# Connection indicator
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.session_state.ws_connected:
        st.success("🔴 LIVE - Receiving real-time updates")
    else:
        st.info("⏳ Connecting to ticker feed...")

# Auto-refresh placeholder
ticker_placeholder = st.empty()

# WebSocket connection in background
def ws_listener():
    """Background thread to listen for WebSocket messages"""
    try:
        ws = websocket.WebSocketApp(
            WS_TICKER_URL,
            on_message=lambda ws, msg: st.session_state.message_queue.put(msg),
            on_open=lambda ws: st.session_state.update({'ws_connected': True}),
            on_close=lambda ws: st.session_state.update({'ws_connected': False}),
            on_error=lambda ws, err: st.session_state.update({'ws_connected': False})
        )

        # Run forever (will be stopped when app closes)
        ws.run_forever()

    except Exception as e:
        st.session_state.ws_connected = False


# Start WebSocket listener if not connected
if not st.session_state.ws_connected and is_healthy:
    thread = threading.Thread(target=ws_listener, daemon=True)
    thread.start()
    time.sleep(1)  # Give it a moment to connect

# Process incoming messages from queue
while not st.session_state.message_queue.empty():
    msg = st.session_state.message_queue.get()
    try:
        data = json.loads(msg)
        if data.get('type') == 'news_update':
            st.session_state.ticker_messages.insert(0, data)

            # Limit message history
            if len(st.session_state.ticker_messages) > max_messages:
                st.session_state.ticker_messages = st.session_state.ticker_messages[:max_messages]

    except json.JSONDecodeError:
        pass


# Display ticker messages
with ticker_placeholder.container():
    if not st.session_state.ticker_messages:
        st.info("⏳ Waiting for news updates...\n\n"
                "💡 **Tip:** Start the ticker service to see live updates:\n"
                "```bash\npython3 news_ticker_service.py\n```")
    else:
        for i, msg in enumerate(st.session_state.ticker_messages):
            data = msg.get('data', {})
            headline = data.get('headline', 'Unknown')
            timestamp = msg.get('timestamp', '')
            entities = data.get('impacted_entities', [])
            processing_time = data.get('processing_time_ms', 0)

            # Filter by confidence if needed
            if not show_low_confidence:
                entities = [e for e in entities if e.get('confidence') != 'low']

            # Skip if no entities after filtering
            if not entities:
                continue

            # Create news card
            with st.container():
                st.markdown(f"""
                <div class="news-card">
                    <div class="news-headline">📰 {headline}</div>
                    <div class="timestamp">⏰ {format_timestamp(timestamp)} | ⚡ {processing_time:.0f}ms</div>
                </div>
                """, unsafe_allow_html=True)

                # Display impacted currencies
                cols = st.columns(min(len(entities), 4))

                for j, entity in enumerate(entities[:4]):
                    with cols[j]:
                        confidence = entity.get('confidence', 'low')
                        currency = entity.get('currency', 'Unknown')
                        score = entity.get('confidence_score', 0)

                        # Confidence badge
                        if confidence == 'high':
                            badge = "🟢 HIGH"
                            css_class = "impact-high"
                        elif confidence == 'medium':
                            badge = "🟡 MEDIUM"
                            css_class = "impact-medium"
                        else:
                            badge = "🔴 LOW"
                            css_class = "impact-low"

                        st.markdown(f"""
                        <div style='text-align: center; padding: 0.5rem; background: white; border-radius: 5px;'>
                            <div style='font-size: 1.5rem; font-weight: bold;'>{currency}</div>
                            <div class='{css_class}'>{badge}</div>
                            <div style='font-size: 0.9rem; color: #7f8c8d;'>{score:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                # Show reasoning for top impact
                if entities:
                    with st.expander("💡 Analysis Details", expanded=False):
                        for entity in entities[:3]:
                            st.markdown(f"**{entity['currency']}** ({entity['confidence'].upper()})")
                            st.caption(entity.get('reasoning', 'No reasoning provided'))

                st.markdown("---")


# Auto-refresh every 2 seconds
time.sleep(2)
st.rerun()
