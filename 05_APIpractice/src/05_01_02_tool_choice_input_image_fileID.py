import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルをアップロード
uploaded_file = client.files.create(file=open("my_photo.jpg", "rb"), purpose="vision")
file_id = uploaded_file.id
print(file_id)

# メッセージに画像を含める。
question = "この画像の建物は何ですか？"
messages = [
    {"role": "user", "content": question},
    {"role": "user", "content": [
        {"type": "input_image", "file_id": file_id}
    ]}
]

# メッセージ送信
response = client.responses.create(
    model="gpt-4o",  # GPT-4oは画像入力に対応
    input=messages
)
print(response.output_text)