import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="課題管理システム", layout="wide")

# --- データベース初期化（永続保存用） ---
def init_db():
    conn = sqlite3.connect('assignments_v3.db', check_same_thread=False)
    c = conn.cursor()
    # 課題本体
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id TEXT PRIMARY KEY, lecture TEXT, title TEXT, due TEXT, created_by TEXT)''')
    # ユーザーごとの完了状態
    c.execute('''CREATE TABLE IF NOT EXISTS task_status 
                 (user_id TEXT, task_id TEXT, is_done INTEGER, PRIMARY KEY (user_id, task_id))''')
    conn.commit()
    return conn

db_conn = init_db()

# --- データ操作関数 ---
def load_tasks():
    df = pd.read_sql('SELECT * FROM tasks', db_conn)
    if not df.empty:
        df["due"] = pd.to_datetime(df["due"])
    return df

def get_user_statuses(user_id):
    return pd.read_sql(f"SELECT task_id, is_done FROM task_status WHERE user_id = '{user_id}'", db_conn)

def save_new_task(lec, title, due_dt, creator):
    tid = f"{int(datetime.now().timestamp())}_{creator}"
    c = db_conn.cursor()
    c.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, ?)', (tid, lec, title, due_dt.strftime('%Y-%m-%d %H:%M'), creator))
    db_conn.commit()

def update_task_detail(tid, lec, title, due_dt):
    c = db_conn.cursor()
    c.execute('UPDATE tasks SET lecture=?, title=?, due=? WHERE id=?', (lec, title, due_dt.strftime('%Y-%m-%d %H:%M'), tid))
    db_conn.commit()

def delete_task(tid):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (tid,))
    c.execute('DELETE FROM task_status WHERE task_id = ?', (tid,))
    db_conn.commit()

def toggle_status(user_id, tid, is_done):
    c = db_conn.cursor()
    c.execute('INSERT OR REPLACE INTO task_status VALUES (?, ?, ?)', (user_id, tid, 1 if is_done else 0))
    db_conn.commit()

# --- UI ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("あなたの名前（合言葉）", key="user_login")

if not user_name:
    st.info("名前を入力してログインしてください。")
    st.stop()

# 編集モード管理用のセッション
if "editing_tid" not in st.session_state:
    st.session_state.editing_id = None

# データ取得
df_tasks = load_tasks()
df_status = get_user_statuses(user_name)
my_tasks = df_tasks[(df_tasks["created_by"] == "all") | (df_tasks["created_by"] == user_name)]

# --- サイドバー：追加 ---
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
            save_new_task(lec, task, datetime.combine(d, t), "all" if add_mode == "全員に共有" else user_name)
            st.rerun()

st.title(f"📚 {user_name} さんの課題マネージャー")

# --- メインリスト ---
if my_tasks.empty:
    st.write("課題はありません。")
else:
    for lec_name in sorted(my_tasks["lecture"].unique()):
        st.subheader(f"📖 {lec_name}")
        lec_tasks = my_tasks[my_tasks["lecture"] == lec_name].sort_values("due")
        
        for _, row in lec_tasks.iterrows():
            tid = row['id']
            is_done = tid in df_status[df_status['is_done'] == 1]['task_id'].values
            
            with st.container(border=True):
                if st.session_state.editing_id == tid:
                    # --- 編集モード ---
                    with st.form(key=f"edit_f_{tid}"):
                        e_lec = st.text_input("講義名", value=row['lecture'])
                        e_title = st.text_input("内容", value=row['title'])
                        e_d = st.date_input("日付", value=row['due'].date())
                        e_t = st.time_input("時間", value=row['due'].time())
                        if st.form_submit_button("✅ 更新"):
                            update_task_detail(tid, e_lec, e_title, datetime.combine(e_d, e_t))
                            st.session_state.editing_id = None
                            st.rerun()
                        if st.form_submit_button("キャンセル"):
                            st.session_state.editing_id = None
                            st.rerun()
                else:
                    # --- 通常表示 ---
                    c1, c2, c3, c4 = st.columns([0.1, 0.5, 0.25, 0.15])
                    
                    # 個別チェック
                    checked = c1.checkbox("済", value=is_done, key=f"chk_{tid}_{user_name}")
                    if checked != is_done:
                        toggle_status(user_name, tid, checked)
                        st.rerun()
                    
                    tag = "📢" if row['created_by'] == "all" else "🔒"
                    txt = f"{tag} **{row['title']}**"
                    c2.markdown(f"~~{txt}~~ ✅" if checked else txt)
                    c3.write(f"⏰ {row['due'].strftime('%m/%d %H:%M')}")
                    
                    # 自分が作った課題のみ編集・削除
                    if row['created_by'] == user_name:
                        btn_e, btn_d = c4.columns(2)
                        if btn_e.button("📝", key=f"ed_{tid}"):
                            st.session_state.editing_id = tid
                            st.rerun()
                        if btn_d.button("🗑️", key=f"de_{tid}"):
                            delete_task(tid)
                            st.rerun()
