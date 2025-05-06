import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルをOpenAIへアップロード
file_path = "company_faq.pdf"
with open(file_path, "rb") as f:
    upload_response = client.File.create(
        file=f,
        purpose="assistants"   # アシスタントの知識ベース用途でアップロード
    )
file_id = upload_response.id
print(f"Uploaded file ID: {file_id}")

# ベクトルストアの作成
vector_store = client.vector_stores.create(name="knowledge_base")
vector_store_id = vector_store.id
print(f"Vector store ID: {vector_store_id}")

# ベクトルストアへアップロード
client.vector_stores.files.create(
    vector_store_id=vector_store_id,
    file_id=file_id
)
print("File added to vector store. (Indexing may take a moment.)")

# ※ 実際には、ファイルがベクトルストアに完全に登録（インデックス作成）されるまで数十秒待つ必要があります

# 作成したベクトルストアを使用する。
query = "社内システムのパスワードをリセットする手順は？"
response = client.responses.create(
    model="gpt-3.5-turbo",  # GPT-3.5でも検索機能は利用可能
    input=query,
    tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
    tool_choice="auto"     # （後述）必要に応じてツールを使う設定
)
# 5. 結果の表示
print("AIの回答:")
print(response.output_text)