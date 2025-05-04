# デバック用ライブラリ

# 標準ライブラリ
import os
import pathlib
import asyncio

# ディストリビューションライブラリ
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Chainlitのライブラリ
import chainlit as cl   #メインのライブラリ
from chainlit.input_widget import Select, Switch, Slider  #ウジェット

# 自作ライブラリのインポート

################ 関数 #####################
# OpenAIのクライアント初期化
def openai_init_client(api_key:str):
    if not api_key:
        cl.Message("APIキーが設定されていません。").send()
        raise ValueError("APIキーが設定されていません。")
    try:
        client = AsyncOpenAI(api_key=api_key)
        return client
    except Exception as e:
        cl.Message(f"エラーが起きました: {str(e)}").send()
        # 例外を再発生させるか
        raise RuntimeError(f"OpenAIクライアントの初期化に失敗しました: {str(e)}") from e

# asyncで非同期関数でメッセージの送信
async def generate_text(client: AsyncOpenAI, prompt: str, model: str):
    "非同期でOpenAIにリクエストを送信する"
    response = await client.responses.create(
        model=model,
        input=prompt,
        store=True,  # 会話履歴をサーバー側で管理
        stream=True #ストリーミング設定ON
    )
    return response

################ グローバル変数 #####################
# 環境変数
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Open API の初期化する。
client:AsyncOpenAI = openai_init_client(OPENAI_API_KEY)

# チャット起動時
@cl.on_chat_start
async def start():
        # 設定のウィジェットを追加
        settings =await cl.ChatSettings(
        [
            Select(#モデルの選択
                id="Model",
                label="OpenAI - Model",
                values=["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"],
                initial_index=0,
            ),
        ]
    ).send()
        # ユーザーセッションを設定
        # ユーザの入力を保存するhistoryを作成
        cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}],
        )
        cl.user_session.set("model", settings["Model"])    # モデルの設定

# 設定が更新されたら実行される。
@cl.on_settings_update
async def setup_agent(settings):
    # 設定が更新されたときに呼び出される
    # 新しい設定をuser_sessionに保存
    cl.user_session.set("model", settings["Model"])
    # ユーザーに設定が更新されたことを通知（オプション）
    await cl.Message(f"設定を更新しました: モデル = {settings['Model']}").send()


# メッセージを受信されたら実行
@cl.on_message
async def on_message(message: cl.Message):
    # 最初に空のメッセージを送信（更新用）⇒アシスタント側のアイコンが出るので処理していることをユーザに視覚的に知らせることができる。
    msg = cl.Message(content="")# インスタンス化
    await msg.send()  # インスタンスメソッドとして呼び出す

    # ユーザの入力をhistoryに格納
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})

    # user_sessionから最新の設定を取得
    model = cl.user_session.get("model")
    
    # 完全なレスポンスを保存するための変数
    full_response = ""

    # メッセージ送信の関数呼び出し
    stream_response = await generate_text(client,message.content,model)

    # ストリームの各チャンクを処理
    async for chunk in stream_response:
        # イベント構造に基づいてテキストを抽出
        if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text') and chunk.delta.text:
            content = chunk.delta.text
            full_response += content
            await msg.stream_token(content)

    # 完全なレスポンスをメッセージ履歴に追加
    message_history.append({"role": "assistant", "content": full_response})

    # ストリーム完了時に最終更新
    await msg.update()


