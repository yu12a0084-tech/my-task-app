# Secretsの \n を本物の改行に変換する（binascii.Error 対策）
if "connections" in st.secrets and "gsheets" in st.secrets.connections:
    secret_data = st.secrets.connections.gsheets
    if "private_key" in secret_data:
        # 文字列としての \n を実際の改行コードに置換
        secret_data["private_key"] = secret_data["private_key"].replace("\\n", "\n")

# その後に接続
conn = st.connection("gsheets", type=GSheetsConnection)
