import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import requests
from io import BytesIO
from datetime import datetime
from auth import require_login

st.set_page_config(page_title="📁 Contract Summary Dashboard", layout="wide")
require_login()

# --- GitHub fallback URLs ---
GITHUB_CONTRACT_FILE_URL = "https://raw.githubusercontent.com/quicksxope/Dashboard-New/main/data/data_kontrak_new.xlsx"
GITHUB_FINANCIAL_FILE_URL = "https://raw.githubusercontent.com/quicksxope/Dashboard-New/main/data/Rekap_Vendor_Pembayaran_Final.xlsx"

# --- Utility functions ---
def get_file_hash(file):
    return hashlib.md5(file.getvalue()).hexdigest()

@st.cache_data(ttl=3600)
def load_excel_from_github(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            return None
    except Exception as e:
        st.warning(f"Error fetching from GitHub: {e}")
        return None

# --- UI Title ---
st.markdown("""
<div style="
    background: linear-gradient(to right, #3498db, #2ecc71);
    padding: 1.2rem 2rem;
    font-size: 2rem;
    font-weight: 800;
    color: white;
    border-radius: 12px;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    margin-bottom: 1.5rem;">
    Contract Summary
</div>
""", unsafe_allow_html=True)

# --- UI Components ---
def section_card(title=None):
    section = st.container()
    if title:
        section.markdown(f"""
        <div style="background: linear-gradient(to right, #3498db, #1abc9c); color: white; padding: 12px 15px; 
                    border-radius: 10px 10px 0 0; margin-bottom: 0; font-weight: 600; font-size: 1.2rem;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.3); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            {title}
        </div>
        """, unsafe_allow_html=True)
    return section

def metric_card(title, value, sub, icon="✅", bg="#2196f3"):
    return f"""
    <div style="padding:1.2rem; background:linear-gradient(135deg, {bg}, {bg}); border-radius:1rem;
        box-shadow:0 3px 10px rgba(0, 0, 0, 0.3); text-align:center; margin-bottom:1rem;">
        <div style="font-size:1.5rem;">{icon}</div>
        <div style="font-size:1.2rem; font-weight:600; color:#fff; margin-bottom:0.5rem;">{title}</div>
        <div style="font-size:2rem; font-weight:700; color:#fff;">{value}</div>
        <div style="color:#e0e0e0; font-size:0.9rem;">{sub}</div>
    </div>
    """

# --- Upload Area ---
contract_file_uploaded = st.sidebar.file_uploader("Upload Contract Excel File (.xlsx)", type="xlsx")
financial_file_uploaded = st.sidebar.file_uploader("Upload Financial Progress Excel (.xlsx)", type="xlsx", key="finance")

# --- Load Contract Data ---
if contract_file_uploaded:
    file_hash = get_file_hash(contract_file_uploaded)
    if st.session_state.get("contract_file_hash") != file_hash:
        st.session_state.contract_file_hash = file_hash
        st.session_state.contract_upload_time = datetime.now()
    contract_data = pd.read_excel(BytesIO(contract_file_uploaded.getvalue()))
    st.sidebar.success(f"Last Contract Upload: {st.session_state.contract_upload_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    contract_bytes = load_excel_from_github(GITHUB_CONTRACT_FILE_URL)
    if contract_bytes:
        contract_data = pd.read_excel(contract_bytes)
        st.sidebar.info("Using default contract file from GitHub")
    else:
        st.error("Failed to load contract data from GitHub")
        st.stop()

# --- Load Financial Data ---
if financial_file_uploaded:
    file_hash = get_file_hash(financial_file_uploaded)
    if st.session_state.get("financial_file_hash") != file_hash:
        st.session_state.financial_file_hash = file_hash
        st.session_state.financial_upload_time = datetime.now()
    financial_data = pd.read_excel(BytesIO(financial_file_uploaded.getvalue()))
    st.sidebar.success(f"Last Financial Upload: {st.session_state.financial_upload_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    financial_bytes = load_excel_from_github(GITHUB_FINANCIAL_FILE_URL)
    if financial_bytes:
        try:
            financial_data = pd.read_excel(financial_bytes)
            st.sidebar.info("Using default financial file from GitHub")
        except Exception as e:
            st.error(f"Failed to read financial data from GitHub: {e}")
            st.stop()
    else:
        st.error("Failed to load financial data from GitHub")
        st.stop()

# --- Visualizations ---
st.success("Data successfully loaded and ready for visualization.")

# Clean contract columns
contract_data.columns = [str(col).strip() for col in contract_data.columns]
contract_data.rename(columns={
    'Start Date': 'START',
    'End Date': 'END',
    'PROGRESS ACTUAL': 'PROGRESS'
}, inplace=True)
contract_data['START'] = pd.to_datetime(contract_data['START'], errors='coerce')
contract_data['END'] = pd.to_datetime(contract_data['END'], errors='coerce')
contract_data['DURATION'] = (contract_data['END'] - contract_data['START']).dt.days
contract_data['PROGRESS'] = pd.to_numeric(contract_data['PROGRESS'], errors='coerce')
contract_data['TIME_GONE'] = ((pd.Timestamp.today() - contract_data['START']) / (contract_data['END'] - contract_data['START'])).clip(0, 1) * 100

# Metrics
with st.columns(2)[0]:
    st.markdown(metric_card("Total Contracts", len(contract_data), "All listed contracts", "📦"), unsafe_allow_html=True)
    st.markdown(metric_card("Active Contracts", contract_data[contract_data['STATUS'] == 'ACTIVE'].shape[0], "Currently ongoing", "✅"), unsafe_allow_html=True)
with st.columns(2)[1]:
    st.markdown(metric_card("Non-Active Contracts", contract_data[contract_data['STATUS'].str.contains('NON ACTIVE', case=False, na=False)].shape[0], "Finished or inactive", "🔝"), unsafe_allow_html=True)
    st.markdown(metric_card("Active Adendum Contracts", contract_data[contract_data['STATUS'].str.contains("ADENDUM", na=False, case=False)].shape[0], "Contracts with Adendum", "📝"), unsafe_allow_html=True)

# Gantt Chart
with section_card("🗖️ Gantt Chart - Contract Timelines"):
    df_plot = contract_data.dropna(subset=['START', 'END']).sort_values('START')
    fig_gantt = px.timeline(df_plot, x_start='START', x_end='END', y='KONTRAK', color='STATUS',
                            hover_data=['DURATION', 'PROGRESS', 'TIME_GONE'], title="Contract Gantt Timeline")
    fig_gantt.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_gantt, use_container_width=True)

# KPI Bar Chart

def get_color(pct):
    return '#2ECC71' if pct >= 50 else '#E74C3C'

def build_kpi_bar(df_subset, title="Progress Pembayaran (%)"):
    fig = go.Figure()
    for _, row in df_subset.iterrows():
        color = get_color(row['REALIZED_PCT'])
        fig.add_trace(go.Bar(
            y=[row['Vendor']], x=[row['REALIZED_PCT']], name='REALIZED (%)', orientation='h',
            marker_color=color, text=f"{row['REALIZED_PCT']:.1f}%", textposition='inside',
            hovertemplate=(f"<b>{row['Vendor']}</b><br>Total Kontrak: Rp {row['CONTRACT_VALUE']:,.0f}<br>"
                           f"Terbayarkan: Rp {row['REALIZATION']:,.0f}<br>"
                           f"Sisa: Rp {row['REMAINING']:,.0f}<br>"
                           f"% Realisasi: {row['REALIZED_PCT']:.1f}%<extra></extra>"), showlegend=False))
        fig.add_trace(go.Bar(
            y=[row['Vendor']], x=[100 - row['REALIZED_PCT']], name='REMAINING (%)', orientation='h',
            marker_color="#D0D3D4", text=f"{100 - row['REALIZED_PCT']:.1f}%", textposition='inside',
            hoverinfo="skip", showlegend=False))
    fig.update_layout(barmode='stack', title=title, xaxis=dict(title="Progress (%)", range=[0, 100]),
                      yaxis=dict(title="", automargin=True), height=700)
    return fig

if 'REALIZED_PCT' in financial_data.columns:
    with section_card("📊 Financial Progress Chart"):
        fig_fin = build_kpi_bar(financial_data, "Progress Pembayaran Seluruh Kontrak")
        st.plotly_chart(fig_fin, use_container_width=True)
