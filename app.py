import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from streamlit_javascript import st_javascript # 初回のみ必要

# データの保存用ファイル名（共有用）
DATA_FILE = 'assignments.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    item['due'] = pd.to_datetime(item['due'])
                return data
        except: return []
    return []

def save_data(data):
    output_data = []
    for item in data:
        new_item = item.copy()
        if isinstance(new_item['due'], (datetime, pd.Timestamp)):
            new_item['due'] = new_item['due'].strftime('%Y-%m-%d %H:%M')
        output_data.append(new_item)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

# アプリの設定
st.set_page_config(page_title="共有課題管理", layout="wide")
st.title("👥 講義課題マネージャー（共有版）")

# 1. 共有データの読み込み
if 'assignments' not in st.session_state:
    st.session_state.assignments = load_data()

# 2. 個人データの管理（ブラウザの「完了」と「非表示講義」）
# ※簡易的に st.session_state で管理。ブラウザを閉じるとリセットされます。
if 'my_status' not in st.session_state:
    st.session_state.my_status = {} # {課題ID: True/False}
if 'hidden_lectures' not in st.session_state:
    st.session_state.hidden_lectures = []

# サイドバー：追加とフィルター
st.sidebar.header("➕ 新規課題の追加（全員に共有）")
with st.sidebar.form("add_form", clear_on_submit=True):
    lecture_name = st.text_input("講義名")
    task_title = st.text_input("課題内容")
    due_datetime = st.datetime_input("提出期限", datetime.now())
    if st.form_submit_button("追加"):
        if lecture_name and task_title:
            new_id = str(int(datetime.now().timestamp())) # 重複しないID
            new_task = {"id": new_id, "lecture": lecture_name, "title": task_title, "due": due_datetime}
            st.session_state.assignments.append(new_task)
            save_data(st.session_state.assignments)
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🚫 講義の表示設定")
all_lectures = sorted(list(set(item['lecture'] for item in st.session_state.assignments)))
st.session_state.hidden_lectures = st.sidebar.multiselect(
    "非表示にしたい講義を選択:",
    options=all_lectures,
    default=st.session_state.hidden_lectures
)

# メイン画面
tab1, tab2 = st.tabs(["📋 課題リスト（自分用表示）", "⚙️ 課題の編集・削除（全員に反映）"])

with tab1:
    st.subheader("自分専用の課題リスト")
    display_data = [item for item in st.session_state.assignments if item['lecture'] not in st.session_state.hidden_lectures]
    
    if not display_data:
        st.info("表示する課題はありません。")
    else:
        for item in display_data:
            col1, col2 = st.columns([0.1, 0.9])
            item_id = item['id']
            # チェックボックスの状態を保持
            is_done = col1.checkbox("", value=st.session_state.my_status.get(item_id, False), key=f"check_{item_id}")
            st.session_state.my_status[item_id] = is_done
            
            # 完了済みの場合は打ち消し線
            text = f"**{item['due'].strftime('%m/%d %H:%M')}** | [{item['lecture']}] {item['title']}"
            if is_done:
                col2.write(f"~~{text}~~ ✅")
            else:
                col2.write(text)

with tab2:
    st.subheader("課題の編集と一括削除")
    st.warning("⚠️ ここでの変更や削除は、利用者全員の画面に反映されます。")
    
    if st.session_state.assignments:
        df = pd.DataFrame(st.session_state.assignments)
        edited_df = st.data_editor(
            df,
            column_config={
                "due": st.column_config.DatetimeColumn("期限", format="YYYY/MM/DD HH:mm"),
                "id": None
            },
            num_rows="dynamic", # ここで行を選択して削除（Delキー）可能
            key="editor_all"
        )
        
        if st.button("全体に反映（保存）"):
            st.session_state.assignments = edited_df.to_dict('records')
            save_data(st.session_state.assignments)
            st.success("全員のデータを更新しました！")
            st.rerun()
    else:
        st.write("課題がありません。")
