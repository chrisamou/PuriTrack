import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="PuriTrack Dashboard", layout="wide", page_icon="🧪")
st.title("🧪 PuriTrack: Purification Operations")

# 2. Database Initialization (The Persistent Storage)
DB_FILE = "puritrack_db.csv"

def load_data():
    if not os.path.exists(DB_FILE):
        # Create an empty database if it doesn't exist yet
        df = pd.DataFrame(columns=[
            "Date", "Run_ID", "Instrument", "Type", "Column_ID", 
            "Run_Time_Min", "Solvent_Used_mL", "Success", "Final_Purity_%"
        ])
        df.to_csv(DB_FILE, index=False)
        return df
    return pd.read_csv(DB_FILE)

# Load the database into memory
df = load_data()

# Convert Date column to actual datetime objects for filtering
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

# 3. Create the App Interface (Tabs)
tab1, tab2 = st.tabs(["📊 Analytics & Reports", "📝 Daily Data Entry"])

# ==========================================
# TAB 1: DATA ENTRY FORM
# ==========================================
with tab2:
    st.subheader("Log a New Purification Run")
    st.markdown("Enter the run details below. This will be permanently saved to the database.")
    
    with st.form("data_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            run_date = st.date_input("Run Date", datetime.today())
            run_id = st.text_input("Run ID / Compound Name (e.g., CHEM-1042)")
            
            instrument_type = st.selectbox("Instrument Type", ["Prep-HPLC (Teledyne)", "Flash (Büchi)"])
            
            if instrument_type == "Prep-HPLC (Teledyne)":
                instrument = st.selectbox("Select Instrument", ["Teledyne-Prep-01", "Teledyne-Prep-02"])
                column_id = st.selectbox("Select Column", ["C18-Prep-A", "C18-Prep-B", "C8-Prep-A"])
            else:
                instrument = st.selectbox("Select Instrument", ["Büchi-Flash-01", "Büchi-Flash-02", "Büchi-Flash-03"])
                column_id = "Disposable (Plastic)"
                st.info("Flash systems automatically default to Disposable columns.")
                
        with col2:
            run_time = st.number_input("Run Time (Minutes)", min_value=0.0, step=0.5, value=15.0)
            solvent_used = st.number_input("Solvent Consumed (mL)", min_value=0.0, step=10.0, value=250.0)
            success = st.checkbox("Run Successful? (Target peak isolated)", value=True)
            purity = st.number_input("Final Purity (%)", min_value=0.0, max_value=100.0, step=0.1, value=95.0)
            
        submitted = st.form_submit_button("💾 Save Run to Database")
        
        if submitted:
            if run_id == "":
                st.error("Please enter a Run ID.")
            else:
                # Create a new row of data
                new_data = pd.DataFrame([{
                    "Date": run_date,
                    "Run_ID": run_id,
                    "Instrument": instrument,
                    "Type": "Flash" if "Flash" in instrument_type else "Prep-HPLC",
                    "Column_ID": column_id,
                    "Run_Time_Min": run_time,
                    "Solvent_Used_mL": solvent_used,
                    "Success": success,
                    "Final_Purity_%": purity
                }])
                
                # Append to the CSV file
                new_data.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
                st.success(f"Successfully logged {run_id}!")
                st.rerun() # Instantly refresh the app to update the charts

# ==========================================
# TAB 2: ANALYTICS & WEEKLY REPORTS
# ==========================================
with tab1:
    if df.empty:
        st.info("📭 The database is currently empty. Go to the 'Daily Data Entry' tab to log your first run!")
    else:
        # Sidebar Report Filters
        st.sidebar.header("📅 Report Filters")
        
        # Calculate dates for "This Week" filtering
        today = datetime.today().date()
        seven_days_ago = today - pd.Timedelta(days=7)
        
        time_filter = st.sidebar.radio("Time Range", ["All Time", "Last 7 Days (Weekly Report)"])
        
        if time_filter == "Last 7 Days (Weekly Report)":
            filtered_df = df[df["Date"] >= seven_days_ago]
            st.subheader("📅 Weekly Purification Report")
        else:
            filtered_df = df
            st.subheader("📈 All-Time Fleet Analytics")

        selected_types = st.sidebar.multiselect("Filter by Instrument Type", options=filtered_df["Type"].unique(), default=filtered_df["Type"].unique())
        filtered_df = filtered_df[filtered_df["Type"].isin(selected_types)]
        
        if filtered_df.empty:
            st.warning("No data matches the current filters.")
        else:
            # Top Level KPIs
            col1, col2, col3, col4 = st.columns(4)
            total_runs = len(filtered_df)
            success_rate = (filtered_df["Success"].sum() / total_runs) * 100
            total_solvent_L = filtered_df["Solvent_Used_mL"].sum() / 1000
            avg_purity = filtered_df[filtered_df["Success"] == True]["Final_Purity_%"].mean()

            col1.metric("Purifications Logged", f"{total_runs}")
            col2.metric("Success Rate", f"{success_rate:.1f}%")
            col3.metric("Solvent Consumed", f"{total_solvent_L:.1f} L")
            col4.metric("Avg Purity", f"{avg_purity:.1f}%")

            st.divider()

            # Visualizations
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("**🤖 Instrument Utilization**")
                utilization = filtered_df.groupby(["Instrument", "Type"]).size().reset_index(name="Runs")
                fig_util = px.bar(utilization, x="Instrument", y="Runs", color="Type", template="plotly_white", color_discrete_map={"Flash": "#3b82f6", "Prep-HPLC": "#8b5cf6"})
                st.plotly_chart(fig_util, use_container_width=True)

            with col_chart2:
                st.markdown("**💧 Solvent Consumption Trend**")
                solvent_trend = filtered_df.groupby("Date")["Solvent_Used_mL"].sum().reset_index()
                solvent_trend["Solvent_Used_L"] = solvent_trend["Solvent_Used_mL"] / 1000
                fig_solv = px.line(solvent_trend, x="Date", y="Solvent_Used_L", markers=True, template="plotly_white")
                fig_solv.update_traces(line_color="#10b981")
                st.plotly_chart(fig_solv, use_container_width=True)

            # Column Health Alerts
            st.subheader("🚨 Teledyne Reusable Column Health")
            reusable_df = filtered_df[filtered_df["Column_ID"] != "Disposable (Plastic)"]

            if not reusable_df.empty:
                column_health = reusable_df.groupby("Column_ID").agg(
                    Total_Injections=("Column_ID", "count"),
                    Avg_Purity=("Final_Purity_%", "mean")
                ).reset_index()

                column_health["Status"] = column_health["Total_Injections"].apply(lambda x: "🔴 REPLACE SOON" if x > 50 else "🟢 HEALTHY")
                
                st.dataframe(
                    column_health.style.applymap(lambda x: "background-color: #fca5a5" if "REPLACE" in str(x) else "background-color: #bbf7d0", subset=["Status"]),
                    use_container_width=True
                )
            else:
                st.info("No reusable columns logged in this time period.")
                
            # Show the raw database table at the bottom
            with st.expander("📂 View Raw Database Log"):
                st.dataframe(filtered_df, use_container_width=True)
