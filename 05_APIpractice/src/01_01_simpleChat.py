# step1_01_simpleChat.py
import os
from openai import OpenAI

from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# システムメッセージとユーザーメッセージを定義
messages = [
    {"role": "system", "content": "あなたはフレンドリーなPythonの先生です。"},
    {"role": "user", "content": "Pythonで現在の日時を表示するにはどうすれば良いですか？"}
]

# 単純なユーザーメッセージ（文字列でも可）
# messages = "PythonでFizzBuzz問題を解くコードを書いてください。"

# Responses API を使って応答を取得
response = client.responses.create(
    model="gpt-4o",           # 使用するモデル。ここでは GPT-4 系列のモデルを指定
    input=messages            # メッセージのリストをそのまま input 引数に渡す
)

# 応答メッセージを出力
print(response.output_text)
