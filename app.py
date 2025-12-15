import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# カスタムCSSでカレンダーの視認性を向上
st.markdown("""
    <style>
    .fc-event-title { font-weight: bold !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    </style>
    """, unsafe_allow_html=True)

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('task_manager.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            lecture TEXT,
            title TEXT,
            due TEXT,
            created_by TEXT
        )
    ''')
    conn.commit()
    return conn

db_conn = init_db()

def load_data():
    df = pd.read_sql('SELECT * FROM tasks', db_conn)
    if not df.empty:
        df["due"] = pd.to_datetime(df["due"])
    return df

def save_task(lec, task, due_dt, creator):
    c = db_conn.cursor()
    task_id = f"{int(datetime.now().timestamp())}_{creator}"
    c.execute(
        'INSERT INTO tasks (id, lecture, title, due, created_by) VALUES (?, ?, ?, ?, ?)',
        (task_id, lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), creator)
    )
    db_conn.commit()

# --- ログイン ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_name")

if not user_name:
    st.info("サイドバーに合言葉を入力してください。")
    st.stop()

# データ読込
df_all = load_data()
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

# --- サイドバー：課題追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 課題の追加")
add_mode = st.sidebar.radio("共有範囲", ["自分専用", "全員に共有"])

with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due_date = st.date_input("提出日", datetime.now())
    due_time = st.time_input("提出時間", datetime.now())
    if st.form_submit_button("保存"):
        if lec and task:
            creator = "all" if add_mode == "全員に共有" else user_name
            save_task(lec, task, datetime.combine(due_date, due_time), creator)
            st.success("保存完了！")
            st.rerun()

# --- メイン画面 ---
st.title(f"📚 {user_name} さんの課題管理")

tab1, tab2 = st.tabs(["📋 リスト表示", "📅 カレンダー表示"])

with tab1:
    if my_visible_tasks.empty:
        st.write("課題はありません。")
    else:
        for lec in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    c1, c2 = st.columns([0.7, 0.3])
                    tag = "📢" if t["created_by"] == "all" else "🔒"
                    c1.write(f"{tag} **{t['title']}**")
                    c2.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    # カレンダー用イベント作成
    calendar_events = []
    for _, t in my_visible_tasks.iterrows():
        calendar_events.append({
            "title": f"[{t['lecture']}] {t['title']}",
            "start": t["due"].isoformat(),
            "backgroundColor": "#ff4b4b" if t["created_by"] == "all" else "#007bff",
            "borderColor": "#ff4b4b" if t["created_by"] == "all" else "#007bff",
        })

    # カレンダーのオプション設定（高さを指定）
    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek",
        },
        "height": 600, # ここで高さを固定するのが重要
        "selectable": True,
    }
    
    calendar(events=calendar_events, options=calendar_options)
