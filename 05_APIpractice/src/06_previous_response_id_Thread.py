import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ユーザーとの最初の対話
message1 = "フランスの首都はどこですか？"
response1 = client.responses.create(
    model="gpt-4o",
    input=message1
)
print("Q1:", message1)
print("A1:", response1.output_text)  # 例: "フランスの首都はパリです。"

# 続けてユーザーがフォローアップ質問
message2 = "そこには何人の人が住んでいますか？"
response2 = client.responses.create(
    model="gpt-4o",
    input=message2,
    previous_response_id=response1.id   # 直前の応答IDを指定
)
print("Q2:", message2)
print("A2:", response2.output_text)
