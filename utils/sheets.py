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


def _clean_headers(raw_header: list[str]) -> list[str]:
    """Make a safe, unique header list.

    gspread's get_all_records() raises if the sheet's header row has blank or
    duplicate cells (e.g. trailing empty columns). We repair it instead:
    - blank cells become 'column_N'
    - duplicates get a numeric suffix ('_2', '_3', ...)
    """
    seen: dict[str, int] = {}
    out: list[str] = []
    for i, h in enumerate(raw_header):
        name = str(h).strip() if h is not None else ""
        if not name:
            name = f"column_{i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        out.append(name)
    return out


@st.cache_data(ttl=60)
def read_all_reports() -> pd.DataFrame:
    client = get_gspread_client()
    if client is None:
        return pd.DataFrame()
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        # get_all_values tolerates messy headers; we build the frame ourselves.
        values = ws.get_all_values()
        if len(values) < 2:
            return pd.DataFrame()
        header = _clean_headers(values[0])
        rows = values[1:]
        # Pad/trim each row to the header width so ragged rows don't break DataFrame.
        width = len(header)
        norm = [(r + [""] * width)[:width] for r in rows]
        df = pd.DataFrame(norm, columns=header)
        # Drop fully-empty synthetic columns (trailing blank sheet columns).
        drop = [c for c in df.columns
                if c.startswith("column_") and (df[c] == "").all()]
        if drop:
            df = df.drop(columns=drop)
        # Drop fully-blank rows.
        df = df.loc[~(df == "").all(axis=1)].reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error reading sheet: {e}")
        return pd.DataFrame()
