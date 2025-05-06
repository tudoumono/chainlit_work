import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

#########6.2 ファイルのアップロード（purpose="fine-tune"）#########
# ファインチューニング用データセットをアップロード
file_path = "./data/my_training_data.jsonl"
with open(file_path, "rb") as f:
    file_obj = client.File.create(
        file=f,
        purpose='fine-tune'   # ファインチューニング目的でアップロード
    )
training_file_id = file_obj.id
print(f"Training File ID: {training_file_id}")

# ファイル一覧
print(client.File.list())

# ファイル削除
# print(client.File.delete(file_id))


#########6.3 ファインチューニングジョブの作成#########
# ファインチューニングジョブの作成
job = client.FineTuningJob.create(
    training_file=training_file_id,
    model="gpt-3.5-turbo",       # ベースとするモデル
    suffix="custom-support-bot"  # （任意）カスタムモデル名に付与される識別子。省略可。
)
print(f"Fine-tuning Job ID: {job.id}, status: {job.status}")
# ジョブIDはftjob-...という形式
# job.status は"running"もしくは"queued"となります。
# ファインチューニングジョブ一覧はclient.FineTuningJob.list()で確認できる。
print(client.FineTuningJob.list())

# 特定ジョブの詳細はclient.FineTuningJob.retrieve(job_id)で取得できます。
# print(client.FineTuningJob.retrieve(job_id))

#########6.4 ファインチューニング結果の確認とモデル名取得#########
result = client.FineTuningJob.retrieve(job_id=job.id)
print(result.status)  # "succeeded"（成功していれば）
print(result.fine_tuned_model)
# 出力例: ft:gpt-3.5-turbo-0613:my-org:custom-support-bot:7pO...（実際のモデル識別子）



