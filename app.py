
import streamlit as st
import pandas as pd
import glob
import os
import seaborn as sns
import matplotlib.pyplot as plt

# --- Configuration ---
st.set_page_config(page_title="Aadhar Data Dashboard", layout="wide")

# --- Data Loading (Cached) ---
@st.cache_data
def load_data():
    base_dir = r"l:\Adhar_data"
    enrolment_path = os.path.join(base_dir, "api_data_aadhar_enrolment", "api_data_aadhar_enrolment")
    demographic_path = os.path.join(base_dir, "api_data_aadhar_demographic", "api_data_aadhar_demographic")
    biometric_path = os.path.join(base_dir, "api_data_aadhar_biometric", "api_data_aadhar_biometric")

    def read_folder(path):
        files = glob.glob(os.path.join(path, "*.csv"))
        df_list = []
        for file in files:
            try:
                df_list.append(pd.read_csv(file))
            except:
                pass
        return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

    df_enrolment = read_folder(enrolment_path)
    df_demographic = read_folder(demographic_path)
    df_biometric = read_folder(biometric_path)

    # Generic Cleaning
    for df in [df_enrolment, df_demographic, df_biometric]:
        if not df.empty:
            df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')

    return df_enrolment, df_demographic, df_biometric

df_enrolment, df_demographic, df_biometric = load_data()

# --- Sidebar ---
st.sidebar.title("Navigation")
options = st.sidebar.radio("Go to", ["Home", "Enrolment Analysis", "Demographics", "Biometrics"])

# --- Pages ---
if options == "Home":
    st.title("Aadhar Data Analysis Dashboard")
    st.write("Welcome to the dashboard. Use the sidebar to navigate.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Enrolments", len(df_enrolment))
    col2.metric("Total Demographics", len(df_demographic))
    col3.metric("Total Biometrics", len(df_biometric))

elif options == "Enrolment Analysis":
    st.header("Enrolment Trends")
    if not df_enrolment.empty:
        st.dataframe(df_enrolment.head())
        # Add plotting logic here if date columns exist
    else:
        st.warning("No Enrolment Data Found")

elif options == "Demographics":
    st.header("Demographic Insights")
    if not df_demographic.empty:
        # Age Distribution
        age_col = next((col for col in df_demographic.columns if 'age' in col), None)
        if age_col:
            st.subheader("Age Distribution")
            fig, ax = plt.subplots()
            sns.histplot(df_demographic[age_col], kde=True, ax=ax)
            st.pyplot(fig)
    else:
        st.warning("No Demographic Data Found")

elif options == "Biometrics":
    st.header("Biometric Analysis")
    if not df_biometric.empty:
        st.dataframe(df_biometric.head())
    else:
        st.warning("No Biometric Data Found")

