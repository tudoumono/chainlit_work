import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルアップロード
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
