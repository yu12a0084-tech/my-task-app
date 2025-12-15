import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- データベース設定 ---
def init_db():
    # サーバー内にファイルを生成して保存
    conn = sqlite3.connect('tasks_permanent.db', check_same_thread=False)
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

def delete_task(task_id):
    c = db_conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db_conn.commit()

# --- UI設定 ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_name")

if not user_name:
    st.warning("左側のサイドバーに合言葉を入力してログインしてください。")
    st.stop()

# データの読み込み
df_all = load_data()
# 自分の課題 + 全員共有の課題を抽出
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

st.title(f"📚 {user_name} さんの課題マネージャー")

# --- 課題の追加フォーム ---
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
            st.success("データベースに保存完了！")
            st.rerun()

# --- メインコンテンツ：タブ分け ---
tab1, tab2, tab3 = st.tabs(["📋 講義別リスト", "📅 カレンダー", "⚙️ 管理・削除"])

with tab1:
    if my_visible_tasks.empty:
        st.info("表示できる課題がありません。")
    else:
        for lec in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    c1, c2, c3 = st.columns([0.1, 0.6, 0.3])
                    tag = "📢" if t["created_by"] == "all" else "🔒"
                    c1.write(tag)
                    c2.markdown(f"**{t['title']}**")
                    c3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    if my_visible_tasks.empty:
        st.write("カレンダーに表示する課題がありません。")
    else:
        calendar_events = []
        for _, t in my_visible_tasks.iterrows():
            calendar_events.append({
                "title": f"[{t['lecture']}] {t['title']}",
                "start": t["due"].isoformat(),
                "backgroundColor": "#ff4b4b" if t["created_by"] == "all" else "#007bff",
                "borderColor": "#ff4b4b" if t["created_by"] == "all" else "#007bff",
            })
        
        # カレンダーオプション
        cal_options = {
            "initialView": "dayGridMonth",
            "height": 600,
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
        }
        calendar(events=calendar_events, options=cal_options)

with tab3:
    st.subheader("自分の課題の管理")
    # 自分が作ったものだけ削除可能
    my_own_tasks = df_all[df_all["created_by"] == user_name]
    
    if my_own_tasks.empty:
        st.write("あなたが追加した課題はありません。")
    else:
        for _, t in my_own_tasks.iterrows():
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(f"【{t['lecture']}】{t['title']} (⏰{t['due'].strftime('%m/%d')})")
            if col2.button("削除", key=f"del_{t['id']}"):
                delete_task(t['id'])
                st.success("削除しました")
                st.rerun()

    st.markdown("---")
    st.subheader("📢 全員共有の課題（確認用）")
    all_tasks = df_all[df_all["created_by"] == "all"]
    st.dataframe(all_tasks[["lecture", "title", "due"]], use_container_width=True)
