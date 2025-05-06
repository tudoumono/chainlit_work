import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイル1をアップロード
file1 = client.files.create(
    file=open("doc1.pdf", "rb"),
    purpose="file_search"
)

# ファイル2をアップロード
file2 = client.files.create(
    file=open("doc2.pdf", "rb"),
    purpose="file_search"
)

query = "これらの文書に出てくるセキュリティポリシーについてまとめてください。"

response = client.responses.create(
    model="gpt-4o",
    input=query,
    tools=[
        {
            "type": "file_search",
            "file_ids": [file1.id, file2.id]  # ←ここに複数IDを渡す
        }
    ],
    tool_choice="required"  # 必ずfile_searchさせたいなら"required"
)

print(response.output_text)
