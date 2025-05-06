import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# テキストから画像生成（DALL·E 3）
# 現時点では、Responses APIが直接画像バイナリを返すことはできません。
# しかし、モデルに「画像生成ツール」を組み込むことでテキスト経由で画像生成を指示することも将来的には可能になるかもしれません。
# 現状では別途Image APIを呼び出すアプローチが確実です。
response = client.Image.create(
    prompt="柴犬が宇宙服を着て月面を歩いているイラスト",
    n=1,#生成枚数
    size="512x512"
)
# 生成された画像のURLを取り出す
image_url = response["data"][0]["url"]
print(image_url)

# 生成された画像URLは数時間程度有効な一時URLです。
# 必要に応じてダウンロードして保存してください。

# nを増やせば複数枚生成も可能ですが、画像1枚ごとに料金がかかる
# sizeは一般に512x512がバランス良いとされています。
# （1024x1024も指定できますが生成に時間がかかる場合があります