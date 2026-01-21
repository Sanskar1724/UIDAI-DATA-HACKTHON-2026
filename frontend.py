import streamlit as st
import pandas as pd
import glob
import os
import requests
import plotly.express as px
import plotly.graph_objects as go

# --- Configuration ---
st.set_page_config(
    page_title="Aadhar Analytics Pro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for "Creative" UI ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        text-align: center;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# --- Constants & Data Loading ---
API_URL = "http://127.0.0.1:8000"
# For simplicity in this demo, we can perform direct loading if API fails or for speed.
# However, to be robust, let's load logic mirrored from backend for standalone capability.

@st.cache_data
def load_data_direct():
    base_dir = r"l:\Adhar_data"
    
    # Helper to find files
    def get_df(folder_name):
        path = os.path.join(base_dir, folder_name, folder_name)
        files = glob.glob(os.path.join(path, "*.csv"))
        if not files:
            files = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
            
        df_list = []
        for file in files:
            try:
                df = pd.read_csv(file)
                df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')
                # Date conversion
                date_col = next((col for col in df.columns if 'date' in col), None)
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y', errors='coerce')
                df_list.append(df)
            except: pass
        
        df_final = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
        # Fill NaNs
        if not df_final.empty:
             num_cols = df_final.select_dtypes(include=['number']).columns
             df_final[num_cols] = df_final[num_cols].fillna(0)
        return df_final

    return (
        get_df("api_data_aadhar_enrolment"), 
        get_df("api_data_aadhar_demographic"), 
        get_df("api_data_aadhar_biometric")
    )

df_enrolment, df_demographic, df_biometric = load_data_direct()

# --- Computed Fields for Analysis ---
if not df_enrolment.empty:
    df_enrolment['total_enrolment'] = df_enrolment['age_0_5'] + df_enrolment['age_5_17'] + df_enrolment['age_18_greater']

if not df_biometric.empty:
    df_biometric['total_biometric'] = df_biometric['bio_age_5_17'] + df_biometric['bio_age_17_']


# --- Sidebar Navigation ---
st.sidebar.title("📊 Aadhar Analytics")
page = st.sidebar.radio("Navigate", ["Executive Overview", "Geographic Analysis", "Demographic Insights", "Biometric Performance"])

# --- Page: Executive Overview ---
if page == "Executive Overview":
    st.title("🇮🇳 Aadhar Executive Dashboard")
    st.write("High-level metrics and system status.")
    
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    
    total_enr = df_enrolment['total_enrolment'].sum() if not df_enrolment.empty else 0
    total_bio = df_biometric['total_biometric'].sum() if not df_biometric.empty else 0
    total_demo = len(df_demographic)
    
    with c1: st.metric("Unique Enrolments", f"{total_enr:,.0f}", delta="Total")
    with c2: st.metric("Biometric Captures", f"{total_bio:,.0f}", delta=f"{(total_bio/total_enr*100 if total_enr else 0):.1f}% Coverage")
    with c3: st.metric("Demographic Records", f"{total_demo:,.0f}")
    with c4: st.metric("States Covered", df_enrolment['state'].nunique() if not df_enrolment.empty else 0)

    # Trend Chart
    st.markdown("### 📈 Enrolment Trends")
    if not df_enrolment.empty:
        trend = df_enrolment.groupby('date')[['age_0_5', 'age_5_17', 'age_18_greater']].sum().reset_index()
        fig = px.area(trend, x='date', y=['age_0_5', 'age_5_17', 'age_18_greater'], 
                      title="Enrolment Trend by Age Group", labels={'value': 'Count', 'variable': 'Age Group'})
        st.plotly_chart(fig, use_container_width=True)

# --- Page: Geographic Analysis ---
elif page == "Geographic Analysis":
    st.title("🗺️ Geographic Deep Dive")
    
    if not df_enrolment.empty:
        # State aggregate
        state_agg = df_enrolment.groupby('state')['total_enrolment'].sum().reset_index().sort_values('total_enrolment', ascending=False)
        
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("State-wise Enrolment Volume")
            fig = px.bar(state_agg, x='state', y='total_enrolment', color='total_enrolment', 
                         color_continuous_scale='Viridis', title="Enrolments per State")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Leaderboard (Top 10)")
            st.dataframe(state_agg.head(10), hide_index=True)
            
        # Drill Down
        st.divider()
        st.subheader("🔍 District Drill-down")
        selected_state = st.selectbox("Select State for Breakdown", state_agg['state'].unique())
        
        district_data = df_enrolment[df_enrolment['state'] == selected_state]
        district_agg = district_data.groupby('district')['total_enrolment'].sum().reset_index()
        
        fig2 = px.treemap(district_agg, path=['district'], values='total_enrolment', 
                          title=f"District Distribution in {selected_state}", color='total_enrolment')
        st.plotly_chart(fig2, use_container_width=True)

# --- Page: Demographic Insights ---
elif page == "Demographic Insights":
    st.title("👥 Demographic & Cohort Analysis")
    
    if not df_enrolment.empty:
        st.markdown("### Age Group Ratios")
        
        # Calculate Totals
        totals = df_enrolment[['age_0_5', 'age_5_17', 'age_18_greater']].sum().reset_index()
        totals.columns = ['Age Group', 'Count']
        
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(totals, values='Count', names='Age Group', hole=0.4, title="Overall Age Distribution")
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.write("### Insight")
            st.info("""
            **Age 0-5 (Bal Aadhar):** Critical for early ID assignment.
            **Age 5-17:** School-going age, critical for biometric updates (Mandatory Biometric Update).
            **Age 18+:** Adult population.
            """)
            
        # Scatter Plot - District Comparison
        st.markdown("### District Cluster Analysis")
        # Aggregating by district
        dist_scatter = df_enrolment.groupby(['state', 'district'])[['age_0_5', 'age_18_greater']].sum().reset_index()
        fig_scatter = px.scatter(dist_scatter, x='age_0_5', y='age_18_greater', color='state', 
                                 hover_data=['district'], title="Infant vs Adult Enrolments per District",
                                 size_max=60)
        st.plotly_chart(fig_scatter, use_container_width=True)

# --- Page: Biometric Performance ---
elif page == "Biometric Performance":
    st.title("🧬 Biometric Efficiency")
    
    if not df_biometric.empty and not df_enrolment.empty:
        # Merge State Aggregates
        bio_agg = df_biometric.groupby('state')['total_biometric'].sum().reset_index()
        enr_agg = df_enrolment.groupby('state')['total_enrolment'].sum().reset_index()
        
        merged = pd.merge(enr_agg, bio_agg, on='state', how='inner')
        merged['pending_biometrics'] = merged['total_enrolment'] - merged['total_biometric']
        merged['coverage_pct'] = (merged['total_biometric'] / merged['total_enrolment']) * 100
        
        st.markdown("### Enrolment vs Biometric Capture Gap")
        
        fig = go.Figure(data=[
            go.Bar(name='Biometrics Captured', x=merged['state'], y=merged['total_biometric']),
            go.Bar(name='Gap (Potential Pending)', x=merged['state'], y=merged['pending_biometrics'])
        ])
        fig.update_layout(barmode='stack', title="Biometric Saturation by State")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### Correlation Matrix")
        st.write("Correlating Demographic variables with Biometric counts.")
        corr = df_enrolment.groupby('state')[['age_5_17', 'age_18_greater']].sum().merge(
               df_biometric.groupby('state')[['bio_age_5_17', 'bio_age_17_']].sum(), on='state').corr()
        
        fig_hm = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', title="Correlation Heatmap")
        st.plotly_chart(fig_hm, use_container_width=True)
