import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- 秘密鍵の自動修復機能付き接続 ---
def get_safe_connection():
    # 1. Secretsからデータを取得
    conf = st.secrets.connections.gsheets.to_dict()
    
    # 2. 秘密鍵内の「文字としての\\n」を「本物の改行」へ置換
    # これにより binascii.Error (Base64失敗) を防ぎます
    if "private_key" in conf:
        conf["private_key"] = conf["private_key"].replace("\\n", "\n")
    
    # 3. typeの重複によるTypeErrorを防ぐ
    if "type" in conf:
        del conf["type"]
        
    return st.connection("gsheets", type=GSheetsConnection, **conf)

# 接続実行
conn = get_safe_connection()

# --- データ操作関数 ---
def load_data():
    try:
        data = conn.read(ttl="0s")
        return data if data is not None else pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])
    except:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    conn.update(data=df)

# --- ログイン・UI ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉（例：ゆうすけ29）")

if not user_name:
    st.info("サイドバーから合言葉を入力してください。")
    st.stop()

# データの読み込みと日付変換
df_all = load_data()
if not df_all.empty and "due" in df_all.columns:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

st.title(f"📚 {user_name} さんの課題管理")

# 課題追加
with st.sidebar.form("add_task"):
    lec = st.text_input("講義名")
    task = st.text_input("内容")
    due = st.datetime_input("期限", datetime.now())
    if st.form_submit_button("保存"):
        new_data = pd.DataFrame([{"id": str(datetime.now().timestamp()), "lecture": lec, "title": task, "due": due.strftime('%Y-%m-%d %H:%M'), "created_by": user_name}])
        save_data(pd.concat([df_all, new_data], ignore_index=True))
        st.success("保存しました！")
        st.rerun()

# 表示
tab1, tab2 = st.tabs(["📋 リスト", "📅 カレンダー"])
my_tasks = df_all[df_all["created_by"] == user_name]

with tab1:
    if my_tasks.empty:
        st.write("課題はありません。")
    else:
        st.dataframe(my_tasks[["lecture", "title", "due"]])

with tab2:
    events = [{"title": f"[{t['lecture']}] {t['title']}", "start": t["due"].isoformat()} for _, t in my_tasks.iterrows()]
    calendar(events=events, options={"initialView": "dayGridMonth"})
