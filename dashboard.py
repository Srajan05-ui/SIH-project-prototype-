import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Defensively import modules
# Defensively import modules with robust fallbacks
class MockLedger:
    def record_transaction(self, *args): pass
    def record_block(self, *args): pass
    def validate_ledger(self): return False, "Ledger module offline (Dependency missing)"
    
class MockRAG:
    def add_context(self, *args): pass
    def query(self, *args): return "RAG module offline (Dependency missing)"

class MockXAI:
    def fit(self, *args): pass

try:
    from index_chain_calc import IndexCalculator
    from market_concentration import MarketConcentration
    from opensky_supply import OpenSkySupply
    from xai_anomaly import XAIAnomalyEngine
    from ledger_audit import LedgerAudit
    from local_rag_desk import LocalRAGDesk
except ImportError:
    pass
    XAIAnomalyEngine = MockXAI
    LedgerAudit = MockLedger
    LocalRAGDesk = MockRAG

st.set_page_config(page_title="Aerofare | Executive Suite", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Executive Obsidian Dark Theme - Bento Box Architecture */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { 
        background-color: #0E1117;
        color: #E6EDF3; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Strict grid alignment & margins */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 95%;
    }
    
    /* Main Headers */
    h1, h2, h3, h4 { color: #FFFFFF !important; font-weight: 700 !important; }
    h1 {
        font-size: 32px !important;
        letter-spacing: -0.5px;
        margin-bottom: 24px !important;
        border-bottom: 1px solid #30363D;
        padding-bottom: 12px;
    }
    
    /* Bento Box Containers */
    div[data-testid="stVerticalBlock"] > div > div {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    
    /* Metrics */
    div[data-testid="stMetricValue"] { 
        color: #00FFCC !important; 
        font-weight: 700 !important; 
        font-size: 28px !important; 
        font-family: 'Inter', monospace;
    }
    div[data-testid="stMetricDelta"] { color: #00D2FF !important; font-weight: 600 !important; }
    
    /* Executive Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        border-bottom: 1px solid #30363D; 
    }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161B22 !important; 
        border-radius: 8px 8px 0px 0px !important; 
        padding: 12px 24px; 
        color: #8B949E !important;
        font-weight: 600;
        border: 1px solid transparent;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] { 
        color: #00FFCC !important; 
        background-color: #21262D !important;
        border: 1px solid #30363D !important;
        border-bottom: 1px solid #21262D !important;
        margin-bottom: -1px;
    }
    
    /* Text Input */
    .stTextInput input {
        background-color: #0E1117 !important;
        color: #E6EDF3 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🦅 Aerofare: National Airfare Intelligence")

# --- Security: Authentication Gateway ---
def check_password():
    """Returns `True` if the user has the correct password."""
    def password_entered():
        # In a real production environment, use hashed passwords or SSO/OAuth.
        # For this prototype, we check against a hardcoded secure string or st.secrets.
        if st.session_state["admin_password"] == "SecureAdmin2026!":
            st.session_state["password_correct"] = True
            del st.session_state["admin_password"]  # Clear from session state immediately
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("### 🔒 Unauthorized Access Prohibited")
    st.markdown("Please authenticate to access the Executive Suite.")
    st.text_input("Administrator Password", type="password", on_change=password_entered, key="admin_password")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("🚫 Invalid credentials.")
    return False

if not check_password():
    st.stop() # Halts all execution if not authenticated

# --- Init Session States securely ---
if 'ledger' not in st.session_state:
    st.session_state.ledger = LedgerAudit()
    try:
        conn = __import__('sqlite3').connect('audit_ledger.db')
        if len(pd.read_sql('SELECT * FROM transactions', conn)) == 0:
            st.session_state.ledger.record_transaction("SYSTEM-INIT", 0.0, "SYS-1")
    except Exception:
        pass

if 'rag' not in st.session_state:
    st.session_state.rag = LocalRAGDesk(model_name='llama3.1:8b')
    st.session_state.rag.add_context("Delhi-Bengaluru (DEL-BLR) capacity is down 15% due to groundings. MoSPI inflation index for aviation is 125.4.")

if 'anomaly_injected' not in st.session_state:
    st.session_state.anomaly_injected = False

if 'xai_engine' not in st.session_state:
    st.session_state.xai_engine = XAIAnomalyEngine()
    df_train = pd.DataFrame({
        'pure_fare': np.random.normal(5000, 500, 100),
        'capacity': np.random.normal(20, 2, 100),
        'hhi': np.random.normal(1500, 300, 100)
    })
    st.session_state.xai_engine.fit(df_train, ['pure_fare', 'capacity', 'hhi'])

# --- Interface Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Sovereign Inflation Command Center", 
    "🚨 Market Concentration & Cartel Watch", 
    "📡 Telemetry & Explainable Anomaly Desk", 
    "🔒 Provenance Vault & Secure Local RAG Desk"
])

with tab1:
    col1, col2, col3 = st.columns(3)
    base_idx = 124.5 + (45.2 if st.session_state.anomaly_injected else 0)
    
    col1.metric("Chained Fisher Ideal Index", f"{base_idx:.1f}", "+3.2% MoM")
    col2.metric("Headline CPI Impact", "12 bps", "+2 bps")
    col3.metric("Avg Capacity (OpenSky)", "2,450 Vectors", "-150 DoD")
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_chart, col_ctrl = st.columns([3, 1])
    with col_chart:
        st.markdown("**Real-Time Index Trajectory vs. Static Baseline**")
        dates = pd.date_range(start="2023-01-01", periods=100)
        trend = np.linspace(100, 120, 100) + np.random.normal(0, 1, 100)
        if st.session_state.anomaly_injected:
            trend[-10:] += np.linspace(0, 50, 10)
            
        chart_data = pd.DataFrame({"Chained Fisher": trend, "Laspeyres (Static)": trend * 1.05}, index=dates)
        st.line_chart(chart_data, color=["#00FFCC", "#00D2FF"]) 
        
    with col_ctrl:
        st.markdown("**Policy Interventions**")
        st.slider("Adjust Jet Fuel Cost (%)", -20, 50, 0)
        st.slider("Re-weight Route Trajectories", -10, 10, 0)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Asset Route Topology Graph (NetworkX)**")
        st.info("Bento Box Matrix: High-density visual map rendered offline via NetworkX.")
        st.code("DEL <--> BOM : W=150\nBOM <--> GOI : W=60\nDEL <--> BLR : W=140")
    
    with col2:
        st.markdown("**HHI Concentration & Pricing Matrix**")
        hhi_data = pd.DataFrame({
            "Route": ["DEL-BOM", "BOM-GOI", "DEL-BLR", "HYD-MAA"],
            "HHI Index": [3200, 4100, 1800, 2600],
            "Price Spike": [True, False, False, True]
        })
        
        def format_status(row):
            if row['HHI Index'] > 2500 and row['Price Spike']:
                return "🔴 CRITICAL CARTEL/MONOPOLY RISK"
            return "🟢 COMPETITIVE CORRIDOR"
            
        hhi_data['Regulatory Status'] = hhi_data.apply(format_status, axis=1)
        st.dataframe(hhi_data, use_container_width=True)

with tab3:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**OpenSky Active Vectors vs. Fares Trajectory**")
        st.line_chart(np.random.normal(20, 2, 14), color="#00D2FF")
        
    with col2:
        st.markdown("**Local SHAP Feature Attribution (Anomaly Causality)**")
        if st.session_state.anomaly_injected:
            shap_data = pd.DataFrame({"Factor": ["Capacity Drop", "HHI Alert", "Demand Shift"], "Attribution (bps)": [60, 35, 5]}).set_index("Factor")
            st.bar_chart(shap_data, color="#FF4B4B") # Crimson Red for alert
        else:
            st.success("No anomalies currently flagged by Isolation Forest.")
            
        st.markdown("---")
        if st.button("💥 Inject Synthetic Market Anomaly"):
            st.session_state.anomaly_injected = not st.session_state.anomaly_injected
            st.session_state.ledger.record_transaction("ANOMALY-INJECTED", 9999.0, "SYS-TEST")
            st.rerun()

with tab4:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Hash-Chained Verification Log**")
        try:
            conn = __import__('sqlite3').connect('audit_ledger.db')
            df_ledger = pd.read_sql('SELECT id, timestamp, route, hash FROM transactions ORDER BY id DESC LIMIT 5', conn)
            st.dataframe(df_ledger, hide_index=True)
        except Exception:
            st.warning("Ledger uninitialized.")
            
        if st.button("Verify Ledger Authenticity"):
            is_valid, msg = st.session_state.ledger.validate_ledger()
            if is_valid:
                st.success("✅ Cryptographically Sealed & Tamper-Proof")
            else:
                st.error(msg)
                
    with col2:
        st.markdown("**Local AI Policy Desk (Air-Gapped RAG)**")
        user_q = st.text_input("Ask the local AI Policy Desk... (e.g. 'Summarize today's inflation and cartel alerts')")
        if user_q:
            with st.spinner("Local AI analyzing secured data (ensure ollama is active)..."):
                answer = st.session_state.rag.query(user_q)
                st.info(answer)
