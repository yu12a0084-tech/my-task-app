import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- 接続設定 (徹底的にシンプルにしました) ---
# Secretsの [connections.gsheets] セクションをライブラリに自動で読み込ませます。
# これにより、手動で引数を渡すことで発生していた TypeError を完全に回避します。
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 読み込み
        data = conn.read(ttl="0s")
        # 期待する5つの列が存在することを確認（不足していれば補完）
        cols = ["id", "lecture", "title", "due", "created_by"]
        if data is None or data.empty:
            return pd.DataFrame(columns=cols)
        
        # 列名がズレている、または足りない場合の保険
        for col in cols:
            if col not in data.columns:
                data[col] = None
        return data[cols]
    except Exception:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    try:
        conn.update(data=df)
    except Exception as e:
        st.error(f"保存エラー: {e}")

# --- ログイン・UI ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力（例：ゆうすけ29）", key="user_name")

if not user_name:
    st.info("左側のサイドバーに合言葉を入力してください。")
    st.stop()

# データの取得と日付の正規化
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
            save_data(df_updated)
            st.success("保存完了！")
            st.rerun()

# --- 表示タブ ---
# 「全員共有」または「自分の名前」の課題だけを抽出
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

tab1, tab2 = st.tabs(["📋 リスト", "📅 カレンダー"])

with tab1:
    if my_visible_tasks.empty:
        st.warning("表示できる課題がありません。サイドバーから追加してください。")
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
