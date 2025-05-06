import os
from openai import OpenAI

from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルアップロード
file_path = "company_faq.pdf"
with open(file_path, "rb") as f:
    upload_response = client.File.create(
        file=f,
        purpose="assistants"   # アシスタントの知識ベース用途でアップロード
    )
file_id = upload_response.id
print(f"Uploaded file ID: {file_id}")

# purposeに指定できる選択肢は何があるか？
# | purpose値       | 意味・用途                                                         |
# | :------------- | :------------------------------------------------------------ |
# | `"assistants"` | **Assistants APIまたはResponses API向け**（ファイル検索、コードツール、マルチモーダルなど） |
# | `"fine-tune"`  | **ファインチューニング用データ**（独自のカスタムモデルを作るための学習データ）                     |
# | `"vision"`     | **画像解析用途のファイル**（一部プレビュー機能専用。通常は使用しない）                         |
# | `"batch"`      | **バッチリクエスト用**（大量一括処理タスク用。現在は限定公開）                             |

# ファイルアップロードすることでできること。
# | 利用先                                                               | 説明                               |
# | :---------------------------------------------------------------- | :------------------------------- |
# | 1. ベクトルストア（`vector_stores.files.create`）                          | → ファイルの内容をEmbeddingして検索できるようにする  |
# | 2. ファイルクエリ（`openai.beta.threads.messages.create`の`file_ids`オプション） | → Chatで「このファイルを読んで答えて」みたいな指定ができる |
# | 3. ファインチューニング用データ（`openai.fine_tuning.jobs.create`）               | → モデルの追加学習データ（JSONL形式など）に使う      |
# | 4. バッチリクエスト用データ（`openai.batches.create`）                          | → APIリクエストを一括で大量に送信するための入力データに使う |
# | 5. ストレージからのダウンロード/削除管理                                            | → ファイルとして再ダウンロードしたり、削除管理するだけの場合も |


