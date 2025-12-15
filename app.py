import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('task_manager_final.db', check_same_thread=False)
    c = conn.cursor()
    # 課題テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id TEXT PRIMARY KEY, lecture TEXT, title TEXT, due TEXT, created_by TEXT)''')
    # ユーザーごとの完了状態
    c.execute('''CREATE TABLE IF NOT EXISTS task_status 
                 (user_id TEXT, task_id TEXT, is_done INTEGER, PRIMARY KEY (user_id, task_id))''')
    conn.commit()
    return conn

db_conn = init_db()

# --- データ操作 ---
def load_data():
    df = pd.read_sql('SELECT * FROM tasks', db_conn)
    if not df.empty:
        df["due"] = pd.to_datetime(df["due"])
    return df

def save_task(lec, task, due_dt, creator):
    tid = f"{int(datetime.now().timestamp())}_{creator}"
    c = db_conn.cursor()
    c.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, ?)', 
              (tid, lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), creator))
    db_conn.commit()

def update_task_detail(tid, lec, task, due_dt):
    c = db_conn.cursor()
    c.execute('UPDATE tasks SET lecture=?, title=?, due=? WHERE id=?', 
              (lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), tid))
    db_conn.commit()

def delete_task(tid):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (tid,))
    c.execute('DELETE FROM task_status WHERE task_id = ?', (tid,))
    db_conn.commit()

def toggle_status(user_id, tid, is_done):
    c = db_conn.cursor()
    c.execute('INSERT OR REPLACE INTO task_status VALUES (?, ?, ?)', 
              (user_id, tid, 1 if is_done else 0))
    db_conn.commit()

# --- UI ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_login")

if not user_name:
    st.info("サイドバーに合言葉を入力してログインしてください。")
    st.stop()

# 編集状態の管理
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

# データ読込
df_all = load_data()
df_status = pd.read_sql(f"SELECT task_id, is_done FROM task_status WHERE user_id = '{user_name}'", db_conn)
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

# --- サイドバー：新規追加 ---
with st.sidebar.form("add_form", clear_on_submit=True):
    st.header("➕ 新規課題追加")
    add_mode = st.radio("共有範囲", ["自分専用", "全員に共有"])
    lec_in = st.text_input("講義名")
    task_in = st.text_input("内容")
    d_in = st.date_input("日付", datetime.now())
    t_in = st.time_input("時間", datetime.now())
    if st.form_submit_button("保存"):
        if lec_in and task_in:
            save_task(lec_in, task_in, datetime.combine(d_in, t_in), "all" if add_mode == "全員に共有" else user_name)
            st.rerun()

st.title(f"📚 {user_name} さんの課題管理")

# --- メインリスト ---
if my_visible_tasks.empty:
    st.info("表示できる課題はありません。")
else:
    for lec_name in sorted(my_visible_tasks["lecture"].unique()):
        st.subheader(f"📖 {lec_name}")
        lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec_name].sort_values("due")
        
        for _, row in lec_tasks.iterrows():
            tid = row['id']
            is_completed = tid in df_status[df_status['is_done'] == 1]['task_id'].values
            
            with st.container(border=True):
                # 編集モードかどうか
                if st.session_state.editing_id == tid:
                    with st.form(key=f"edit_form_{tid}"):
                        st.write("📝 課題の編集")
                        new_lec = st.text_input("講義名", value=row['lecture'])
                        new_task = st.text_input("内容", value=row['title'])
                        c_d, c_t = st.columns(2)
                        new_d = c_d.date_input("日付", value=row['due'].date())
                        new_t = c_t.time_input("時間", value=row['due'].time())
                        
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("✅ 保存"):
                            update_task_detail(tid, new_lec, new_task, datetime.combine(new_d, new_t))
                            st.session_state.editing_id = None
                            st.rerun()
                        if b2.form_submit_button("キャンセル"):
                            st.session_state.editing_id = None
                            st.rerun()
                else:
                    # 通常表示
                    col1, col2, col3, col4 = st.columns([0.1, 0.5, 0.25, 0.15])
                    
                    # チェック保存
                    done = col1.checkbox("済", value=is_completed, key=f"chk_{tid}")
                    if done != is_completed:
                        toggle_status(user_name, tid, done)
                        st.rerun()
                    
                    tag = "📢" if row['created_by'] == "all" else "🔒"
                    title_display = f"**{row['title']}**"
                    if done: title_display = f"~~{title_display}~~ ✅"
                    col2.markdown(f"{tag} {title_display}")
                    
                    col3.write(f"⏰ {row['due'].strftime('%m/%d %H:%M')}")
                    
                    # 自分が作成した課題のみ操作可能
                    if row['created_by'] == user_name:
                        ed_btn, de_btn = col4.columns(2)
                        if ed_btn.button("📝", key=f"ed_{tid}"):
                            st.session_state.editing_id = tid
                            st.rerun()
                        if de_btn.button("🗑️", key=f"de_{tid}"):
                            delete_task(tid)
                            st.rerun()
