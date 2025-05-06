import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# メッセージに画像を含める。(インターネット上にあるURLを指定する（例：S3などにアップロードしてリンクを渡す）)
image_url = "https://example.com/my_photo.jpg"
question = "この画像の建物は何ですか？"
messages = [
    {"role": "user", "content": question},
    {"role": "user", "content": [ {"type": "input_image", "image_url": image_url} ]}
]
response = client.responses.create(
    model="gpt-4o",  # GPT-4oは画像入力に対応
    input=messages
)
print(response.output_text)
