import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- 1. 接続設定（最もエラーが起きない書き方） ---
# Secretsを使わず、直接URLを指定します
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nn6dT3ZSaPzxwyLb69MxDvvs6SyjdZr2UhVkkJinqv4/edit"

# 接続（引数を最小限にしてTypeErrorを回避）
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # URLを直接渡して読み込む
        return conn.read(spreadsheet=spreadsheet_url, ttl="0s")
    except:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    try:
        # URLを直接渡して書き込む
        conn.update(spreadsheet=spreadsheet_url, data=df)
        return True
    except Exception as e:
        st.error(f"保存に失敗しました。共有設定を確認してください: {e}")
        return False

# --- 2. ログイン機能 ---
st.sidebar.title("👤 ログイン")
user_name = st.sidebar.text_input("合言葉を入力")
if not user_name:
    st.info("サイドバーに合言葉を入力して開始してください。")
    st.stop()

# データの取得と整形
df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce').fillna(pd.Timestamp.now())

st.title(f"📚 {user_name} さんの課題管理")

# --- 3. 課題の追加 ---
with st.sidebar.form("add_task"):
    st.subheader("➕ 新しい課題")
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    d = st.date_input("提出日", datetime.now())
    t = st.time_input("時間", datetime.now())
    
    if st.form_submit_button("保存"):
        if lec and task:
            # 新しい行を作成
            new_row = pd.DataFrame([{
                "id": str(datetime.now().timestamp()),
                "lecture": lec,
                "title": task,
                "due": datetime.combine(d, t).strftime('%Y-%m-%d %H:%M'),
                "created_by": user_name
            }])
            # 既存データと結合して保存
            df_updated = pd.concat([df_all, new_row], ignore_index=True)
            if save_data(df_updated):
                st.success("スプレッドシートに保存完了！")
                st.rerun()

# --- 4. 表示（自分だけの課題を表示） ---
view_df = df_all[df_all["created_by"] == user_name]

tab1, tab2 = st.tabs(["📋 リスト表示", "📅 カレンダー"])

with tab1:
    if view_df.empty:
        st.write("まだ課題がありません。左のメニューから追加してください。")
    else:
        st.table(view_df[["lecture", "title", "due"]])

with tab2:
    events = [
        {"title": f"[{t['lecture']}] {t['title']}", "start": t["due"].isoformat()}
        for _, t in view_df.iterrows()
    ]
    calendar(events=events)
