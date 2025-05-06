import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルをアップロード（ベクトルストア指定なし）
uploaded_file = client.files.create(
    file=open("your_doc.pdf", "rb"),
    purpose="file_search"  #purpose="file_search" を指定すること
)

# ファイルIDの取得
file_id = uploaded_file.id

query = "このマニュアルのバージョン履歴について教えて"

response = client.responses.create(
    model="gpt-4o",
    input=query,
    tools=[
        {
            "type": "file_search",
            "file_ids": [file_id]  # vector_store_idsではなくfile_ids!!
        }
    ],
    tool_choice="required"  # 必須使用なら "required"
)
print(response.output_text)
