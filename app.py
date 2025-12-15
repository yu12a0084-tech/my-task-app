import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- 接続設定（書き込みを成功させるための修正） ---
def get_connection():
    # Secretsの内容を取得
    secret_data = st.secrets.connections.gsheets.to_dict()
    # 秘密鍵の中の「\\n」を「本物の改行」に変換（これが無いと書き込み権限エラーになります）
    if "private_key" in secret_data:
        secret_data["private_key"] = secret_data["private_key"].replace("\\n", "\n")
    # typeが重複してTypeErrorになるのを防ぐ
    if "type" in secret_data:
        del secret_data["type"]
    
    return st.connection("gsheets", type=GSheetsConnection, **secret_data)

conn = get_connection()

def load_data():
    try:
        data = conn.read(ttl="0s")
        cols = ["id", "lecture", "title", "due", "created_by"]
        if data is None or data.empty:
            return pd.DataFrame(columns=cols)
        # 必要な列が揃っているか確認
        for col in cols:
            if col not in data.columns:
                data[col] = None
        return data[cols]
    except Exception:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    try:
        # スプレッドシートを更新
        conn.update(data=df)
        return True
    except Exception as e:
        st.error(f"保存に失敗しました。権限または鍵の設定を確認してください: {e}")
        return False

# --- ログイン設定 ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力（例：ゆうすけ29）", key="user_name")

if not user_name:
    st.info("左側のサイドバーに合言葉を入力してください。")
    st.stop()

# データの取得
df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

st.title(f"📚 {user_name} さんの課題管理")

# --- 課題追加フォーム ---
with st.sidebar.form("add_form", clear_on_submit=True):
    st.header("➕ 課題追加")
    add_mode = st.radio("共有範囲", ["自分専用", "全員に共有"])
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due_date = st.date_input("提出日", datetime.now())
    due_time = st.time_input("提出時間", datetime.now())
    
    if st.form_submit_button("保存"):
        if lec and task:
            new_id = f"{int(datetime.now().timestamp())}"
            creator = "all" if add_mode == "全員に共有" else user_name
            due_dt = datetime.combine(due_date, due_time).strftime('%Y-%m-%d %H:%M')
            
            new_row = pd.DataFrame([{"id": new_id, "lecture": lec, "title": task, "due": due_dt, "created_by": creator}])
            df_updated = pd.concat([df_all, new_row], ignore_index=True)
            
            if save_data(df_updated):
                st.success("スプレッドシートに保存しました！")
                st.rerun()

# --- 表示 ---
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

tab1, tab2 = st.tabs(["📋 リスト", "📅 カレンダー"])

with tab1:
    if my_visible_tasks.empty:
        st.warning("表示できる課題がありません。")
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
    calendar_events = [
        {"title": f"[{t['lecture']}] {t['title']}", "start": t["due"].isoformat()}
        for _, t in my_visible_tasks.iterrows()
    ]
    calendar(events=calendar_events)
