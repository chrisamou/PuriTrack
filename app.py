import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# 1. Page Configuration
st.set_page_config(page_title="PuriTrack Dashboard", layout="wide", page_icon="🧪")
st.title("🧪 PuriTrack: Purification Operations")
st.markdown("Monitor instrument utilization, column health, and solvent consumption across the automated purification fleet.")

# 2. Mock Data Generator (Teledyne vs. Büchi Logic)
@st.cache_data
def generate_mock_data():
    np.random.seed(42)
    dates = [datetime.today() - timedelta(days=i) for i in range(30)]
    
    data = []
    for i in range(600):
        # 70% chance it's a Flash run, 30% chance it's Prep-HPLC
        is_flash = np.random.choice([True, False], p=[0.7, 0.3])
        
        if is_flash:
            instrument = np.random.choice(["Büchi-Flash-01", "Büchi-Flash-02", "Büchi-Flash-03"])
            col = "Disposable (Plastic)"
            run_time = np.random.normal(loc=25.0, scale=5.0) 
            solvent_vol = run_time * np.random.uniform(40, 80) # Flash uses lots of solvent
            success = np.random.choice([True, False], p=[0.95, 0.05])
        else:
            instrument = np.random.choice(["Teledyne-Prep-01", "Teledyne-Prep-02"])
            col = np.random.choice(["C18-Prep-A", "C18-Prep-B", "C8-Prep-A"])
            run_time = np.random.normal(loc=12.0, scale=2.0)
            solvent_vol = run_time * np.random.uniform(15, 30) # HPLC uses less solvent
            success = np.random.choice([True, False], p=[0.88, 0.12])

        purity = np.random.normal(loc=96.0, scale=2.5) if success else np.random.normal(loc=65.0, scale=15.0)
        
        data.append({
            "Date": np.random.choice(dates),
            "Instrument": instrument,
            "Type": "Flash" if is_flash else "Prep-HPLC",
            "Column_ID": col,
            "Run_Time_Min": round(run_time, 1),
            "Solvent_Used_mL": round(solvent_vol, 1),
            "Success": success,
            "Final_Purity_%": min(100.0, round(purity, 1))
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values("Date").reset_index(drop=True)
    return df

df = generate_mock_data()

# 3. Sidebar Filters
st.sidebar.header("⚙️ Dashboard Filters")
st.sidebar.info("💡 **Demo Mode Active:** Generating 30 days of simulated Chemify fleet data.")

selected_types = st.sidebar.multiselect("Filter by Instrument Type", options=df["Type"].unique(), default=df["Type"].unique())
filtered_df = df[df["Type"].isin(selected_types)]

st.sidebar.divider()
st.sidebar.markdown("**Upload Real Data (Future Feature)**")
uploaded_file = st.sidebar.file_uploader("Upload Instrument CSV", type=["csv"])

# 4. Top Level KPIs
st.subheader("📈 Fleet Performance KPIs (Last 30 Days)")
col1, col2, col3, col4 = st.columns(4)

total_runs = len(filtered_df)
success_rate = (filtered_df["Success"].sum() / total_runs) * 100 if total_runs > 0 else 0
total_solvent_L = filtered_df["Solvent_Used_mL"].sum() / 1000
avg_purity = filtered_df[filtered_df["Success"] == True]["Final_Purity_%"].mean() if total_runs > 0 else 0

col1.metric("Total Purifications", f"{total_runs}")
col2.metric("Overall Success Rate", f"{success_rate:.1f}%")
col3.metric("Total Solvent Consumed", f"{total_solvent_L:.1f} L")
col4.metric("Avg Successful Purity", f"{avg_purity:.1f}%")

st.divider()

# 5. Visualizations
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("🤖 Instrument Utilization")
    utilization = filtered_df.groupby(["Instrument", "Type"]).size().reset_index(name="Runs")
    fig_util = px.bar(utilization, x="Instrument", y="Runs", color="Type", template="plotly_white", color_discrete_map={"Flash": "#3b82f6", "Prep-HPLC": "#8b5cf6"})
    st.plotly_chart(fig_util, use_container_width=True)

with col_chart2:
    st.subheader("💧 Solvent Consumption Trend")
    solvent_trend = filtered_df.groupby("Date")["Solvent_Used_mL"].sum().reset_index()
    solvent_trend["Solvent_Used_L"] = solvent_trend["Solvent_Used_mL"] / 1000
    fig_solv = px.line(solvent_trend, x="Date", y="Solvent_Used_L", markers=True, template="plotly_white")
    fig_solv.update_traces(line_color="#10b981")
    st.plotly_chart(fig_solv, use_container_width=True)

# 6. Column Health Alerts (Excludes Disposables)
st.subheader("🚨 Teledyne Reusable Column Health")
st.markdown("Tracking cumulative injections on Prep-HPLC columns to optimize replacement cycles.")

# Filter out the disposable columns for this table
reusable_df = filtered_df[filtered_df["Column_ID"] != "Disposable (Plastic)"]

if not reusable_df.empty:
    column_health = reusable_df.groupby("Column_ID").agg(
        Total_Injections=("Column_ID", "count"),
        Avg_Purity=("Final_Purity_%", "mean")
    ).reset_index()

    # Flag columns with more than 50 injections
    column_health["Status"] = column_health["Total_Injections"].apply(lambda x: "🔴 REPLACE SOON" if x > 50 else "🟢 HEALTHY")

    st.dataframe(
        column_health.style.applymap(lambda x: "background-color: #fca5a5" if "REPLACE" in str(x) else "background-color: #bbf7d0", subset=["Status"]),
        use_container_width=True
    )
else:
    st.info("No reusable columns in the current filtered view.")
