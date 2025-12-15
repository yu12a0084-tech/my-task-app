import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

def get_safe_connection():
    conf = st.secrets.connections.gsheets.to_dict()
    if "private_key" in conf:
        conf["private_key"] = conf["private_key"].replace("\\n", "\n")
    if "type" in conf:
        del conf["type"]
    return st.connection("gsheets", type=GSheetsConnection, **conf)

conn = get_safe_connection()

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])
        
        # 列名がズレていた場合に強制的に合わせる
        expected_cols = ["id", "lecture", "title", "due", "created_by"]
        if list(data.columns) != expected_cols:
            data.columns = expected_cols + list(data.columns)[len(expected_cols):]
            
        return data
    except Exception:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    conn.update(data=df)

st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力（例：ゆうすけ29）", key="user_name")

if not user_name:
    st.info("左側のサイドバーに合言葉を入力してください。")
    st.stop()

df_all = load_data()

# 日付形式の修正
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

st.title(f"📚 {user_name} さんの課題")

# 課題追加（サイドバー）
with st.sidebar.form("add_form", clear_on_submit=True):
    st.header("➕ 課題追加")
    add_mode = st.radio("共有範囲", ["自分専用", "全員に共有"])
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due_d = st.date_input("日付", datetime.now())
    due_t = st.time_input("時刻", datetime.now())
    
    if st.form_submit_button("保存"):
        if lec and task:
            new_id = f"{int(datetime.now().timestamp())}"
            creator = "all" if add_mode == "全員に共有" else user_name
            due_str = datetime.combine(due_d, due_t).strftime('%Y-%m-%d %H:%M')
            
            new_row = pd.DataFrame([{"id": new_id, "lecture": lec, "title": task, "due": due_str, "created_by": creator}])
            df_updated = pd.concat([df_all, new_row], ignore_index=True)
            save_data(df_updated)
            st.success("保存しました！")
            st.rerun()

# フィルタリング（自分の課題 + 全員共有の課題）
# 入力した合言葉とスプレッドシートの created_by が一致するものだけを表示
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

tab1, tab2 = st.tabs(["📋 リスト", "📅 カレンダー"])

with tab1:
    if my_visible_tasks.empty:
        st.warning(f"現在、{user_name} さんが閲覧できる課題はありません。サイドバーから新しく追加してください。")
    else:
        for lec in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    col1, col2 = st.columns([0.7, 0.3])
                    tag = "📢" if t["created_by"] == "all" else "🔒"
                    col1.write(f"{tag} **{t['title']}**")
                    col2.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    calendar_events = []
    for _, t in my_visible_tasks.iterrows():
        calendar_events.append({
            "title": f"[{t['lecture']}] {t['title']}",
            "start": t["due"].isoformat(),
            "color": "#ff4b4b" if t["created_by"] == "all" else "#007bff"
        })
    calendar(events=calendar_events)
