import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

query = "今日のAI業界の重要なニュースを3つ教えてください。"
response = client.responses.create(
    model="gpt-4o",
    input=query,
    tools=[ {"type": "web_search_preview"} ],  # Web検索ツールを許可
    tool_choice="required"  # ツール使用を必須に設定
)
print(response.output_text)

#  デフォルトではモデルが自律的に「検索すべきかどうか」を判断しますが、
# tool_choiceを"required"にしたことで強制的に検索を実行させています


# ちなみに、通常の設定では、ベクトルストアやファインチューニングデータは外部に出ません。
# | 項目               | 関与するか？  |
# | :--------------- | :------ |
# | 入力クエリ（query）     | ✅ 使われる  |
# | ベクトルストアの中身       | ❌ 使われない |
# | ファインチューニングの学習データ | ❌ 使われない |
# あなたが明示的にinputに渡さない限り、モデルもツールも知ることができません。
# これはOpenAIが意図的に設計しているセキュリティポリシーです。
# inputの中にベクトルストアの内容を貼り付けたら当然外部検索に出ますが、意図的にそうしない限り漏洩しません。


