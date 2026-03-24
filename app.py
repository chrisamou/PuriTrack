import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="PuriTrack Dashboard", layout="wide", page_icon="🧪")
st.title("🧪 PuriTrack: Purification Operations")

# 2. Database Initialization (Added Mass, Injections, and pH)
DB_FILE = "puritrack_db.csv"

def load_data():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            "Date", "Run_ID", "Instrument", "Type", "Column_ID", 
            "Sample_Mass_mg", "Injections", "pH", "Success"
        ])
        df.to_csv(DB_FILE, index=False)
        return df
    return pd.read_csv(DB_FILE)

df = load_data()

if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

# 3. Create the App Interface (Tabs)
tab1, tab2 = st.tabs(["📊 Analytics & Reports", "📝 Daily Data Entry"])

# ==========================================
# TAB 1: DATA ENTRY FORM
# ==========================================
with tab2:
    st.subheader("Log a New Purification Run")
    st.markdown("Enter the run details below. Keep it quick and accurate.")
    
    with st.form("data_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            run_date = st.date_input("Run Date", datetime.today())
            run_id = st.text_input("Run ID / Compound Name (e.g., CHEM-1042)")
            
            instrument_type = st.selectbox("Instrument Type", ["Prep-HPLC (Teledyne)", "Flash (Büchi)"])
            
            if instrument_type == "Prep-HPLC (Teledyne)":
                instrument = st.selectbox("Select Instrument", [f"Teledyne-Prep-{i}" for i in range(1, 4)])
                column_id = st.selectbox("Select Column", ["C18-Prep-A", "C18-Prep-B", "C8-Prep-A", "Chiral-OD"])
            else:
                instrument = st.selectbox("Select Instrument", [f"Büchi-Flash-{i}" for i in range(1, 9)])
                column_id = "Disposable (Plastic)"
                st.info("Flash systems automatically default to Disposable columns.")
                
        with col2:
            # ⚡ NEW: The three requested inputs
            sample_mass = st.number_input("Sample Mass (mg)", min_value=0.0, step=50.0, value=100.0)
            injections = st.number_input("Number of Injections", min_value=1, step=1, value=1)
            ph_value = st.number_input("Method pH", min_value=0.0, max_value=14.0, step=0.1, value=7.0)
            
            st.write("") # Spacer
            success = st.checkbox("✅ Run Successful? (Target peak isolated)", value=True)
            
        submitted = st.form_submit_button("💾 Save Run to Database")
        
        if submitted:
            if run_id == "":
                st.error("Please enter a Run ID.")
            else:
                new_data = pd.DataFrame([{
                    "Date": run_date,
                    "Run_ID": run_id,
                    "Instrument": instrument,
                    "Type": "Flash" if "Flash" in instrument_type else "Prep-HPLC",
                    "Column_ID": column_id,
                    "Sample_Mass_mg": sample_mass,
                    "Injections": injections,
                    "pH": ph_value,
                    "Success": success
                }])
                
                new_data.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
                st.success(f"Successfully logged {run_id}!")
                st.rerun()

# ==========================================
# TAB 2: ANALYTICS & WEEKLY REPORTS
# ==========================================
with tab1:
    if df.empty:
        st.info("📭 The database is currently empty. Go to the 'Daily Data Entry' tab to log your first run!")
    else:
        st.sidebar.header("📅 Report Filters")
        
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
            # ⚡ UPGRADED KPIs
            col1, col2, col3, col4 = st.columns(4)
            total_runs = len(filtered_df)
            success_rate = (filtered_df["Success"].sum() / total_runs) * 100 if total_runs > 0 else 0
            
            # Convert total mg to grams for the dashboard
            total_mass_g = filtered_df["Sample_Mass_mg"].sum() / 1000 
            total_injections = filtered_df["Injections"].sum()

            col1.metric("Total Purifications", f"{total_runs}")
            col2.metric("Overall Success Rate", f"{success_rate:.1f}%")
            col3.metric("Total Mass Processed", f"{total_mass_g:.2f} g")
            col4.metric("Total Injections", f"{total_injections}")

            st.divider()

            # Visualizations
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("**🤖 Instrument Utilization**")
                utilization = filtered_df.groupby(["Instrument", "Type"]).size().reset_index(name="Runs")
                fig_util = px.bar(utilization, x="Instrument", y="Runs", color="Type", template="plotly_white", color_discrete_map={"Flash": "#3b82f6", "Prep-HPLC": "#8b5cf6"})
                st.plotly_chart(fig_util, use_container_width=True)

            with col_chart2:
                st.markdown("**📅 Runs per Day Trend**")
                trend = filtered_df.groupby("Date").size().reset_index(name="Total Runs")
                fig_trend = px.line(trend, x="Date", y="Total Runs", markers=True, template="plotly_white")
                fig_trend.update_traces(line_color="#10b981")
                fig_trend.update_yaxes(dtick=1)
                st.plotly_chart(fig_trend, use_container_width=True)

            # ⚡ UPGRADED: Column Health Alerts (Now sums actual injections)
            st.subheader("🚨 Teledyne Reusable Column Health")
            reusable_df = filtered_df[filtered_df["Column_ID"] != "Disposable (Plastic)"]

            if not reusable_df.empty:
                column_health = reusable_df.groupby("Column_ID").agg(
                    Total_Injections=("Injections", "sum"), # Sums the exact number of injections logged
                    Avg_pH=("pH", "mean") # Shows the average pH run through the column
                ).reset_index()

                column_health["Status"] = column_health["Total_Injections"].apply(lambda x: "🔴 REPLACE SOON" if x > 50 else "🟢 HEALTHY")
                
                # Format Avg_pH to 1 decimal place
                column_health["Avg_pH"] = column_health["Avg_pH"].round(1)

                st.dataframe(
                    column_health.style.applymap(lambda x: "background-color: #fca5a5" if "REPLACE" in str(x) else "background-color: #bbf7d0", subset=["Status"]),
                    use_container_width=True
                )
            else:
                st.info("No reusable columns logged in this time period.")
                
            with st.expander("📂 View Raw Database Log"):
                st.dataframe(filtered_df, use_container_width=True)
