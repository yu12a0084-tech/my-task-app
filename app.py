import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

def get_connection():
    s = st.secrets.connections.gsheets
    return st.connection(
        "gsheets",
        type=GSheetsConnection,
        project_id=s.project_id,
        private_key_id=s.private_key_id,
        private_key=s.private_key.replace("\\n", "\n"),
        client_email=s.client_email,
        client_id=s.client_id,
        auth_uri=s.auth_uri,
        token_uri=s.token_uri,
        auth_provider_x509_cert_url=s.auth_provider_x509_cert_url,
        client_x509_cert_url=s.client_x509_cert_url
    )

conn = get_connection()
url = st.secrets.connections.gsheets.spreadsheet

def load_data():
    try:
        data = conn.read(spreadsheet=url, ttl="0s")
        cols = ["id", "lecture", "title", "due", "created_by"]
        if data is None or data.empty:
            return pd.DataFrame(columns=cols)
        for col in cols:
            if col not in data.columns:
                data[col] = None
        return data[cols]
    except:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    try:
        conn.update(spreadsheet=url, data=df)
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力", key="user_name")

if not user_name:
    st.stop()

df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

st.title(f"📚 {user_name} さんの課題")

with st.sidebar.form("add_task"):
    lec = st.text_input("講義名")
    task = st.text_input("内容")
    d = st.date_input("日付", datetime.now())
    t = st.time_input("時間", datetime.now())
    if st.form_submit_button("保存"):
        new_row = pd.DataFrame([{
            "id": str(datetime.now().timestamp()),
            "lecture": lec,
            "title": task,
            "due": datetime.combine(d, t).strftime('%Y-%m-%d %H:%M'),
            "created_by": user_name
        }])
        if save_data(pd.concat([df_all, new_row], ignore_index=True)):
            st.success("Saved")
            st.rerun()

view = df_all[df_all["created_by"] == user_name]
t1, t2 = st.tabs(["List", "Calendar"])

with t1:
    st.dataframe(view[["lecture", "title", "due"]], use_container_width=True)

with t2:
    events = [{"title": f"[{t['lecture']}] {t['title']}", "start": t["due"].isoformat()} for _, t in view.iterrows()]
    calendar(events=events)
