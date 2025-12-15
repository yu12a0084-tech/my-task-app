import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 最新のデータを取得
        return conn.read(ttl="0s")
    except:
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

# データの読み込みと型変換
df_all = load_data()
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"])

st.title(f"📚 {user_name} さんの課題マネージャー")

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
            st.success("保存しました！")
            st.rerun()

# --- フィルタリング ---
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

tab1, tab2, tab3 = st.tabs(["📋 講義別リスト", "📅 カレンダー", "⚙️ 管理・削除"])

with tab1:
    if my_visible_tasks.empty:
        st.info("課題がありません。サイドバーから追加してください。")
    else:
        all_lecs = sorted(my_visible_tasks["lecture"].unique())
        hidden = st.multiselect("非表示にする講義:", options=all_lecs)
        display_tasks = my_visible_tasks[~my_visible_tasks["lecture"].isin(hidden)]
        
        for lec in sorted(display_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = display_tasks[display_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    is_shared = t["created_by"] == "all"
                    tag = "📢[共有] " if is_shared else "🔒[個人] "
                    
                    done = col1.checkbox("", key=f"list_{t['id']}")
                    label = f"{tag}**{t['title']}**"
                    col2.write(f"~~{label}~~ ✅" if done else label)
                    col3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    st.subheader("期限カレンダー")
    calendar_events = []
    for _, t in my_visible_tasks.iterrows():
        is_shared = t["created_by"] == "all"
        calendar_events.append({
            "id": str(t["id"]),
            "title": f"[{t['lecture']}] {t['title']}",
            "start": t["due"].isoformat(),
            "color": "#ff4b4b" if is_shared else "#007bff"
        })
    
    calendar(events=calendar_events, options={"initialView": "dayGridMonth"})
    st.caption("🔴 赤: 全員共有 / 🔵 青: 自分専用")

with tab3:
    st.subheader("自分が作成した課題の編集・削除")
    st.caption("あなたが作成した課題（共有・個人両方）を修正できます。")
    
    my_own_mask = df_all["created_by"] == user_name
    my_own_df = df_all[my_own_mask]
    
    if not my_own_df.empty:
        edited_df = st.data_editor(
            my_own_df, 
            column_config={"id": None, "created_by": None}, 
            num_rows="dynamic",
            key="editor"
        )
        
        if st.button("変更を確定して保存"):
            others_df = df_all[~my_own_mask]
            final_df = pd.concat([others_df, edited_df], ignore_index=True)
            save_data(final_df)
            st.success("スプレッドシートを更新しました。")
            st.rerun()
    else:
        st.write("あなたが作成した課題はありません。")
