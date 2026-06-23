"""Google Sheets reader for the dashboard."""
import streamlit as st
import pandas as pd

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_ID = st.secrets.get("spreadsheet_id", "")
SHEET_NAME = st.secrets.get("sheet_name", "Sheet1")


@st.cache_resource(ttl=300)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        return None
    import gspread
    from google.oauth2.service_account import Credentials
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=60)
def read_all_reports() -> pd.DataFrame:
    client = get_gspread_client()
    if client is None:
        return pd.DataFrame()
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading sheet: {e}")
        return pd.DataFrame()
