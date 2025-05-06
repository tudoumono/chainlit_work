
# Python開発者のための OpenAI Responses API チュートリアル

# 目次

- [はじめに](#はじめに)
- [前提](#前提)
- [1. Responses API の基礎](#1-responses-api-の基礎)
  - [1-1. 単発呼び出し](#1-1-単発呼び出し)
  - [1-2. ストリーミング](#1-2-ストリーミング)
- [2. ファイル検索(file_search)](#2-ファイル検索file_search)
  - [2-1. 単一ファイル](#2-1-単一ファイル)
  - [2-2. 複数ファイル](#2-2-複数ファイル)
- [3. ベクトルストアでファイル検索](#3-ベクトルストアでファイル検索)
- [4. Web 検索ツール](#4-web-検索ツール)
- [5. 画像を扱う](#5-画像を扱う)
  - [5-1. 画像理解](#5-1-画像理解)
    - [①image_urlを使用する方法](#image_urlを使用する方法)
    - [②file_idを使用する方法](#file_idを使用する方法)
  - [5-2. 画像生成](#5-2-画像生成)
- [6. Thread で会話を継続](#6-thread-で会話を継続)
- [7. モデルのファインチューニング (カスタムモデル作成)](#7-モデルのファインチューニング-カスタムモデル作成)
  - [7.1 データ準備とJSONL形式](#71-データ準備とjsonl形式)
  - [7.2 ファイルのアップロード](#72-ファイルのアップロードpurposefine-tune)
  - [7.3 ファインチューニングジョブの作成](#73-ファインチューニングジョブの作成)
  - [7.4 ファインチューニング結果の確認とモデル名取得](#74-ファインチューニング結果の確認とモデル名取得)
- [8. ファインチューニングモデルの使用 (カスタムモデル利用)](#8-ファインチューニングモデルの使用-カスタムモデル利用)
- [9. text_to_speech (TTS) と speech_to_text (STT)](#9-text_to_speech-tts-と-speech_to_text-stt)
  - [①text_to_speech（TTS）使い方](#text_to_speechtts使い方文字--音声)
  - [②speech_to_text（STT）使い方](#speech_to_textstt使い方音声--文字)
  - [③Responses APIのツール機能で使う場合](#responses-apiのツール機能で使う場合未来的)
- [10. Responses API 各種パラメータの選択肢と推奨設定](#10-responses-api-各種パラメータの選択肢と推奨設定)
  - [モデル (model) の選択肢](#モデル-model-の選択肢)
  - [入力 (input) の形式](#入力-input-の形式)
  - [ストリーミング (stream)](#ストリーミング-stream)
  - [ツール (tools) の種類](#ツール-tools-の種類)
  - [ツール使用ポリシー (tool_choice)](#ツール使用ポリシー-tool_choice)
  - [出力制御パラメータ](#出力制御パラメータ)
  - [繰り返し抑制パラメータ](#繰り返し抑制パラメータ)


## はじめに

OpenAI が提供する **Responses API (`client.responses.create`)** は、チャット生成・ドキュメント検索・Web 検索・マルチモーダル入出力などを **単一のエンドポイント** で呼び出せる統合 API です。  

---

## 前提

```bash
pip install --upgrade openai
pip install --upgrade load_dotenv
echo 'OPENAI_API_KEY="sk-proj-your-APIkey"' >> .env

```

---

## 1. Responses API の基礎

### 1‑1. 単発呼び出し

```python
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
```

### 1‑2. ストリーミング
```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# 単純なユーザーメッセージ（文字列でも可）
user_input = "PythonでFizzBuzz問題を解くコードを書いてください。"

# ストリーミングモードでAPI呼び出し
stream = client.responses.create(
    model="gpt-4o",
    input=user_input,
    stream=True
)

# 部分応答を順次受け取って表示
for event in stream:
    # event.delta にテキストの増分が含まれる
    if hasattr(event, "delta") and event.delta:
        print(event.delta, end="", flush=True)
```

---

## 2. ファイル検索(file_search)

| 方法         | 使用するパラメータ          | いつ使う？                    |
| :--------- | :----------------- | :----------------------- |
| ファイル単体で使う  | ```tools=[{"type": "file_search","file_ids": [file_id]}]```| 小規模・一時的な検索や、少数ファイル対象時    |

### 2‑1. 単一ファイル
```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルをアップロード（ベクトルストア指定なし）
uploaded_file = client.files.create(
    file=open("your_doc.pdf", "rb"),
    purpose="file_search"  #purpose="file_search" を指定すること
)

# ファイルIDの取得
file_id = uploaded_file.id

query = "このマニュアルのバージョン履歴について教えて"

response = client.responses.create(
    model="gpt-4o",
    input=query,
    tools=[
        {
            "type": "file_search",
            "file_ids": [file_id]  # vector_store_idsではなくfile_ids!!
        }
    ],
    tool_choice="required"  # 必須使用なら "required"
)
print(response.output_text)
```

### 2‑2. 複数ファイル

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイル1をアップロード
file1 = client.files.create(
    file=open("doc1.pdf", "rb"),
    purpose="file_search"
)

# ファイル2をアップロード
file2 = client.files.create(
    file=open("doc2.pdf", "rb"),
    purpose="file_search"
)

query = "これらの文書に出てくるセキュリティポリシーについてまとめてください。"

response = client.responses.create(
    model="gpt-4o",
    input=query,
    tools=[
        {
            "type": "file_search",
            "file_ids": [file1.id, file2.id]  # ←ここに複数IDを渡す
        }
    ],
    tool_choice="required"  # 必ずfile_searchさせたいなら"required"
)

print(response.output_text)
```

---

## 3. ベクトルストアでファイル検索

| 方法         | 使用するパラメータ          | いつ使う？                    |
| :--------- | :----------------- | :----------------------- |
| ベクトルストアを使う | ```tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}]```, | たくさんのファイルをまとめて管理・検索したいとき |

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ファイルをOpenAIへアップロード
file_path = "company_faq.pdf"
with open(file_path, "rb") as f:
    upload_response = client.File.create(
        file=f,
        purpose="assistants"   # アシスタントの知識ベース用途でアップロード
    )
file_id = upload_response.id
print(f"Uploaded file ID: {file_id}")

# ベクトルストアの作成
vector_store = client.vector_stores.create(name="knowledge_base")
vector_store_id = vector_store.id
print(f"Vector store ID: {vector_store_id}")

# ベクトルストアへアップロード
client.vector_stores.files.create(
    vector_store_id=vector_store_id,
    file_id=file_id
)
print("File added to vector store. (Indexing may take a moment.)")

# ※ 実際には、ファイルがベクトルストアに完全に登録（インデックス作成）されるまで数十秒待つ必要があります

# 作成したベクトルストアを使用する。
query = "社内システムのパスワードをリセットする手順は？"
response = client.responses.create(
    model="gpt-3.5-turbo",  # GPT-3.5でも検索機能は利用可能
    input=query,
    tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
    tool_choice="auto"     # （後述）必要に応じてツールを使う設定
)
# 5. 結果の表示
print("AIの回答:")
print(response.output_text)

```
# purposeに指定できる選択肢は何があるか？
現在、OpenAI公式では以下の選択肢がドキュメントで公開されています（2025年5月時点）。

| purpose値       | 意味・用途                                                         |
| :------------- | :------------------------------------------------------------ |
| `"assistants"` | **Assistants APIまたはResponses API向け**（ファイル検索、コードツール、マルチモーダルなど） |
| `"fine-tune"`  | **ファインチューニング用データ**（独自のカスタムモデルを作るための学習データ）                     |
| `"vision"`     | **画像解析用途のファイル**（一部プレビュー機能専用。通常は使用しない）                         |
| `"batch"`      | **バッチリクエスト用**（大量一括処理タスク用。現在は限定公開）                             |

つまり、
- Responses API/Assistants API → "assistants"
- モデルのファインチューニング → "fine-tune"
- 特殊な画像解析プロジェクト用 → "vision"
- 大量リクエスト専用モード → "batch"
というふうに、目的別に使い分ける必要があります。
<br>
もっと簡単に言うと、
「今すぐ動かしたいならassistants」、「将来賢くしたいならfine-tune」
これが運用判断の基本になります！

#　ベクトルストアの仕様

| 質問         | 結論                                |
| :--------- | :-------------------------------- |
| ① 誰が使える？   | 同じOrganization/Project内のAPIユーザーのみ |
| ② 1回作成でOK？ | はい。以後はファイル追加だけで運用可                |
| ③ 再作成すると？  | リセットはされないが、別ベクトルストアができる（ID注意） <br> ID（vector_store_id）が別物になる   |


---

## 4. Web 検索ツール

```python
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

```
### 通常の設定では、ベクトルストアやファインチューニングデータは外部に出ません。
| 項目               | 関与するか？  |
| :--------------- | :------ |
| 入力クエリ（query）     | ✅ 使われる  |
| ベクトルストアの中身       | ❌ 使われない |
| ファインチューニングの学習データ | ❌ 使われない |

あなたが明示的にinputに渡さない限り、モデルもツールも知ることができません。
これはOpenAIが意図的に設計しているセキュリティポリシーです。
inputの中にベクトルストアの内容を貼り付けたら当然外部検索に出ますが、意図的にそうしない限り漏洩しません。
| 項目                              | 回答                          |
| :------------------------------ | :-------------------------- |
| 通常設定でベクトルストアやファインチューニングデータが漏れる？ | ❌ 漏れない                      |
| 漏れる可能性があるとしたら？                  | ⚠️ クエリ（input）に内部データを渡した場合のみ |
| 防止するには？                         | ✅ クエリ内容を安全に設計する             |

---

## 5. 画像を扱う

### 5‑1. 画像理解
#### ①image_urlを使用する方法
```python
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


```
#### ②file_idを使用する方法
```python
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
```

### 5‑2. 画像生成

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

response = client.Image.create(
    prompt="柴犬が宇宙服を着て月面を歩いているイラスト",
    n=1,#生成枚数
    size="512x512"
)
# 生成された画像のURLを取り出す
image_url = response["data"][0]["url"]
print(image_url)
```

- 現時点では、Responses APIが直接画像バイナリを返すことはできません。
しかし、モデルに「画像生成ツール」を組み込むことでテキスト経由で画像生成を指示することも将来的には可能になるかもしれません。
現状では別途Image APIを呼び出すアプローチが確実です。
- 生成された画像URLは数時間程度有効な一時URLです。
必要に応じてダウンロードして保存してください。

- nを増やせば複数枚生成も可能ですが、画像1枚ごとに料金がかかる
- sizeは一般に512x512がバランス良いとされています。
（1024x1024も指定できますが生成に時間がかかる場合があります
- 一度テキストで画像内容の指示をResponses APIで作らせ、その指示をImage APIに渡す、といった段階を踏むことも可能。

---

## 6. Thread で会話を継続

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# ユーザーとの最初の対話
message1 = "フランスの首都はどこですか？"
response1 = client.responses.create(
    model="gpt-4o",
    input=message1
)
print("Q1:", message1)
print("A1:", response1.output_text)  # 例: "フランスの首都はパリです。"

# 続けてユーザーがフォローアップ質問
message2 = "そこには何人の人が住んでいますか？"
response2 = client.responses.create(
    model="gpt-4o",
    input=message2,
    previous_response_id=response1.id   # 直前の応答IDを指定
)
print("Q2:", message2)
print("A2:", response2.output_text)
```

### Thread管理の仕組み:

- previous_response_idを適切に渡していくだけで、会話履歴を逐一メッセージで送らなくても対話を継続できます。
- APIから返ってくるresponseオブジェクトには内部的に会話の履歴全体が紐づいているため、開発者がクライアント側で履歴を保持・マージする必要がありません

###### ※スレッドを継続すると内部的には会話履歴がどんどん長く蓄積されていきます。当然ながら、履歴が長大になるとモデルの処理負荷やトークン消費も増大します。

---

## 7. モデルのファインチューニング (カスタムモデル作成) 

#### 7.1 データ準備とJSONL形式

- チャット形式のデータ: GPT-3.5-turboやGPT-4のようなチャットモデルをファインチューニングする場合、各サンプルはメッセージのリストで構成されます。具体的には、次のようなフォーマットです

```json
{"messages": [
    {"role": "system", "content": "<システム指示（任意）>"},
    {"role": "user", "content": "<ユーザーの発話>"},
    {"role": "assistant", "content": "<アシスタントの理想的な返答>"}  
]}
```

- role: system は省略可能ですが、特定の口調やルールを持たせたい場合に含めます。
- role: user はユーザー入力、role: assistant はそれに対する望ましい回答を記述します。
必要に応じて複数ターンのやりとりを一つのmessages配列に含めることもできますが、基本は1ターンのQAペアを1行にします。

#### 例: ヘルプデスクBotのデータでは、ユーザーの質問と模範回答をペアにして並べます。
```json
{"messages": [
    {"role": "user", "content": "VPNに接続できません。どうすれば良いですか？"},
    {"role": "assistant", "content": "まずネットワーク設定を確認してください...<詳細な手順>..."}
]}
```
- 変換と確認: 既存のFAQ集や対話ログから上記形式に変換するスクリプトを用意すると良いでしょう。変換後、OpenAIの提供するデータ検証スクリプトでフォーマットを確認することもできます
- データ数は最低でも10行以上必要です。OpenAIの規約で10件未満のデータではジョブを実行できません）。またデータ量に応じてトークン数を算出し、コスト見積もりをしておくのも重要です

#### 7.2 ファイルのアップロード（purpose="fine-tune"）
```python 
# ファインチューニング用データセットをアップロード
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
```
#### 7.3 ファインチューニングジョブの作成
```python
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
```
#### 7.4 ファインチューニング結果の確認とモデル名取得
```python
#########6.4 ファインチューニング結果の確認とモデル名取得#########
result = client.FineTuningJob.retrieve(job_id=job.id)
print(result.status)  # "succeeded"（成功していれば）
print(result.fine_tuned_model)
# 出力例: ft:gpt-3.5-turbo-0613:my-org:custom-support-bot:7pO...（実際のモデル識別子）
```

## 8. ファインチューニングモデルの使用 (カスタムモデル利用)
```python
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
```



### カスタムモデルが分からなくなった場合
ファインチューニング済みモデルの名前は、APIまたはOpenAIの管理画面（Platform UI）から確認できます。
- ファインチューニングジョブが失敗していると、fine_tuned_modelは空のままです。
- 古いモデルは自動削除されることもあるので、定期的にバックアップ推奨です。

#### 【方法①】APIで確認する（コードで一覧取得）
```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

# FineTuningJobの一覧を取得する
jobs = client.FineTuningJob.list()

# 完了しているジョブだけ抜き出してモデル名を表示
for job in jobs.data:
    if job.status == "succeeded":
        print(f"Fine-tuned model: {job.fine_tuned_model}")

```
- fine_tuned_modelフィールドに完成したファインチューニングモデルの名前が入っています。
通常はこんな形になっています：
```
ft:gpt-3.5-turbo-1106:your-organization::xxxx
```


####　【方法②】OpenAI Platformの管理画面から確認する
- ブラウザで以下へアクセスします：
    OpenAI Platform → Fine-tuning Jobs
- 過去に作成したファインチューニングジョブ一覧が見れます。
- 成功しているジョブの「ファインチューニング済みモデル名（fine-tuned model）」が確認できます。

### 【ファインチューニング使用可能モデル】2025年5月時点でファインチューニングできるベースモデル一覧
| ベースモデル               | 説明                                                    |
| :------------------- | :---------------------------------------------------- |
| `gpt-3.5-turbo-0613` | GPT-3.5 Turboのファインチューニング対応版。2023年リリース。                |
| `gpt-3.5-turbo-1106` | GPT-3.5 Turboの後期版。より高精度。ファインチューニング可能。                 |
| `gpt-4-1106-preview` | GPT-4の高速版。2024年から一部ファインチューニングに対応開始。（注意：限定公開されている場合あり） |
| `davinci-002`        | 旧GPT-3系列モデル。依然としてファインチューニング対象。                        |
| `babbage-002`        | 小型モデル。高速・軽量向けチューニング対象。                                |

---
## 9. text_to_speech (TTS) と speech_to_text (STT)
>:warning:現在Responses API（openai.responses.create）にtoolsオプションで、
"text_to_speech"または"speech_to_text"を設定できる設計が進められています。
（ただし、2025年5月現在はベータ版、もしくは制限付き公開です）

| 項目| 内容|
| :------------------------- | :-------------------------------------------- |
| **text\_to\_speech (TTS)** | テキスト（文字列）を音声に変換して、音声ファイル（MP3など）として出力する。       |
| **speech\_to\_text (STT)** | 音声ファイル（WAV, MP3など）をアップロードして、文字起こし（テキスト）に変換する。 |

### ①text_to_speech（TTS）使い方（文字 → 音声）
```python
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

```
##### パラメータ解説:
| 項目| 内容|
| :------------------------- | :-------------------------------------------- |
| **model** | TTS専用モデル（通常 tts-1 または高品質版 tts-1-hd を指定）|
| **voice** | 音声スタイル（現在5種類提供） |
| **input** | 読み上げるテキスト |

### ②speech_to_text（STT）使い方（音声 → 文字）

```python
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
```

##### パラメータ解説:

| 項目| 内容|
| :------------------------- | :-------------------------------------------- |
| **model** | Whisperベースの音声認識モデル（現時点では "whisper-1"）|
| **file** | 音声ファイル (mp3, wav, m4aなどに対応) |

### ③Responses APIのツール機能で使う場合（未来的）

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の取得
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーの設定
client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-4o",
    input=[{"role": "user", "content": "この文章を音声に変換して"}],
    tools=[{"type": "text_to_speech"}],
    tool_choice="required"
)
```
（※:bangbang: この辺りはAPIのバージョンによって若干仕様変更される可能性あり）

---
---

# 10. Responses API 各種パラメータの選択肢と推奨設定

## Responses API 各種パラメータの選択肢と推奨設定

モデル選択から出力制御まで、基本的なパラメータの意味や違い、使い分け

---

### モデル (model) の選択肢

| モデル名                                         | 特徴                                              |
| :------------------------------------------- | :---------------------------------------------- |
| **GPT-3.5-Turbo**                            | ChatGPT相当。高速・低コスト。多くの用途で十分な性能。創造性・推論力はGPT-4に劣る。 |
| **GPT-4**                                    | 高度な推論力と理解力を持つ。複雑なタスクに最適。コスト・レイテンシは高め。           |
| **GPT-4o ("Omni")**                          | テキスト＋画像対応の最新マルチモーダルモデル。リアルタイム性が高く多才。利用権限に制限あり。  |
| **GPT-4o-mini**                              | GPT-4oの小型版。高速・低コスト。軽量処理や短い応答向け。総合知能は4oより下。      |
| **ファインチューニングモデル (例: ft\:gpt-3.5-turbo-...)** | ベースモデルを特定用途向けに微調整。特定ドメインでは高精度。ただし最新知識は持たない。     |

#### 選択指針

* まずは **GPT-3.5-turbo** で試す。
* 高度な推論や画像解析が必要なら **GPT-4** または **GPT-4o** を検討。
* コストや速度重視なら **GPT-4o-mini** や **GPT-3.5** を使う。

---

### 入力 (input) の形式

* **文字列**：単発質問向き。
* **メッセージ配列**：コンテキスト全体（システムメッセージ・ユーザー発言・アシスタント発言）を含めた対話を構成可能。

推奨：
→ **システム設定や直前のやりとりを活かしたい場合はメッセージ配列形式を使用。**

---

### ストリーミング (stream)

* **デフォルト**：応答完了後にまとめて返す。
* **stream=True**：応答を逐次受信でき、ユーザー体感速度が向上。

推奨使い分け：

* チャットUI → `stream=True`
* バックエンド処理 → デフォルト（まとめて受信）

---

### ツール (tools) の種類

| ツール名                                | 説明                                               |
| :---------------------------------- | :----------------------------------------------- |
| web\_search\_preview                | ウェブ検索で最新情報を取得                                    |
| file\_search                        | アップロードファイルのベクトル検索。ベクトルストアと連携して意味的検索を実現           |
| vector\_store                       | ファイルをチャンク化し、ベクトル化して保存するデータベース。file\_searchツールで使用 |
| python                              | コード実行（ベータ版機能）                                    |
| text\_to\_speech / speech\_to\_text | 音声合成・音声認識                                        |
| image\_generation                   | DALL·Eベースで画像生成（※現時点で一部限定）                        |
| moderation                          | コンテンツモデレーション（ポリシー違反検出）                           |


複数ツールを渡して、モデルに適切なものを選ばせることも可能です。

---

### ツール使用ポリシー (tool\_choice)

| 設定          | 説明                       |
| :---------- | :----------------------- |
| auto（デフォルト） | 質問に応じてモデルがツール使用を自律判断     |
| required    | 必ずツールを使用（指定ツールが1個なら強制使用） |
| none        | ツールを一切使わない               |
| 特定ツール指定     | 渡したツール群の中から特定ツールだけを強制使用  |

推奨使い分け：

* 最新情報必須 → `required`
* モデル内部知識だけで回答 → `none`
* 通常は `auto` で自然な運用。

---

### 出力制御パラメータ

#### 温度 (temperature)

* 値：`0〜2`
* 大きいほどランダム・創造的、低いと保守的・安定。
* 推奨：

  * 事実重視：`0〜0.5`
  * 創造性重視：`0.7〜1.0`
  * あまり高すぎるとまとまりが悪くなることも。

#### トップP (top\_p)

* 値：`0〜1`
* 確率上位n%に絞って選択。
* 推奨：

  * 基本は `top_p=1`
  * 特別に安定重視する場合のみ下げる。
* **OpenAI推奨**：`temperature`と`top_p`を同時に極端に操作しない。

---

### 繰り返し抑制パラメータ

| パラメータ              | 説明                          |
| :----------------- | :-------------------------- |
| presence\_penalty  | すでに出た単語へのペナルティ。話題拡散を促進。     |
| frequency\_penalty | 出現頻度が高い単語へのペナルティ。冗長な繰り返し防止。 |

* 値：`-2.0〜2.0`
* 通常は `0`（無効）だが、繰り返しを減らしたいときに `0.2〜0.5` くらい設定。

---
