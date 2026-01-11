"""
Fixed Streamlit UI - Request/Response Mode
All issues resolved - custom headlines now work!
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="AI Headline Impact Analyzer",
    page_icon="📰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .confidence-high { color: #2ecc71; font-weight: bold; }
    .confidence-medium { color: #f39c12; font-weight: bold; }
    .confidence-low { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200, response.json()
    except:
        return False, None


def analyze_headline(headline, min_confidence, llm_provider):
    """Analyze a news headline"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={
                "headline": headline,
                "min_confidence": min_confidence,
                "llm_provider": llm_provider
            },
            timeout=15
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"API Error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"


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
        st.warning("Please start the API service:\n```bash\npython3 api_service.py\n```")
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

# Main content
st.markdown('<div class="main-header">📰 AI Headline Impact Analyzer</div>', unsafe_allow_html=True)

st.header("🔍 Analyze News Headline")

# Initialize session state for headline
if 'current_headline' not in st.session_state:
    st.session_state.current_headline = ""

# Example buttons FIRST - these set the session state
st.markdown("#### 💡 Quick Examples (Click to analyze)")
example_col1, example_col2 = st.columns(2)

with example_col1:
    if st.button("📈 Fed raises interest rates", key="ex1", use_container_width=True):
        st.session_state.current_headline = "Federal Reserve raises interest rates by 0.75 basis points"
        st.rerun()

if st.button("🇬🇧 UK tax increase", key="ex2", use_container_width=True):
        st.session_state.current_headline = "Rachel Reeves increased the tax"
        st.rerun()

example_col3, example_col4 = st.columns(2)

with example_col3:
    if st.button("⚠️ Russia-Ukraine conflict", key="ex3", use_container_width=True):
        st.session_state.current_headline = "Russia launches missile attack on Ukrainian energy infrastructure"
        st.rerun()

with example_col4:
    if st.button("🛢️ OPEC production cuts", key="ex4", use_container_width=True):
        st.session_state.current_headline = "OPEC+ announces surprise oil production cut of 2 million barrels per day"
        st.rerun()

st.markdown("---")

# Input form
headline = st.text_area(
    "Or enter your own news headline:",
    value=st.session_state.current_headline,
    height=100,
    placeholder="e.g., European Central Bank cuts interest rates to zero",
    help="Enter any financial or economic news headline"
)

analyze_button = st.button("🚀 Analyze Impact", type="primary", use_container_width=True)

# Analysis
if analyze_button and headline.strip():
    st.session_state.current_headline = headline  # Save for next time

    with st.spinner(f"🔄 Analyzing with {llm_provider}..."):
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
            st.metric("Entities Analyzed", result['metadata']['total_entities_analyzed'])
        with col3:
            st.metric("Above Threshold", result['metadata']['entities_above_threshold'])

        entities = result.get('impacted_entities', [])

        if entities:
            st.markdown("### 💱 Impacted Currencies")

            # Create tabs for different views
            view_tab1, view_tab2, view_tab3 = st.tabs(["📊 Visual", "📋 List", "📄 Table"])

            with view_tab1:
                # Visual bar chart
                df = pd.DataFrame(entities)
                fig = go.Figure(go.Bar(
                    x=df['confidence_score'],
                    y=df['currency'],
                    orientation='h',
                    marker=dict(
                        color=df['confidence_score'],
                        colorscale='RdYlGn',
                        showscale=True
                    ),
                    text=df['confidence'].str.upper(),
                    textposition='auto'
                ))

                fig.update_layout(
                    title="Currency Impact Confidence Levels",
                    xaxis_title="Confidence Score",
                    yaxis_title="Currency",
                    height=max(300, len(entities) * 50)
                )

                st.plotly_chart(fig, use_container_width=True)

            with view_tab2:
                # List view with reasoning
                for i, entity in enumerate(entities, 1):
                    conf = entity['confidence']
                    css_class = f"confidence-{conf}"

                    st.markdown(f"""
                    **#{i} {entity['currency']}**
                    - Confidence: <span class="{css_class}">{conf.upper()}</span> ({entity['confidence_score']:.2f})
                    - Reasoning: {entity['reasoning']}
                    """, unsafe_allow_html=True)
                    st.markdown("---")

            with view_tab3:
                # Table view
                df = pd.DataFrame(entities)
                st.dataframe(df, use_container_width=True)

            # Export section
            st.markdown("---")
            st.markdown("### 💾 Export Results")

            export_col1, export_col2 = st.columns(2)

            with export_col1:
                import json
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
            st.info("""
            **Possible reasons:**
            - The headline is not related to forex/currencies
            - The confidence threshold is too high
            - Try a financial/economic headline like:
              - "Federal Reserve raises interest rates"
              - "European Central Bank cuts rates"
              - "Bank of Japan intervenes in currency market"
            """)

    else:
        st.error(f"❌ Analysis failed: {result}")
        st.info("""
        **Troubleshooting:**
        - Check that API service is running
        - Try restarting: `python3 api_service.py`
        - Check the error message above
        """)

# Footer
st.markdown("---")
with st.expander("📖 How to Use"):
    st.markdown("""
    ### Using This Tool:

    1. **Quick Start**: Click any example button above
    2. **Custom Headlines**: Type your headline in the text box
    3. **Analyze**: Click "Analyze Impact"
    4. **View Results**: See impacted currencies in 3 different views
    5. **Export**: Download results as JSON or CSV

    ### What Headlines Work Best:
    - ✅ Federal Reserve/ECB/Bank of England policy changes
    - ✅ Interest rate announcements
    - ✅ Economic data releases
    - ✅ Currency intervention announcements
    - ✅ Trade policy changes

    ### What Won't Work:
    - ❌ Non-financial news (sports, entertainment)
    - ❌ Company-specific news (unless major economic impact)
    - ❌ Headlines not related to currencies/forex

    ### Tips:
    - Lower the confidence threshold to see more results
    - Use Mock LLM for fast testing
    - Switch to Gemini Flash or Claude for production
    """)