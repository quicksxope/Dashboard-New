import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="📁 Contract Summary Dashboard", layout="wide")
from auth import require_login
require_login()
st.title("📁 Contract Summary Dashboard")

# --- Section Card Function ---
def section_card(title=None):
    section = st.container()
    section_id = f"section_{title.replace(' ', '_').lower() if title else 'no_title'}"
    if title:
        section.markdown(f"""
        <div id=\"{section_id}_header\" style=\"background: linear-gradient(to right, #3498db, #1abc9c); color: white; padding: 12px 15px; border-radius: 10px 10px 0 0; margin-bottom: 0; font-weight: 600; font-size: 1.2rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);\">
            {title}
        </div>
        """, unsafe_allow_html=True)
    return section

# --- Metric Card Function ---
def metric_card(title, value, sub, icon="✅", bg="#2196f3"):
    gradient = f"linear-gradient(135deg, {bg}, {bg})"
    text_color = "#ffffff"
    sub_color = "#e0e0e0"
    shadow_color = "rgba(0, 0, 0, 0.3)"
    return f"""
    <div class=\"metric-card\" style=\"padding:1.2rem; background:{gradient}; border-radius:1rem; box-shadow:0 3px 10px {shadow_color}; text-align:center; margin-bottom:1rem; height:100%; width:100%; max-width:100%; border:none !important; outline:none !important;\">
        <div style=\"font-size:1.5rem; margin-bottom:0.3rem;\">{icon}</div>
        <div style=\"font-size:1.2rem; font-weight:600; color:{text_color}; margin-bottom:0.5rem;\">{title}</div>
        <div style=\"font-size:calc(1.5rem + 0.5vw); font-weight:700; color:{text_color}; margin:0.6rem 0;\">{value}</div>
        <div style=\"color:{sub_color}; font-size:0.9rem;\">{sub}</div>
    </div>
    """


# --- Upload File in Sidebar ---
st.sidebar.header("📂 Upload Your File")
uploaded_file = st.sidebar.file_uploader("Upload Contract Excel File (.xlsx)", type="xlsx") 


