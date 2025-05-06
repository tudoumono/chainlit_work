import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

response = client.audio.speech.create(
    model="tts-1",  # or "tts-1-hd"（高品質版）
    voice="alloy",  # 声の種類（alloy, echo, fable, onyx, nova, shimmer）
    input="こんにちは、私はAIです！"
)

# 音声ファイルを保存する
with open("output.mp3", "wb") as f:
    f.write(response.content)