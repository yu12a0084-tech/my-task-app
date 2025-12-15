import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="永続・講義課題管理", layout="wide")

# --- スプレッドシート接続設定 ---
# ここにコピーしたスプレッドシートのURLを貼り付けてください
SPREADSHEET_URL = "あなたのスプレッドシートのURLをここに貼り付け"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(spreadsheet=SPREADSHEET_URL, ttl="0s")
    except:
        # 初回起動時（シートが空の場合）のデータ構造
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    conn.update(spreadsheet=SPREADSHEET_URL, data=df)

# --- ユーザー識別 ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("あなたの名前（合言葉）を入力", key="user_name")

if not user_name:
    st.warning("サイドバーに名前を入力してログインしてください。")
    st.stop()

# データの読み込み
df_all = load_data()

# 日付型に変換
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"])

# --- サイドバー：課題追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 課題の追加")
add_mode = st.sidebar.radio("種類:", ["自分専用", "全員に共有"])

with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due = st.datetime_input("提出期限", datetime.now())
    if st.form_submit_button("保存"):
        if lec and task:
            new_id = f"{int(datetime.now().timestamp())}_{user_name}"
            creator = "all" if add_mode == "全員に共有" else user_name
            
            new_row = pd.DataFrame([{
                "id": new_id,
                "lecture": lec,
                "title": task,
                "due": due.strftime('%Y-%m-%d %H:%M'),
                "created_by": creator
            }])
            
            df_updated = pd.concat([df_all, new_row], ignore_index=True)
            save_data(df_updated)
            st.success("スプレッドシートに保存しました！")
            st.rerun()

# --- メイン画面のフィルタリング ---
my_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

tab1, tab2, tab3 = st.tabs(["📋 課題リスト", "📅 カレンダー", "⚙️ 管理・削除"])

with tab1:
    if my_tasks.empty:
        st.info("課題がありません。")
    else:
        for lec in sorted(my_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = my_tasks[my_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    is_shared = t["created_by"] == "all"
                    tag = "📢" if is_shared else "🔒"
                    
                    # 完了状態は各ブラウザの一時的な状態として管理
                    done = col1.checkbox("", key=f"done_{t['id']}")
                    label = f"{tag} **{t['title']}**"
                    col2.write(f"~~{label}~~ ✅" if done else label)
                    col3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    events = []
    for _, t in my_tasks.iterrows():
        is_shared = t["created_by"] == "all"
        events.append({
            "id": t["id"],
            "title": f"[{t['lecture']}] {t['title']}",
            "start": t["due"].isoformat(),
            "color": "#ff4b4b" if is_shared else "#007bff"
        })
    calendar(events=events, options={"initialView": "dayGridMonth"})

with tab3:
    st.subheader("データの編集・削除")
    st.caption("あなたが作成したデータのみ操作可能です。")
    # 自分が作成したデータのみ抽出
    my_own_indices = df_all[df_all["created_by"] == user_name].index
    if not my_own_indices.empty:
        edited_df = st.data_editor(df_all.loc[my_own_indices], column_config={"id":None, "created_by":None}, num_rows="dynamic")
        if st.button("スプレッドシートを更新"):
            # 修正後のデータを元の全体データに反映
            df_all.update(edited_df)
            # 削除された行がある場合の対応（簡易版）
            if len(edited_df) < len(my_own_indices):
                # 削除処理は少し複雑なため、ここでは追加・修正をメインとしています
                pass
            save_data(df_all)
            st.rerun()
