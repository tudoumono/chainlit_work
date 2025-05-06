# step1_02_simpleChatStream.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# 単純なユーザーメッセージ（文字列でも可）
user_input = "PythonでFizzBuzz問題を解くコードを書いてください。"

# ストリーミングモードでAPI呼び出し
stream = client.responses.create(
    model="gpt-4o",
    input=user_input,
    stream=True
)

# 部分応答を順次受け取って表示
for event in stream:
    # event.delta にテキストの増分が含まれる
    if hasattr(event, "delta") and event.delta:
        print(event.delta, end="", flush=True)
