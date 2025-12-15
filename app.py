import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

def get_connection():
    # Secretsを辞書として取得
    s = st.secrets.connections.gsheets
    conf = {
        "project_id": s.project_id,
        "private_key_id": s.private_key_id,
        "private_key": s.private_key.replace("\\n", "\n"), # 改行を修復
        "client_email": s.client_email,
        "client_id": s.client_id,
        "auth_uri": s.auth_uri,
        "token_uri": s.token_uri,
        "auth_provider_x509_cert_url": s.auth_provider_x509_cert_url,
        "client_x509_cert_url": s.client_x509_cert_url
    }
    return st.connection("gsheets", type=GSheetsConnection, **conf)

conn = get_connection()
spreadsheet_url = st.secrets.connections.gsheets.spreadsheet

def load_data():
    try:
        return conn.read(spreadsheet=spreadsheet_url, ttl="0s")
    except:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    try:
        conn.update(spreadsheet=spreadsheet_url, data=df)
        return True
    except Exception as e:
        st.error(f"書き込み失敗: {e}")
        return False

# --- UI ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力")
if not user_name:
    st.stop()

df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

# 課題追加
with st.sidebar.form("add"):
    lec = st.text_input("講義名")
    task = st.text_input("内容")
    d = st.date_input("日", datetime.now())
    t = st.time_input("時", datetime.now())
    if st.form_submit_button("保存"):
        new = pd.DataFrame([{"id": str(datetime.now().timestamp()), "lecture": lec, "title": task, "due": datetime.combine(d, t).strftime('%Y-%m-%d %H:%M'), "created_by": user_name}])
        if save_data(pd.concat([df_all, new], ignore_index=True)):
            st.success("完了！")
            st.rerun()

# 表示
view = df_all[df_all["created_by"] == user_name]
st.write(f"### {user_name} さんの課題一覧")
st.table(view[["lecture", "title", "due"]] if not view.empty else pd.DataFrame(columns=["lecture", "title", "due"]))
