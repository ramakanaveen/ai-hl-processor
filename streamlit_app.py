"""
Streamlit UI for AI Headline Impact Processor - v2
Multi-page app with Request/Response and Live Stream modes
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
from typing import List, Dict, Any
import json
import websocket
import threading

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="AI Headline Impact Analyzer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .confidence-high {
        color: #2ecc71;
        font-weight: bold;
    }
    .confidence-medium {
        color: #f39c12;
        font-weight: bold;
    }
    .confidence-low {
        color: #e74c3c;
        font-weight: bold;
    }
    .stream-card {
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        animation: slideIn 0.3s ease-in;
    }
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
""", unsafe_allow_html=True)


# Utility functions
def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)


def analyze_headline(headline: str, min_confidence: float = 0.3, llm_provider: str = "mock"):
    """Call API to analyze headline"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={
                "headline": headline,
                "min_confidence": min_confidence,
                "llm_provider": llm_provider
            },
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json()
    except Exception as e:
        return False, str(e)


def get_confidence_color(confidence: str):
    """Get color for confidence level"""
    colors = {
        "high": "#2ecc71",
        "medium": "#f39c12",
        "low": "#e74c3c"
    }
    return colors.get(confidence, "#95a5a6")


def display_impact_card(entity: Dict[str, Any]):
    """Display entity impact as a card"""
    confidence = entity['confidence']
    color = get_confidence_color(confidence)

    st.markdown(f"""
    <div style="border-left: 4px solid {color}; padding: 1rem; margin: 1rem 0; background-color: #f8f9fa; border-radius: 0.5rem;">
        <h3 style="margin: 0; color: {color};">{entity['currency']}</h3>
        <p style="margin: 0.5rem 0;">
            <strong>Confidence:</strong> <span style="color: {color}; font-weight: bold;">{confidence.upper()}</span>
            ({entity['confidence_score']:.2f})
        </p>
        <p style="margin: 0.5rem 0; color: #666;">
            <strong>Reasoning:</strong> {entity['reasoning']}
        </p>
    </div>
    """, unsafe_allow_html=True)


def create_confidence_chart(entities: List[Dict[str, Any]]):
    """Create confidence chart"""
    if not entities:
        return None

    df = pd.DataFrame(entities)
    df = df.sort_values('confidence_score', ascending=True)

    fig = go.Figure(go.Bar(
        x=df['confidence_score'],
        y=df['currency'],
        orientation='h',
        marker=dict(
            color=df['confidence_score'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Confidence")
        ),
        text=df['confidence'].str.upper(),
        textposition='auto',
    ))

    fig.update_layout(
        title="Currency Impact Confidence Levels",
        xaxis_title="Confidence Score",
        yaxis_title="Currency",
        height=max(300, len(entities) * 50),
        showlegend=False
    )

    return fig


# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    # API health check
    is_healthy, health_info = check_api_health()

    if is_healthy:
        st.success("✅ API Connected")
        if health_info:
            st.info(f"**Environment:** {health_info.get('environment', 'N/A')}")
    else:
        st.error("❌ API Not Available")
        st.warning("Please start the API service:\n```bash\npython api_service.py\n```")
        st.stop()

    st.markdown("---")

    # LLM Provider Selection
    st.subheader("🤖 LLM Provider")
    llm_provider = st.selectbox(
        "Select LLM Provider",
        options=["mock", "gemini_flash", "claude"],
        format_func=lambda x: {
            "mock": "Mock LLM (Fast, no API required)",
            "gemini_flash": "Google Gemini Flash",
            "claude": "Anthropic Claude"
        }[x],
        help="Choose which LLM to use for analysis"
    )

    # Show provider-specific info
    if llm_provider == "gemini_flash":
        st.info("📌 Requires: GOOGLE_CLOUD_PROJECT and GOOGLE_CREDENTIALS_PATH")
    elif llm_provider == "claude":
        st.info("📌 Requires: ANTHROPIC_API_KEY environment variable")

    st.markdown("---")

    # Analysis Settings
    st.subheader("Analysis Settings")
    min_confidence = st.slider(
        "Minimum Confidence Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.05,
        help="Only show entities with confidence above this threshold"
    )

    st.markdown("---")
    st.markdown("### 📊 Statistics")
    if st.button("Get API Stats"):
        try:
            response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                st.json(stats)
        except Exception as e:
            st.error(f"Error fetching stats: {e}")


# Main navigation
st.markdown('<div class="main-header">📰 AI Headline Impact Analyzer</div>', unsafe_allow_html=True)

# Page selection tabs
tab1, tab2 = st.tabs(["📊 Request / Response", "📡 Live Stream"])

# ========== TAB 1: REQUEST/RESPONSE MODE ==========
with tab1:
    st.header("🔍 Analyze News Headline")

    # Input form
    with st.form(key="analysis_form"):
        headline = st.text_area(
            "Enter news headline",
            height=100,
            placeholder="e.g., Rachel Reeves increased the tax",
            help="Enter a financial news headline to analyze its impact on currencies"
        )

        submit_button = st.form_submit_button("🚀 Analyze Impact", use_container_width=True)

    # Example headlines
    st.markdown("#### 💡 Example Headlines")
    example_col1, example_col2 = st.columns(2)

    with example_col1:
        if st.button("📈 Fed raises interest rates", key="ex1", use_container_width=True):
            headline = "Federal Reserve raises interest rates by 0.75 basis points"
            submit_button = True

    with example_col2:
        if st.button("🇬🇧 UK tax increase", key="ex2", use_container_width=True):
            headline = "Rachel Reeves increased the tax"
            submit_button = True

    example_col3, example_col4 = st.columns(2)

    with example_col3:
        if st.button("⚠️ Russia-Ukraine conflict", key="ex3", use_container_width=True):
            headline = "Russia launches missile attack on Ukrainian energy infrastructure"
            submit_button = True

    with example_col4:
        if st.button("🛢️ OPEC production cuts", key="ex4", use_container_width=True):
            headline = "OPEC+ announces surprise oil production cut of 2 million barrels per day"
            submit_button = True

    # Analysis results
    if submit_button and headline.strip():
        with st.spinner("🔄 Analyzing headline..."):
            success, result = analyze_headline(headline, min_confidence, llm_provider)

        if success:
            st.success("✅ Analysis Complete!")

            # Display results
            st.markdown("---")
            st.header("📊 Impact Analysis Results")

            # Metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Processing Time", f"{result['processing_time_ms']:.0f} ms")
            with col2:
                entities_count = len(result['impacted_entities'])
                st.metric("Impacted Entities", entities_count)
            with col3:
                if result.get('metadata'):
                    overall_conf = result['metadata'].get('overall_confidence', 0)
                    st.metric("Overall Confidence", f"{overall_conf:.2f}")

            # Display headline
            st.markdown(f"### 📰 Headline")
            st.info(result['headline'])

            # Impacted entities
            entities = result['impacted_entities']

            if entities:
                st.markdown(f"### 💱 Impacted Currencies ({len(entities)})")

                # Tabs for different views
                view_tab1, view_tab2, view_tab3 = st.tabs(["📋 Cards View", "📊 Chart View", "📄 Table View"])

                with view_tab1:
                    for entity in entities:
                        display_impact_card(entity)

                with view_tab2:
                    fig = create_confidence_chart(entities)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                with view_tab3:
                    df = pd.DataFrame(entities)
                    df = df.sort_values('confidence_score', ascending=False)
                    st.dataframe(df, use_container_width=True)

                # Export option
                st.markdown("---")
                st.markdown("### 💾 Export Results")

                export_col1, export_col2 = st.columns(2)

                with export_col1:
                    json_str = json.dumps(result, indent=2, default=str)
                    st.download_button(
                        label="📥 Download as JSON",
                        data=json_str,
                        file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

                with export_col2:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("⚠️ No entities found above the confidence threshold.")
        else:
            st.error(f"❌ Analysis failed: {result}")


# ========== TAB 2: LIVE STREAM MODE ==========
with tab2:
    st.header("📡 Live News Stream")
    st.markdown("Real-time analysis of incoming news headlines via WebSocket")

    # Stream controls
    col1, col2 = st.columns([3, 1])

    with col1:
        stream_headline = st.text_input(
            "Enter headline to stream",
            placeholder="Type a headline and press Enter...",
            key="stream_input"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        send_button = st.button("📤 Send to Stream", use_container_width=True)

    # Initialize session state for stream results
    if 'stream_results' not in st.session_state:
        st.session_state.stream_results = []

    # Send headline via WebSocket
    if send_button and stream_headline:
        st.info("🔄 Processing via WebSocket...")

        try:
            import websocket as ws

            # Create WebSocket connection
            websocket_url = "ws://localhost:8000/ws/stream"

            def on_message(ws, message):
                data = json.loads(message)
                if data.get('status') == 'completed':
                    st.session_state.stream_results.insert(0, data['data'])

            def on_error(ws, error):
                st.error(f"WebSocket error: {error}")

            # Connect and send
            websocket_client = ws.WebSocketApp(
                websocket_url,
                on_message=on_message,
                on_error=on_error
            )

            # Send headline
            def send_headline():
                ws = ws.create_connection(websocket_url)
                ws.send(json.dumps({
                    "headline": stream_headline,
                    "min_confidence": min_confidence,
                    "llm_provider": llm_provider
                }))

                # Receive response
                response = ws.recv()
                data = json.loads(response)

                if data.get('status') == 'completed':
                    st.session_state.stream_results.insert(0, data['data'])

                ws.close()

            threading.Thread(target=send_headline, daemon=True).start()
            time.sleep(1)  # Wait for response
            st.rerun()

        except Exception as e:
            st.error(f"❌ WebSocket error: {e}")
            st.info("💡 Tip: Make sure the API service is running with WebSocket support")

    # Display stream results
    st.markdown("---")
    st.markdown("### 📊 Stream Results")

    if st.session_state.stream_results:
        for i, result in enumerate(st.session_state.stream_results):
            with st.expander(f"📰 {result['headline'][:80]}...", expanded=(i == 0)):
                st.markdown(f"**Time:** {result.get('analysis_timestamp', 'N/A')}")
                st.markdown(f"**Processing:** {result.get('processing_time_ms', 0):.0f}ms")

                entities = result.get('impacted_entities', [])
                if entities:
                    for entity in entities:
                        display_impact_card(entity)
                else:
                    st.warning("No entities found")

        # Clear button
        if st.button("🗑️ Clear Stream History"):
            st.session_state.stream_results = []
            st.rerun()
    else:
        st.info("👆 Enter headlines above to see real-time analysis results")


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>AI Headline Impact Processor v2.0.0-phase1</p>
    <p>Powered by Multiple LLM Providers & WebSocket Streaming</p>
</div>
""", unsafe_allow_html=True)