if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]

    # Rename for consistency
    df.rename(columns={
        'Start Date': 'START',
        'End Date': 'END',
        'PROGRESS ACTUAL': 'PROGRESS'
    }, inplace=True)

    df['START'] = pd.to_datetime(df['START'], errors='coerce')
    df['END'] = pd.to_datetime(df['END'], errors='coerce')
    df['DURATION'] = (df['END'] - df['START']).dt.days
    df['PROGRESS'] = pd.to_numeric(df['PROGRESS'], errors='coerce')

    today = pd.Timestamp.today()
    df['TIME_GONE'] = ((today - df['START']) / (df['END'] - df['START'])).clip(0, 1) * 100

    # --- Metrics ---
    total_contracts = len(df)
    active_contracts = df[df['STATUS'] == 'ACTIVE'].shape[0]
    non_active_contracts = df[df['STATUS'].str.contains('NON ACTIVE', case=False, na=False)].shape[0]
    active_adendum_contracts = df[df['STATUS'].str.contains("ADENDUM", na=False, case=False)].shape[0]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(metric_card("Total Contracts", total_contracts, "All listed contracts", "📦"), unsafe_allow_html=True)
        st.markdown(metric_card("Active Contracts", active_contracts, "Currently ongoing", "✅"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Non-Active Contracts", non_active_contracts, "Finished or inactive", "🔝"), unsafe_allow_html=True)
        st.markdown(metric_card("Active Adendum Contracts", active_adendum_contracts, "Contracts with Adendum", "📝"), unsafe_allow_html=True)

    # --- Gantt Chart ---
    with section_card("🗖️ Gantt Chart - Contract Timelines"):
        df_sorted = df.sort_values('START')
        df_plot = df_sorted.dropna(subset=['START', 'END'])  # Only valid ones plotted
        fig_gantt = px.timeline(
            df_plot,
            x_start='START',
            x_end='END',
            y='KONTRAK',
            color='STATUS',
            hover_data=['DURATION', 'PROGRESS', 'TIME_GONE'],
            title="Contract Gantt Timeline"
        )
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)


        import plotly.graph_objects as go

        # --- Color Logic ---
        def get_color(pct):
            return '#2ECC71' if pct >= 50 else '#E74C3C'  # Green if ≥50%, Red otherwise

        # --- Build Horizontal Bar Chart with Conditional Color and %
        def build_kpi_bar(df_subset, title):
            fig = go.Figure()
            for _, row in df_subset.iterrows():
                color = get_color(row['REALIZED_PCT'])

                # Realized
                fig.add_trace(go.Bar(
                    y=[row['KONTRAK']],
                    x=[row['REALIZATION']],
                    name='REALIZED',
                    orientation='h',
                    marker=dict(color=color),
                    text=f"{row['REALIZED_PCT']}%",
                    textposition='inside',
                    hovertemplate=(
                        f"<b>{row['KONTRAK']}</b><br>"
                        f"Total Contract: {row['CONTRACT_VALUE']:.1f} M<br>"
                        f"Realized: {row['REALIZATION']:.1f} M<br>"
                        f"Remaining: {row['REMAINING']:.1f} M<br>"
                        f"% Realized: {row['REALIZED_PCT']}%"
                    ),
                    showlegend=False
                ))

                # Remaining
                fig.add_trace(go.Bar(
                    y=[row['KONTRAK']],
                    x=[row['REMAINING']],
                    name='REMAINING',
                    orientation='h',
                    marker=dict(color='#D0D3D4'),
                    text=f"{row['REMAINING']:.1f} M",
                    textposition='inside',
                    hovertemplate=(
                        f"<b>{row['KONTRAK']}</b><br>"
                        f"Total Contract: {row['CONTRACT_VALUE']:.1f} M<br>"
                        f"Realized: {row['REALIZATION']:.1f} M<br>"
                        f"Remaining: {row['REMAINING']:.1f} M<br>"
                        f"% Realized: {row['REALIZED_PCT']}%"
                    ),
                    showlegend=False
                ))

            fig.update_layout(
                barmode='stack',
                title=title,
                xaxis=dict(
                    title="Contract Value (Millions)",
                    tickformat=".0f",
                    showgrid=True,
                    zeroline=True,
                    rangeslider=dict(visible=True)  # Enables zoom via slider
                ),
                yaxis=dict(
                    title="Project",
                    automargin=True
                ),
                height=600,
                margin=dict(l=300, r=50, t=60, b=50),
                dragmode=False  # Disable drag-to-zoom
            )
            return fig

        # --- Prepare Data ---
        df_chart = df.copy()
        df_chart.rename(columns={
            'Nilai Kontrak 2023-2024': 'CONTRACT_VALUE',
            'Realisasi On  2023-2024': 'REALIZATION'
        }, inplace=True)

        df_chart = df_chart[df_chart['CONTRACT_VALUE'].notna() & df_chart['REALIZATION'].notna()].copy()
        df_chart['REMAINING'] = df_chart['CONTRACT_VALUE'] - df_chart['REALIZATION']
        df_chart[['REALIZATION', 'REMAINING']] = df_chart[['REALIZATION', 'REMAINING']].clip(lower=0)
        df_chart['REALIZED_PCT'] = (df_chart['REALIZATION'] / df_chart['CONTRACT_VALUE'] * 100).round(1)
        df_chart.sort_values(by='CONTRACT_VALUE', ascending=False, inplace=True)

        # Split top 5 and others
        top5 = df_chart.head(5)
        others = df_chart.iloc[5:]

        # --- Display in Streamlit ---
        with section_card("📊 Top 5 Contracts (Realization % and Conditional Color)"):
            fig_top5 = build_kpi_bar(top5, "Top 5 Contracts by Value")
            st.plotly_chart(fig_top5, use_container_width=True, config={
                'scrollZoom': False,  # disable scroll-to-zoom
                'displaylogo': False,
                'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                'displayModeBar': 'always'
            })

        with section_card("📊 Remaining Contracts (Scaled View)"):
            fig_others = build_kpi_bar(others, "Remaining Contracts by Value")
            st.plotly_chart(fig_others, use_container_width=True, config={
                'scrollZoom': False,  # disable scroll-to-zoom
                'displaylogo': False,
                'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                'displayModeBar': 'always'
            })




    # --- Time-Based Progress Category ---
        with section_card("📈 Project Progress Categories (Based on Time Elapsed)"):
            bins = [-1, 30, 50, 80, 100]
            labels = ['<30%', '30-50%', '50-80%', '>80%']
            df['TIME_GONE_CAT'] = pd.cut(df['TIME_GONE'], bins=bins, labels=labels)

            progress_counts = df['TIME_GONE_CAT'].value_counts().sort_index().reset_index()
            progress_counts.columns = ['Progress Range', 'Count']
            fig_progress = px.bar(progress_counts, x='Progress Range', y='Count', color='Progress Range',
                                title="Project Progress by Time Elapsed", text='Count')
            st.plotly_chart(fig_progress, use_container_width=True)

    # --- Status Pie Chart and Filter Table ---
    with section_card("📊 Contract Status Distribution and Filter"):
        col_pie, col_table = st.columns(2)

        with col_pie:
            status_counts = df['STATUS'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_status = px.pie(status_counts, names='Status', values='Count', hole=0.4)
            st.plotly_chart(fig_status, use_container_width=True)

        with col_table:
            status_filter = st.selectbox("Select Status", options=["All"] + df['STATUS'].unique().tolist())
            if status_filter == "All":
                filtered_df = df
            else:
                filtered_df = df[df['STATUS'] == status_filter]

            st.dataframe(filtered_df[['KONTRAK', 'START', 'END', 'DURATION', 'STATUS', 'PROGRESS', 'TIME_GONE']].sort_values('END'), use_container_width=True)

    # --- Full Contract Table ---
    with section_card("📋 Full Contract Table"):
        st.dataframe(df[['KONTRAK', 'START', 'END', 'DURATION', 'STATUS', 'PROGRESS', 'TIME_GONE']].sort_values('END'), use_container_width=True)

else:
    st.info("Upload an Excel file containing the contract data.")
