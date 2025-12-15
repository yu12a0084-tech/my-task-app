import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 (SQLite) ---
def init_db():
    conn = sqlite3.connect('tasks_v2.db', check_same_thread=False)
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
    return pd.read_sql('SELECT * FROM tasks', db_conn)

def save_task(lec, task, due_dt, creator):
    c = db_conn.cursor()
    task_id = f"{int(datetime.now().timestamp())}_{creator}"
    c.execute(
        'INSERT INTO tasks (id, lecture, title, due, created_by) VALUES (?, ?, ?, ?, ?)',
        (task_id, lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), creator)
    )
    db_conn.commit()

def delete_task(task_id):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db_conn.commit()

# --- ログイン設定 ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_name")

if not user_name:
    st.warning("左側のサイドバーに合言葉を入力してログインしてください。")
    st.stop()

st.title(f"📚 {user_name} さんの課題マネージャー")

# --- 課題の追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 課題の追加")
add_mode = st.sidebar.radio("追加の種類:", ["自分専用", "全員に共有"])

with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due_date = st.date_input("提出日", datetime.now())
    due_time = st.time_input("提出時間", datetime.now())
    
    if st.form_submit_button("保存"):
        if lec and task:
            creator = "all" if add_mode == "全員に共有" else user_name
            due_dt = datetime.combine(due_date, due_time)
            save_task(lec, task, due_dt, creator)
            st.success("保存完了！")
            st.rerun()

# データの取得と整形
df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"])

# 閲覧可能な課題（自分用 + 全員用）
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

tab1, tab2, tab3 = st.tabs(["📋 講義別リスト", "📅 カレンダー", "⚙️ 管理・削除"])

with tab1:
    if my_visible_tasks.empty:
        st.info("表示できる課題がありません。")
    else:
        for lec in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    tag = "📢[共有] " if t["created_by"] == "all" else "🔒[個人] "
                    # チェックを入れたら削除ボタンを表示する簡易的な仕組み
                    if col1.checkbox("", key=f"check_{t['id']}"):
                        if st.button("削除", key=f"del_{t['id']}"):
                            delete_task(t['id'])
                            st.rerun()
                    col2.markdown(f"{tag}{t['title']}")
                    col3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    calendar_events = [
        {
            "id": str(t["id"]),
            "title": f"[{t['lecture']}] {t['title']}",
            "start": t["due"].isoformat(),
            "color": "#ff4b4b" if t["created_by"] == "all" else "#007bff"
        }
        for _, t in my_visible_tasks.iterrows()
    ]
    calendar(events=calendar_events, options={"initialView": "dayGridMonth"})

with tab3:
    st.subheader("全データ一覧（デバッグ・一括確認用）")
    st.dataframe(df_all, use_container_width=True)
