import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar  # ← これが NameError の原因です

# ページ設定
st.set_page_config(page_title="講義課題管理システム", layout="wide")

# --- binascii.Error / 秘密鍵の改行対策 ---
if "connections" in st.secrets and "gsheets" in st.secrets.connections:
    secret_data = st.secrets.connections.gsheets
    if "private_key" in secret_data:
        # Secrets内の文字列 "\n" を実際の改行コードに変換
        secret_data["private_key"] = secret_data["private_key"].replace("\\n", "\n")

# --- スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        # 読み込んだデータがNoneまたは空の場合、正しい列を持つ空のDFを返す
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])
        return data
    except Exception as e:
        # 接続エラーなどが起きた場合も止まらずに空のDFを返す
        return pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

# --- ログイン後のデータ処理部分 ---
df_all = load_data()

# 列が足りない場合の補完
for col in ["id", "lecture", "title", "due", "created_by"]:
    if col not in df_all.columns:
        df_all[col] = None

# 日付の変換（エラーが出やすい箇所なので安全に処理）
if not df_all.empty:
    df_all["due"] = pd.to_datetime(df_all["due"], errors='coerce')
    # 変換に失敗（NaT）した行を今日の日付で埋める
    df_all["due"] = df_all["due"].fillna(pd.Timestamp.now())

def save_data(df):
    # スプレッドシートを更新
    conn.update(data=df)

# --- ログイン設定 (合言葉) ---
st.sidebar.title("👤 ログイン設定")
st.sidebar.info("合言葉：名前(ひらがな) + 誕生日(2桁)\n例：ゆうすけ29")
user_name = st.sidebar.text_input("合言葉を入力してください", key="user_name")

if not user_name:
    st.warning("左側のサイドバーに合言葉を入力してログインしてください。")
    st.stop()

# データの読み込みと準備
df_all = load_data()
if not df_all.empty and "due" in df_all.columns:
    df_all["due"] = pd.to_datetime(df_all["due"])
else:
    df_all = pd.DataFrame(columns=["id", "lecture", "title", "due", "created_by"])

st.title(f"📚 {user_name} さんの課題マネージャー")

# --- サイドバー：課題追加 ---
st.sidebar.markdown("---")
st.sidebar.header("➕ 課題の追加")
add_mode = st.sidebar.radio("追加の種類:", ["自分専用", "全員に共有"])

with st.sidebar.form("add_form", clear_on_submit=True):
    lec = st.text_input("講義名")
    task = st.text_input("課題内容")
    due = st.datetime_input("提出期限", datetime.now())
    if st.form_submit_button("保存"):
        if lec and task:
            # 重複しにくいIDを生成
            new_id = f"{int(datetime.now().timestamp())}_{user_name}"
            # 作成者を記録（共有は 'all'、個人は自分の合言葉）
            creator = "all" if add_mode == "全員に共有" else user_name
            
            new_row = pd.DataFrame([{
                "id": new_id,
                "lecture": lec,
                "title": task,
                "due": due.strftime('%Y-%m-%d %H:%M'),
                "created_by": creator
            }])
            
            # 既存データに結合して保存
            df_updated = pd.concat([df_all, new_row], ignore_index=True)
            save_data(df_updated)
            st.success("スプレッドシートに保存しました！")
            st.rerun()

# --- 表示するデータのフィルタリング ---
# 共有データ または 自分の合言葉で作成したデータのみを抽出
my_visible_tasks = df_all[(df_all["created_by"] == "all") | (df_all["created_by"] == user_name)]

# タブ作成
tab1, tab2, tab3 = st.tabs(["📋 講義別リスト", "📅 カレンダー", "⚙️ 管理・削除"])

# --- タブ1: 講義別リスト ---
with tab1:
    if my_visible_tasks.empty:
        st.info("課題がありません。サイドバーから追加してください。")
    else:
        all_lecs = sorted(my_visible_tasks["lecture"].unique())
        hidden = st.multiselect("非表示にする講義:", options=all_lecs)
        # 非表示設定を除外
        display_tasks = my_visible_tasks[~my_visible_tasks["lecture"].isin(hidden)]
        
        for lec in sorted(display_tasks["lecture"].unique()):
            with st.expander(f"📖 {lec}", expanded=True):
                # その講義の課題を期限順に並べる
                lec_tasks = display_tasks[display_tasks["lecture"] == lec].sort_values("due")
                for _, t in lec_tasks.iterrows():
                    col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                    is_shared = t["created_by"] == "all"
                    tag = "📢[共有] " if is_shared else "🔒[個人] "
                    
                    # 完了チェック（ブラウザを閉じるとリセットされる簡易チェック）
                    done = col1.checkbox("", key=f"list_{t['id']}")
                    label = f"{tag}**{t['title']}**"
                    col2.write(f"~~{label}~~ ✅" if done else label)
                    col3.write(f"⏰ {t['due'].strftime('%m/%d %H:%M')}")

# --- タブ2: カレンダー ---
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
