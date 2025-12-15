import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from streamlit_calendar import calendar

# データの保存
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

st.set_page_config(page_title="講義課題管理プロ", layout="wide")
st.title("🎓 講義課題マネージャー")

if 'assignments' not in st.session_state:
    st.session_state.assignments = load_data()
if 'my_status' not in st.session_state:
    st.session_state.my_status = {}
if 'hidden_lectures' not in st.session_state:
    st.session_state.hidden_lectures = []

# サイドバー
st.sidebar.header("➕ 新規課題の追加")
with st.sidebar.form("add_form", clear_on_submit=True):
    lecture_name = st.text_input("講義名")
    task_title = st.text_input("課題内容")
    due_datetime = st.datetime_input("提出期限", datetime.now())
    if st.form_submit_button("全員に共有して追加"):
        if lecture_name and task_title:
            new_id = str(int(datetime.now().timestamp()))
            new_task = {"id": new_id, "lecture": lecture_name, "title": task_title, "due": due_datetime}
            st.session_state.assignments.append(new_task)
            save_data(st.session_state.assignments)
            st.rerun()

all_lectures = sorted(list(set(item['lecture'] for item in st.session_state.assignments)))
st.sidebar.markdown("---")
st.sidebar.header("🚫 表示設定")
st.session_state.hidden_lectures = st.sidebar.multiselect("非表示にする講義:", options=all_lectures)

# メイン画面
tab1, tab2, tab3 = st.tabs(["📋 講義別リスト", "📅 カレンダー", "⚙️ 管理・削除"])

with tab1:
    display_data = [item for item in st.session_state.assignments if item['lecture'] not in st.session_state.hidden_lectures]
    if not display_data:
        st.info("課題はありません。")
    else:
        # 講義名でグループ化
        lectures = sorted(list(set(item['lecture'] for item in display_data)))
        for lec in lectures:
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = [t for t in display_data if t['lecture'] == lec]
                # 期限順にソート
                lec_tasks.sort(key=lambda x: x['due'])
                
                for task in lec_tasks:
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    tid = task['id']
                    is_done = col1.checkbox("", value=st.session_state.my_status.get(tid, False), key=f"list_{tid}")
                    st.session_state.my_status[tid] = is_done
                    
                    time_str = task['due'].strftime('%m/%d %H:%M')
                    if is_done:
                        col2.write(f"~~{task['title']}~~ ✅")
                    else:
                        col2.write(f"**{task['title']}**")
                    col3.write(f"⏰ {time_str}")

with tab2:
    st.subheader("期限カレンダー")
    # カレンダー用イベント作成
    calendar_events = []
    for item in st.session_state.assignments:
        if item['lecture'] not in st.session_state.hidden_lectures:
            is_done = st.session_state.my_status.get(item['id'], False)
            calendar_events.append({
                "title": f"[{item['lecture']}] {item['title']}",
                "start": item['due'].isoformat(),
                "color": "#28a745" if is_done else "#ff4b4b" # 完了は緑、未完了は赤
            })
    
    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
    }
    calendar(events=calendar_events, options=calendar_options)

with tab3:
    st.subheader("全データの管理（編集・削除）")
    if st.session_state.assignments:
        df = pd.DataFrame(st.session_state.assignments)
        edited_df = st.data_editor(
            df,
            column_config={"due": st.column_config.DatetimeColumn("期限"), "id": None},
            num_rows="dynamic",
            key="global_editor"
        )
        if st.button("全体変更を保存"):
            st.session_state.assignments = edited_df.to_dict('records')
            save_data(st.session_state.assignments)
            st.rerun()
