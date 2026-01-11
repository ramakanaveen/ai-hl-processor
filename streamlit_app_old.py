"""
Streamlit UI for AI Headline Impact Processor
Real-time news analysis dashboard
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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)


def analyze_headline(headline: str, min_confidence: float = 0.3):
    """Call API to analyze headline"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={
                "headline": headline,
                "min_confidence": min_confidence
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


def main():
    # Header
    st.markdown('<div class="main-header">📰 AI Headline Impact Analyzer</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API health check
        is_healthy, health_info = check_api_health()

        if is_healthy:
            st.success("✅ API Connected")
            if health_info:
                st.info(f"**Environment:** {health_info.get('environment', 'N/A')}")
                st.info(f"**Model:** {health_info.get('model_provider', 'N/A')}")
        else:
            st.error("❌ API Not Available")
            st.warning("Please start the API service:\n```bash\npython api_service.py\n```")
            st.stop()

        st.markdown("---")

        # Settings
        st.subheader("Analysis Settings")
        min_confidence = st.slider(
            "Minimum Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            help="Only show entities with confidence above this threshold"
        )

        auto_refresh = st.checkbox("Auto-refresh results", value=False)
        if auto_refresh:
            refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 10)

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

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
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
            if st.button("📈 Fed raises interest rates", use_container_width=True):
                headline = "Federal Reserve raises interest rates by 0.75 basis points"
                submit_button = True

        with example_col2:
            if st.button("🇬🇧 UK tax increase", use_container_width=True):
                headline = "Rachel Reeves increased the tax"
                submit_button = True

        example_col3, example_col4 = st.columns(2)

        with example_col3:
            if st.button("⚠️ Russia-Ukraine conflict", use_container_width=True):
                headline = "Russia launches missile attack on Ukrainian energy infrastructure"
                submit_button = True

        with example_col4:
            if st.button("🛢️ OPEC production cuts", use_container_width=True):
                headline = "OPEC+ announces surprise oil production cut of 2 million barrels per day"
                submit_button = True

    with col2:
        st.header("ℹ️ How it works")
        st.markdown("""
        1. **Enter** a financial news headline
        2. **Analyze** to see currency impact
        3. **View** confidence levels:
           - 🟢 **High** (>0.7): Strong impact expected
           - 🟡 **Medium** (0.4-0.7): Moderate impact
           - 🔴 **Low** (<0.4): Minor impact
        4. **Read** reasoning for each assessment
        """)

    # Analysis results
    if submit_button and headline.strip():
        with st.spinner("🔄 Analyzing headline..."):
            success, result = analyze_headline(headline, min_confidence)

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
                tab1, tab2, tab3 = st.tabs(["📋 Cards View", "📊 Chart View", "📄 Table View"])

                with tab1:
                    # Card view
                    for entity in entities:
                        display_impact_card(entity)

                with tab2:
                    # Chart view
                    fig = create_confidence_chart(entities)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    # Table view
                    df = pd.DataFrame(entities)
                    df = df.sort_values('confidence_score', ascending=False)

                    # Style the dataframe
                    def style_confidence(val):
                        if val == 'high':
                            return 'background-color: #d4edda; color: #155724;'
                        elif val == 'medium':
                            return 'background-color: #fff3cd; color: #856404;'
                        else:
                            return 'background-color: #f8d7da; color: #721c24;'

                    styled_df = df.style.applymap(style_confidence, subset=['confidence'])
                    st.dataframe(styled_df, use_container_width=True)

                # Export option
                st.markdown("---")
                st.markdown("### 💾 Export Results")

                export_col1, export_col2 = st.columns(2)

                with export_col1:
                    # JSON export
                    json_str = json.dumps(result, indent=2, default=str)
                    st.download_button(
                        label="📥 Download as JSON",
                        data=json_str,
                        file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

                with export_col2:
                    # CSV export
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("⚠️ No entities found above the confidence threshold. Try lowering the minimum confidence in the sidebar.")

        else:
            st.error(f"❌ Analysis failed: {result}")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p>AI Headline Impact Processor v1.0.0-phase1</p>
        <p>Powered by Google Gemini Flash & Economic Knowledge Graphs</p>
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh
    if auto_refresh and 'last_refresh' in st.session_state:
        if time.time() - st.session_state.last_refresh > refresh_interval:
            st.session_state.last_refresh = time.time()
            st.rerun()
    elif auto_refresh:
        st.session_state.last_refresh = time.time()


if __name__ == "__main__":
    main()
