import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('task_v5_main.db', check_same_thread=False)
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

def update_task_detail(task_id, lec, task, due_dt):
    c = db_conn.cursor()
    c.execute('UPDATE tasks SET lecture=?, title=?, due=? WHERE id=?',
              (lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), task_id))
    db_conn.commit()

def delete_task(task_id):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    c.execute('DELETE FROM task_status WHERE task_id = ?', (task_id,))
    db_conn.commit()

# --- ログイン ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_login")

if not user_name:
    st.info("左側のサイドバーに合言葉を入力してログインしてください。")
    st.stop()

# データの読み込み
df_all = load_data()
df_status = get_status(user_name)
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

# --- サイドバー：課題追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 新規課題追加")
add_mode = st.sidebar.radio("共有範囲", ["自分専用", "全員に共有"])
with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    d = st.date_input("日付", datetime.now())
    t = st.time_input("時間", datetime.now())
    if st.form_submit_button("保存"):
        if lec and task:
            save_task(lec, task, datetime.combine(d, t), "all" if add_mode == "全員に共有" else user_name)
            st.rerun()

st.title(f"📚 {user_name} さんの課題管理")

# --- メインリスト表示 ---
if my_visible_tasks.empty:
    st.info("表示できる課題はありません。サイドバーから追加してください。")
else:
    for lec_name in sorted(my_visible_tasks["lecture"].unique()):
        st.subheader(f"📖 {lec_name}")
        lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec_name].sort_values("due")
        
        for _, row in lec_tasks.iterrows():
            tid = row['id']
            # 完了状態の取得
            is_completed = tid in df_status[df_status['is_done'] == 1]['task_id'].values
            
            # 編集モードの判定
            is_editing = st.session_state.get(f"edit_mode_{tid}", False)
            
            with st.container(border=True):
                if not is_editing:
                    # --- 通常表示モード ---
                    c1, c2, c3, c4 = st.columns([0.1, 0.5, 0.25, 0.15])
                    
                    # 1. 完了チェック
                    done = c1.checkbox("済", value=is_completed, key=f"chk_{tid}")
                    if done != is_completed:
                        update_status(user_name, tid, done)
                        st.rerun()
                    
                    # 2. 内容
                    tag = "📢" if row['created_by'] == "all" else "🔒"
                    title_text = f"**{row['title']}**"
                    if done: title_text = f"~~{title_text}~~ ✅"
                    c2.markdown(f"{tag} {title_text}")
                    
                    # 3. 期限
                    c3.write(f"⏰ {row['due'].strftime('%m/%d %H:%M')}")
                    
                    # 4. 操作（自分が作ったものだけ編集・削除可能）
                    if row['created_by'] == user_name:
                        edit_btn, del_btn = c4.columns(2)
                        if edit_btn.button("📝", key=f"btn_ed_{tid}"):
                            st.session_state[f"edit_mode_{tid}"] = True
                            st.rerun()
                        if del_btn.button("🗑️", key=f"btn_de_{tid}"):
                            delete_task(tid)
                            st.rerun()
                else:
                    # --- 編集フォームモード ---
                    st.markdown("#### 📝 課題の編集")
                    with st.form(key=f"form_ed_{tid}"):
                        new_lec = st.text_input("講義名", value=row['lecture'])
                        new_task = st.text_input("内容", value=row['title'])
                        col_d, col_t = st.columns(2)
                        new_d = col_d.date_input("日付", value=row['due'].date())
                        new_t = col_t.time_input("時間", value=row['due'].time())
                        
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("✅ 更新を保存"):
                            update_task_detail(tid, new_lec, new_task, datetime.combine(new_d, new_t))
                            st.session_state[f"edit_mode_{tid}"] = False
                            st.rerun()
                        if b2.form_submit_button("❌ キャンセル"):
                            st.session_state[f"edit_mode_{tid}"] = False
                            st.rerun()
