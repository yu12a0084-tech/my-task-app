import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('task_v3_main.db', check_same_thread=False)
    c = conn.cursor()
    # 課題本体テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            lecture TEXT,
            title TEXT,
            due TEXT,
            created_by TEXT
        )
    ''')
    # ユーザーごとの完了状態テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS task_status (
            user_id TEXT,
            task_id TEXT,
            is_done INTEGER,
            PRIMARY KEY (user_id, task_id)
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

def get_status(user_id):
    return pd.read_sql(f"SELECT task_id, is_done FROM task_status WHERE user_id = '{user_id}'", db_conn)

def update_status(user_id, task_id, is_done):
    c = db_conn.cursor()
    c.execute('INSERT OR REPLACE INTO task_status (user_id, task_id, is_done) VALUES (?, ?, ?)',
              (user_id, task_id, 1 if is_done else 0))
    db_conn.commit()

def save_task(lec, task, due_dt, creator):
    c = db_conn.cursor()
    task_id = f"{int(datetime.now().timestamp())}_{creator}"
    c.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, ?)',
              (task_id, lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), creator))
    db_conn.commit()

def delete_task(task_id):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    c.execute('DELETE FROM task_status WHERE task_id = ?', (task_id,))
    db_conn.commit()

# --- ログイン ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力", key="user_login")

if not user_name:
    st.info("サイドバーに合言葉を入力してログインしてください。")
    st.stop()

# データの読み込み
df_all = load_data()
df_status = get_status(user_name)
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

# --- サイドバー：課題追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 新規課題")
add_mode = st.sidebar.radio("共有範囲", ["自分専用", "全員に共有"])
with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("内容")
    d = st.date_input("日付")
    t = st.time_input("時間")
    if st.form_submit_button("保存"):
        if lec and task:
            save_task(lec, task, datetime.combine(d, t), "all" if add_mode == "全員に共有" else user_name)
            st.rerun()

st.title(f"📚 {user_name} さんの課題管理")

tab1, tab2 = st.tabs(["📋 リスト・完了管理", "📅 カレンダー"])

with tab1:
    if my_visible_tasks.empty:
        st.write("課題はありません。")
    else:
        # 講義ごとに表示
        for lec_name in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec_name}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec_name].sort_values("due")
                for _, row in lec_tasks.iterrows():
                    tid = row['id']
                    # 個別の完了状態を確認
                    is_completed = tid in df_status[df_status['is_done'] == 1]['task_id'].values
                    
                    col1, col2, col3, col4 = st.columns([0.1, 0.5, 0.3, 0.1])
                    
                    # チェックボックス（個別保存）
                    new_done = col1.checkbox("完了", value=is_completed, key=f"check_{tid}")
                    if new_done != is_completed:
                        update_status(user_name, tid, new_done)
                        st.rerun()
                    
                    # 表示テキスト（完了なら打ち消し線）
                    display_text = f"**{row['title']}**"
                    if new_done:
                        display_text = f"~~{display_text}~~ ✅"
                    tag = "📢" if row['created_by'] == "all" else "🔒"
                    col2.markdown(f"{tag} {display_text}")
                    
                    col3.write(f"⏰ {row['due'].strftime('%m/%d %H:%M')}")
                    
                    # 自分が
