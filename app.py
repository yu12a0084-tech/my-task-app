import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('task_manager_v6.db', check_same_thread=False)
    c = conn.cursor()
    # 課題テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id TEXT PRIMARY KEY, lecture TEXT, title TEXT, due TEXT, created_by TEXT)''')
    # 個別完了状態
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

def update_task(tid, lec, task, due_dt):
    c = db_conn.cursor()
    c.execute('UPDATE tasks SET lecture=?, title=?, due=? WHERE id=?', 
              (lec, task, due_dt.strftime('%Y-%m-%d %H:%M'), tid))
    db_conn.commit()

def delete_task(tid):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (tid,))
    c.execute('DELETE FROM task_status WHERE task_id = ?', (tid,))
    db_conn.commit()

# --- ログイン設定 ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_login")

if not user_name:
    st.info("サイドバーに合言葉を入力してログインしてください。")
    st.stop()

# 編集モード管理
if "edit_target_id" not in st.session_state:
    st.session_state.edit_target_id = None

# データ取得
df_all = load_data()
df_status = pd.read_sql(f"SELECT task_id, is_done FROM task_status WHERE user_id = '{user_name}'", db_conn)
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

# --- サイドバー：新規追加 ---
with st.sidebar.form("add_form", clear_on_submit=True):
    st.header("➕ 新規課題追加")
    add_mode = st.radio("共有範囲", ["自分専用", "全員に共有"])
    lec_in = st.text_input("講義名")
    task_in = st.text_input("内容")
    d_in = st.date_input("日付")
    t_in = st.time_input("時間")
    if st.form_submit_button("保存"):
        if lec_in and task_in:
            tid = f"{int(datetime.now().timestamp())}_{user_name}"
            creator = "all" if add_mode == "全員に共有" else user_name
            c = db_conn.cursor()
            c.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, ?)', (tid, lec_in, task_in, datetime.combine(d_in, t_in).strftime('%Y-%m-%d %H:%M'), creator))
            db_conn.commit()
            st.rerun()

st.title(f"📚 {user_name} さんの課題管理")

# --- メイン画面：タブ分け ---
tab1, tab2 = st.tabs(["📋 課題リスト", "⚙️ 課題の編集・削除"])

with tab1:
    if my_visible_tasks.empty:
        st.info("表示できる課題はありません。")
    else:
        for lec_name in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec_name}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec_name].sort_values("due")
                for _, row in lec_tasks.iterrows():
                    tid = row['id']
                    is_completed = tid in df_status[df_status['is_done'] == 1]['task_id'].values
                    
                    c1, c2, c3 = st.columns([0.1, 0.6, 0.3])
                    # 個別完了チェック
                    done = c1.checkbox("済", value=is_completed, key=f"list_chk_{tid}")
                    if done != is_completed:
                        c = db_conn.cursor()
                        c.execute('INSERT OR REPLACE INTO task_status VALUES (?, ?, ?)', (user_name, tid, 1 if done else 0))
                        db_conn.commit()
                        st.rerun()
                    
                    tag = "📢" if row['created_by'] == "all" else "🔒"
                    title_display = f"**{row['title']}**"
                    if done: title_display = f"~~{title_display}~~ ✅"
                    c2.markdown(f"{tag} {title_display}")
                    c3.write(f"⏰ {row['due'].strftime('%m/%d %H:%M')}")

with tab2:
    st.subheader("🛠 課題の管理")
    # 自分が作成した課題のみ抽出
    my_own_tasks = df_all[df_all["created_by"] == user_name]
    
    if my_own_tasks.empty:
        st.write("あなたが作成した編集可能な課題はありません。")
    else:
        # 編集する課題を選択するプルダウン
        task_options = {f"[{t['lecture']}] {t['title']}": t['id'] for _, t in my_own_tasks.iterrows()}
        selected_task_label = st.selectbox("編集または削除する課題を選択してください:", ["-- 選択してください --"] + list(task_options.keys()))
        
        if selected_task_label != "-- 選択してください --":
            target_id = task_options[selected_task_label]
            target_row = my_own_tasks[my_own_tasks["id"] == target_id].iloc[0]
            
            # --- 編集フォーム ---
            with st.form("edit_manage_form"):
                st.write(f"### 📝 内容の変更")
                edit_lec = st.text_input("講義名", value=target_row['lecture'])
                edit_title = st.text_input("課題内容", value=target_row['title'])
                col_d, col_t = st.columns(2)
                edit_d = col_d.date_input("日付", value=target_row['due'].date())
                edit_t = col_t.time_input("時間", value=target_row['due'].time())
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("✅ 変更を保存"):
                    update_task(target_id, edit_lec, edit_title, datetime.combine(edit_d, edit_t))
                    st.success("更新しました！")
                    st.rerun()
                
                if b2.form_submit_button("🗑️ この課題を削除"):
                    delete_task(target_id)
                    st.warning("削除しました。")
                    st.rerun()
