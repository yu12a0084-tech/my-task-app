import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# データの保存用ファイル名
DATA_FILE = 'assignments.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# アプリの設定
st.set_page_config(page_title="講義課題管理", layout="wide")
st.title("📚 講義課題マネージャー")

# データの読み込み
if 'assignments' not in st.session_state:
    st.session_state.assignments = load_data()

# サイドバー：追加機能
st.sidebar.header("➕ 新規課題の追加")
with st.sidebar.form("add_form", clear_on_submit=True):
    lecture_name = st.text_input("講義名")
    task_title = st.text_input("課題内容")
    due_date = st.date_input("提出期限", datetime.now())
    submitted = st.form_submit_button("追加")
    
    if submitted and lecture_name and task_title:
        new_task = {
            "id": len(st.session_state.assignments) + 1,
            "lecture": lecture_name,
            "title": task_title,
            "due": str(due_date),
            "status": "未完了"
        }
        st.session_state.assignments.append(new_task)
        save_data(st.session_state.assignments)
        st.sidebar.success("追加されました！")

# メイン画面
tab1, tab2 = st.tabs(["📋 課題リスト・編集", "📅 カレンダー表示"])

with tab1:
    st.subheader("課題一覧")
    if not st.session_state.assignments:
        st.info("課題がありません。サイドバーから追加してください。")
    else:
        df = pd.DataFrame(st.session_state.assignments)
        edited_df = st.data_editor(
            df, 
            column_config={
                "status": st.column_config.SelectboxColumn("状態", options=["未完了", "完了"]),
                "due": st.column_config.DateColumn("提出期限")
            },
            num_rows="dynamic",
            key="data_editor"
        )
        if st.button("変更を保存"):
            st.session_state.assignments = edited_df.to_dict('records')
            save_data(st.session_state.assignments)
            st.rerun()

with tab2:
    st.subheader("期限カレンダー")
    if st.session_state.assignments:
        cal_df = pd.DataFrame(st.session_state.assignments)
        cal_df['due'] = pd.to_datetime(cal_df['due'])
        target_month = st.date_input("表示月を選択", datetime.now()).month
        filtered_df = cal_df[cal_df['due'].dt.month == target_month].sort_values("due")
        
        if filtered_df.empty:
            st.write("この月の期限はありません。")
        else:
            for _, row in filtered_df.iterrows():
                st.info(f"📅 {row['due'].strftime('%m/%d')} : [{row['lecture']}] {row['title']} ({row['status']})")
