import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

def get_connection():
    conf = st.secrets.connections.gsheets.to_dict()
    if "private_key" in conf:
        conf["private_key"] = conf["private_key"].replace("\\n", "\n").strip()
    if "type" in conf:
        del conf["type"]
    return st.connection("gsheets", type=GSheetsConnection, **conf)

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
        st.error(f"保存失敗: {e}")
        return False

st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_name")

if not user_name:
    st.info("サイドバーに合言葉を入力してログインしてください。")
    st.stop()

df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

st.title(f"📚 {user_name} さんの課題管理")

with st.sidebar.form("add_form", clear_on_submit=True):
    st.header("➕ 課題追加")
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    d = st.date_input("提出日", datetime.now())
    t = st.time_input("提出時間", datetime.now())
    if st.form_submit_button("保存"):
        if lec and task:
            new_row = pd.DataFrame([{
                "id": str(datetime.now().timestamp()),
                "lecture": lec,
                "title": task,
                "due": datetime.combine(d, t).strftime('%Y-%m-%d %H:%M'),
                "created_by": user_name
            }])
            if save_data(pd.concat([df_all, new_row], ignore_index=True)):
                st.success("保存完了")
                st.rerun()

view_df = df_all[df_all["created_by"] == user_name]
tab1, tab2 = st.tabs(["📋 リスト", "📅 カレンダー"])

with tab1:
    if view_df.empty:
        st.write("課題はありません。")
    else:
        st.dataframe(view_df[["lecture", "title", "due"]], use_container_width=True)

with tab2:
    events = [{"title": f"[{t['lecture']}] {t['title']}", "start": t["due"].isoformat()} for _, t in view_df.iterrows()]
    calendar(events=events)
