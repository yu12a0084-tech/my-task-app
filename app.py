import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# ページ設定
st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- スプレッドシート接続 ---
# Secretsが正しく書かれていれば、この1行だけで自動的に認証されます
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])
        return data
    except Exception:
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

def save_data(df):
    conn.update(data=df)

# --- ログイン設定 ---
st.sidebar.title("👤 ログイン設定")
st.sidebar.info("合言葉：名前(ひらがな) + 誕生日(2桁)\n例：ゆうすけ29")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_name")

if not user_name:
    st.warning("左側のサイドバーに合言葉を入力してログインしてください。")
    st.stop()

# データの読み込み
df_all = load_data()
if not df_all.empty and "due" in df_all.columns:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce')
    df_all["due"] = df_all["due"].fillna(pd.Timestamp.now())
else:
    df_all = pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

st.title(f"📚 {user_name} さんの課題マネージャー")

# --- 課題追加 ---
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
            new_id = f"{int(datetime.now().timestamp())}_{user_name}"
            creator = "all" if add_mode == "全員に共有" else user_name
            due_dt = datetime.combine(due_date, due_time)
            
            new_row = pd.DataFrame([{
                "id": new_id,
                "lecture": lec,
                "title": task,
                "due": due_dt.strftime('%Y-%m-%d %H:%M'),
                "created_by": creator
            }])
            
            df_updated = pd.concat([df_all, new_row], ignore_index=True)
            save_data(df_updated)
            st.success("保存完了！")
            st.rerun()

# --- タブ表示 ---
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]
tab1, tab2, tab3 = st.tabs(["📋 講義別リスト", "📅 カレンダー", "⚙️ 管理・削除"])

with tab1:
    if my_visible_tasks.empty:
        st.info("表示できる課題がありません。")
    else:
        for lec in sorted(my_visible_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = my_visible_tasks[my_visible_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    tag = "📢[共有] " if t["created_by"] == "all" else "🔒[個人] "
                    done = col1.checkbox("", key=f"list_{t['id']}")
                    col2.write(f"~~{tag}{t['title']}~~ ✅" if done else f"{tag}{t['title']}")
                    col3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    calendar_events = []
    for _, t in my_visible_tasks.iterrows():
        calendar_events.append({
            "id": str(t["id"]),
            "title": f"[{t['lecture']}] {t['title']}",
            "start": t["due"].isoformat(),
            "color": "#ff4b4b" if t["created_by"] == "all" else "#007bff"
        })
    calendar(events=calendar_events, options={"initialView": "dayGridMonth"})

with tab3:
    st.subheader("自分の課題の削除・編集")
    my_own_df = df_all[df_all["created_by"] == user_name]
    if not my_own_df.empty:
        edited_df = st.data_editor(my_own_df, column_config={"id": None, "created_by": None}, num_rows="dynamic")
        if st.button("変更をスプレッドシートに反映"):
            others_df = df_all[df_all["created_by"] != user_name]
            final_df = pd.concat([others_df, edited_df], ignore_index=True)
            save_data(final_df)
            st.success("更新しました！")
            st.rerun()
    else:
        st.write("あなたが作成した課題はありません。")
