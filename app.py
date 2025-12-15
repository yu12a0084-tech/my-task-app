import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from streamlit_calendar import calendar

DATA_FILE = 'assignments_v2.json'

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

st.set_page_config(page_title="永続課題管理システム", layout="wide")

# --- ユーザー識別 ---
st.sidebar.title("👤 ログイン設定")
user_name = st.sidebar.text_input("あなたの名前（または合言葉）を入力してください", key="user_name")

if not user_name:
    st.warning("左側のサイドバーに名前を入力してログインしてください。")
    st.stop()

# データの読み込み
if 'all_tasks' not in st.session_state:
    st.session_state.all_tasks = load_data()

# 各個人の完了チェック状態（これはブラウザセッション中のみですが、課題自体は永続化されます）
if 'my_status' not in st.session_state:
    st.session_state.my_status = {}

st.title(f"📚 {user_name} さんの課題マネージャー")

# --- サイドバー：課題追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 課題の追加")

add_mode = st.sidebar.radio("追加する種類:", ["自分専用", "全員に共有"])

with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due = st.datetime_input("提出期限", datetime.now())
    if st.form_submit_button("保存"):
        if lec and task:
            new_id = f"{int(datetime.now().timestamp())}_{user_name}"
            # 作成者を記録（全員共有の場合は 'all'）
            creator = "all" if add_mode == "全員に共有" else user_name
            new_entry = {
                "id": new_id,
                "lecture": lec,
                "title": task,
                "due": due,
                "created_by": creator
            }
            st.session_state.all_tasks.append(new_entry)
            save_data(st.session_state.all_tasks)
            st.rerun()

# --- データのフィルタリング ---
# 1. 全員共有のもの 2. 自分が作ったもの のみを表示
my_visible_tasks = [
    t for t in st.session_state.all_tasks 
    if t.get('created_by') == "all" or t.get('created_by') == user_name
]

# --- メイン画面 ---
tab1, tab2, tab3 = st.tabs(["📋 課題リスト", "📅 カレンダー", "🗑️ 課題の編集・削除"])

with tab1:
    if not my_visible_tasks:
        st.info("表示できる課題がありません。")
    else:
        # 講義の非表示フィルタ
        all_lecs = sorted(list(set(t['lecture'] for t in my_visible_tasks)))
        hidden = st.multiselect("非表示にする講義:", options=all_lecs)
        
        filtered_tasks = [t for t in my_visible_tasks if t['lecture'] not in hidden]
        
        for lec in sorted(list(set(t['lecture'] for t in filtered_tasks))):
            with st.expander(f"📖 {lec}", expanded=True):
                lec_tasks = sorted([t for t in filtered_tasks if t['lecture'] == lec], key=lambda x: x['due'])
                for t in lec_tasks:
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    is_shared = t.get('created_by') == "all"
                    tag = "📢[共有] " if is_shared else "🔒[自分] "
                    
                    done = col1.checkbox("", key=f"check_{t['id']}")
                    text = f"{tag}**{t['title']}**"
                    col2.write(f"~~{text}~~ ✅" if done else text)
                    col3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

with tab2:
    calendar_events = []
    for t in my_visible_tasks:
        is_shared = t.get('created_by') == "all"
        calendar_events.append({
            "id": t['id'],
            "title": f"{'📢' if is_shared else '🔒'}{t['title']}",
            "start": t['due'].isoformat(),
            "color": "#ff4b4b" if is_shared else "#007bff"
        })
    calendar(events=calendar_events, options={"initialView": "dayGridMonth"})

with tab3:
    st.subheader("作成した課題の管理")
    st.caption("あなたが作成した課題（共有・個人問わず）のみ編集・削除できます。")
    
    # 自分が作成者であるデータのみ編集可能にする
    my_own_data = [t for t in st.session_state.all_tasks if t.get('created_by') == user_name or (user_name == "admin" and t.get('created_by') == "all")]
    
    if my_own_data:
        df = pd.DataFrame(my_own_data)
        edited_df = st.data_editor(df, column_config={"id": None, "created_by": None}, num_rows="dynamic")
        
        if st.button("変更を確定して保存"):
            # 1. 自分のデータ以外を抽出
            other_data = [t for t in st.session_state.all_tasks if not (t.get('created_by') == user_name or (user_name == "admin" and t.get('created_by') == "all"))]
            # 2. 編集後の自分のデータを結合
            new_all_tasks = other_data + edited_df.to_dict('records')
            st.session_state.all_tasks = new_all_tasks
            save_data(new_all_tasks)
            st.success("保存しました。")
            st.rerun()
    else:
        st.write("編集できる課題がありません。")
