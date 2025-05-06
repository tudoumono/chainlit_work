import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

#########6.4 ファインチューニング結果の確認とモデル名取得#########
result = client.FineTuningJob.retrieve(job_id="作成したjob.id") #job.idは先ほど作ったカスタムモデルのid
print(result.status)  # "succeeded"（成功していれば）
print(result.fine_tuned_model)
# 出力例: ft:gpt-3.5-turbo-0613:my-org:custom-support-bot:7pO...（実際のモデル識別子）

#########7. ファインチューニング済みモデルを使う#########
custom_model_name = "<上で取得したfine_tuned_model名>"
response = client.responses.create(
    model=custom_model_name,
    input="こんにちは、調子はどう？"
)
print(response.output_text)