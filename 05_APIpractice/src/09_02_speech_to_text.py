import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

audio_file = open("your_audio_file.mp3", "rb")

response = client.audio.transcriptions.create(
    model="whisper-1",  # Whisperモデルを使用
    file=audio_file
)

print(response["text"])  # テキスト化された結果