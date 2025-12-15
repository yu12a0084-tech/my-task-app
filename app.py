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
                data = json.load(f)
                # 読み込み時に日付文字列をdatetime型に変換（エラー対策）
                for item in data:
                    item['due'] = pd.to_datetime(item['due'])
                return data
        except:
            return []
    return []

def save_data(data):
    # 保存用にデータをコピー
    output_data = []
    for item in data:
        new_item = item.copy()
        # 保存時は文字列に変換
        if isinstance(new_item['due'], (datetime, pd.Timestamp)):
            new_item['due'] = new_item['due'].strftime('%Y-%m-%d %H:%M')
        output_data.append(new_item)
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

# アプリの設定
st.set_page_config(page_title="講義課題管理", layout="wide")
st.title("📚 講義課題マネージャー")

# データの初期化
if 'assignments' not in st.session_state:
    st.session_state.assignments = load_data()

# サイドバー：追加機能
st.sidebar.header("➕ 新規課題の追加")
with st.sidebar.form("add_form", clear_on_submit=True):
    lecture_name = st.text_input("講義名")
    task_title = st.text_input("課題内容")
    # 日付だけでなく「時刻」も選択できるように変更
    due_datetime = st.datetime_input("提出期限（日付と時刻）", datetime.now())
    submitted = st.form_submit_button("追加")
    
    if submitted and lecture_name and task_title:
        new_task = {
            "id": len(st.session_state.assignments) + 1,
            "lecture": lecture_name,
            "title": task_title,
            "due": due_datetime,
            "status": "未完了"
        }
        st.session_state.assignments.append(new_task)
        save_data(st.session_state.assignments)
        st.sidebar.success("追加されました！")

# メイン画面
tab1, tab2 = st.tabs(["📋 課題リスト・編集", "📅 期限リスト"])

with tab1:
    st.subheader("課題一覧")
    if not st.session_state.assignments:
        st.info("課題がありません。サイドバーから追加してください。")
    else:
        df = pd.DataFrame(st.session_state.assignments)
        
        # 編集画面の設定
        edited_df = st.data_editor(
            df, 
            column_config={
                "status": st.column_config.SelectboxColumn("状態", options=["未完了", "完了"]),
                "due": st.column_config.DatetimeColumn("提出期限", format="YYYY/MM/DD HH:mm"),
                "id": None  # IDは非表示
            },
            num_rows="dynamic",
            key="data_editor"
        )
        
        if st.button("変更を保存"):
            # 変更内容をセッション状態に反映
            st.session_state.assignments = edited_df.to_dict('records')
            save_data(st.session_state.assignments)
            st.rerun()

with tab2:
    st.subheader("期限の確認")
    if st.session_state.assignments:
        cal_df = pd.DataFrame(st.session_state.assignments)
        cal_df['due'] = pd.to_datetime(cal_df['due'])
        
        # 期限が近い順に並び替え
        sorted_df = cal_df.sort_values("due")
        
        for _, row in sorted_df.iterrows():
            status_color = "🔴" if row['status'] == "未完了" else "🟢"
            # 表示形式を「月/日 時:分」に
            time_str = row['due'].strftime('%m/%d %H:%M')
            st.info(f"{status_color} **{time_str}締切** : [{row['lecture']}] {row['title']}")
