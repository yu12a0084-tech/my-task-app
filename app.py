import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 ---
def init_db():
    # データベース名を新しくしてクリーンな状態で開始（必要に応じて既存名に戻してください）
    conn = sqlite3.connect('task_manager_v8.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id TEXT PRIMARY KEY, lecture TEXT, title TEXT, due TEXT, created_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS task_status 
                 (user_id TEXT, task_id TEXT, is_done INTEGER, PRIMARY KEY (user_id, task_id))''')
    conn.commit()
    return conn

db_conn = init_db()

# --- ログイン ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("あなたの名前（合言葉）を入力", key="user_login")

if not user_name:
    st.info("サイドバーに名前を入力してログインしてください。")
    st.stop()

# --- データ操作関数 ---
def load_data():
    df = pd.read_sql('SELECT * FROM tasks', db_conn)
    if not df.empty:
        df["due"] = pd.to_datetime(df["due"])
    return df

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
            # 作成者を記録
            creator = "all" if add_mode == "全員に共有" else user_name
            c = db_conn.cursor()
            c.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, ?)', 
                      (tid, lec_in, task_in, datetime.combine(d_in, t_in).strftime('%Y-%m-%d %H:%M'), creator))
            db_conn.commit() # 確実に保存
            st.rerun()

st.title(f"📚 {user_name} さんの課題管理")

# 常に最新データを読み込み
df_all = load_data()
df_status = pd.read_sql(f"SELECT task_id, is_done FROM task_status WHERE user_id = '{user_name}'", db_conn)
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

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
    # 編集可能なリスト：共有課題("all")も含めてすべて表示
    editable_tasks = df_all[(df_all["created_by"] == user_name) | (df_all["created_by"] == "all")]
    
    if editable_tasks.empty:
        st.warning("編集・削除できる課題がありません。")
    else:
        # プルダウンの選択肢を作成
        task_options = {f"[{t['lecture']}] {t['title']} ({'📢共有' if t['created_by']=='all' else '🔒個人'})": t['id'] for _, t in editable_tasks.iterrows()}
        selected_label = st.selectbox("対象の課題を選択してください:", ["-- 選択してください --"] + list(task_options.keys()))
        
        if selected_label != "-- 選択してください --":
            target_id = task_options[selected_label]
            target_row = editable_tasks[editable_tasks["id"] == target_id].iloc[0]
            
            # 編集・削除用フォーム
            with st.form("edit_delete_form"):
                st.markdown(f"**選択中の課題:** `{selected_label}`")
                edit_lec = st.text_input("講義名", value=target_row['lecture'])
                edit_title = st.text_input("内容", value=target_row['title'])
                c_d, c_t = st.columns(2)
                edit_d = c_d.date_input("日付", value=target_row['due'].date())
                edit_t = c_t.time_input("時間", value=target_row['due'].time())
                
                btn_col1, btn_col2 = st.columns(2)
                
                # 更新ボタン
                if btn_col1.form_submit_button("✅ 変更内容を保存"):
                    c = db_conn.cursor()
                    c.execute('UPDATE tasks SET lecture=?, title=?, due=? WHERE id=?', 
                              (edit_lec, edit_title, datetime.combine(edit_d, edit_t).strftime('%Y-%m-%d %H:%M'), target_id))
                    db_conn.commit()
                    st.success("課題を更新しました！")
                    st.rerun()
                
                # 削除ボタン（ここを修正）
                if btn_col2.form_submit_button("🗑️ この課題を完全に削除"):
                    c = db_conn.cursor()
                    # 課題本体を削除
                    c.execute('DELETE FROM tasks WHERE id = ?', (target_id,))
                    # 関連する完了ステータスも削除
                    c.execute('DELETE FROM task_status WHERE task_id = ?', (target_id,))
                    db_conn.commit() # 確実に削除を反映
                    st.warning("課題を削除しました。")
                    st.rerun()
