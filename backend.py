from fastapi import FastAPI, HTTPException
import pandas as pd
import glob
import os
from typing import List, Dict, Any

app = FastAPI(title="Aadhar Data Advanced API")

# --- Data Loading Utility ---
base_dir = r"l:\Adhar_data"
enrolment_path = os.path.join(base_dir, "api_data_aadhar_enrolment", "api_data_aadhar_enrolment")
demographic_path = os.path.join(base_dir, "api_data_aadhar_demographic", "api_data_aadhar_demographic")
biometric_path = os.path.join(base_dir, "api_data_aadhar_biometric", "api_data_aadhar_biometric")

def load_df_from_folder(path):
    # Support both direct and nested structure just in case
    files = glob.glob(os.path.join(path, "*.csv"))
    if not files:
        files = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
        
    print(f"Scanning {path}, found {len(files)} files.")
    df_list = []
    for file in files:
        try:
            df = pd.read_csv(file)
            # Basic cleaning
            df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')
            
            # Convert date if exists
            date_col = next((col for col in df.columns if 'date' in col), None)
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y', errors='coerce')
                
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            pass
    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

# Load data on startup
print("Loading data...")
df_enrolment = load_df_from_folder(enrolment_path)
df_demographic = load_df_from_folder(demographic_path)
df_biometric = load_df_from_folder(biometric_path)

# Fill NaN for numeric columns
for df in [df_enrolment, df_demographic, df_biometric]:
    if not df.empty:
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)

print("Data loaded.")

@app.get("/")
def read_root():
    return {"message": "Aadhar Data Advanced Analytics API"}

@app.get("/stats")
def get_stats():
    return {
        "enrolment": {
            "total_records": int(len(df_enrolment)),
            "age_0_5_total": int(df_enrolment['age_0_5'].sum()) if not df_enrolment.empty else 0,
            "age_5_17_total": int(df_enrolment['age_5_17'].sum()) if not df_enrolment.empty else 0,
            "age_18_greater_total": int(df_enrolment['age_18_greater'].sum()) if not df_enrolment.empty else 0,
        },
        "demographic": {
            "total_records": int(len(df_demographic)),
            "demo_age_5_17_total": int(df_demographic['demo_age_5_17'].sum()) if not df_demographic.empty else 0,
        },
        "biometric": {
            "total_records": int(len(df_biometric)),
            "bio_age_5_17_total": int(df_biometric['bio_age_5_17'].sum()) if not df_biometric.empty else 0,
        }
    }

@app.get("/analytics/state-summary")
def get_state_summary():
    """Returns aggregated metrics per state for all datasets."""
    summary = {}
    
    if not df_enrolment.empty:
        enrol_grp = df_enrolment.groupby('state')[['age_0_5', 'age_5_17', 'age_18_greater']].sum().reset_index()
        enrol_grp['total_enrolment'] = enrol_grp['age_0_5'] + enrol_grp['age_5_17'] + enrol_grp['age_18_greater']
        summary['enrolment'] = enrol_grp.to_dict(orient='records')

    if not df_biometric.empty:
        bio_grp = df_biometric.groupby('state')[['bio_age_5_17', 'bio_age_17_']].sum().reset_index()
        bio_grp['total_biometric'] = bio_grp['bio_age_5_17'] + bio_grp['bio_age_17_']
        summary['biometric'] = bio_grp.to_dict(orient='records')
        
    return summary

@app.get("/analytics/trends")
def get_trends():
    """Returns time-series data aggregated by date."""
    if df_enrolment.empty:
        return []
        
    # Group by date
    trend = df_enrolment.groupby('date')[['age_0_5', 'age_5_17', 'age_18_greater']].sum().reset_index()
    # Convert date to string for JSON serialization
    trend['date'] = trend['date'].dt.strftime('%Y-%m-%d')
    return trend.to_dict(orient='records')

@app.get("/analytics/district-rankings")
def get_district_rankings(state: str = None):
    """Returns top performing districts."""
    if df_enrolment.empty:
        return []
    
    df = df_enrolment.copy()
    if state:
        df = df[df['state'] == state]
        
    df['total'] = df['age_0_5'] + df['age_5_17'] + df['age_18_greater']
    ranked = df.groupby(['state', 'district'])['total'].sum().reset_index().sort_values('total', ascending=False).head(20)
    return ranked.to_dict(orient='records')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
