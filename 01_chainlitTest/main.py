"""
main.py － Chainlit + OpenAI (デバッグモード対応)
================================================

● 追加機能
------------------------------------------------
* 環境変数 DEBUG_MODE=1 で **デバッグモード** に切替
  - OpenAI へはアクセスしない
  - 代わりに「ダミー応答」を返す（API料金ゼロ）
  - コードの動作確認や UI テストに便利

● DEBUG_MODE の切り替え方法
------------------------------------------------
Windows (PowerShell) :
    $env:DEBUG_MODE="1"; poetry run chainlit run main.py

macOS / Linux :
    DEBUG_MODE=1 poetry run chainlit run main.py

.env を使う場合（本番は 0、開発時は 1 など）:
    DEBUG_MODE=1

● 参考ドキュメント
------------------------------------------------
* Chainlit Decorators & Classes:  
  https://docs.chainlit.io/api-reference
* OpenAI Chat Completions:  
  https://platform.openai.com/docs/api-reference/chat
"""

# --- 標準ライブラリ ---------------------------------------------------------
import os
from datetime import datetime
from pathlib import Path
import json

# --- サードパーティ --------------------------------------------------------
from dotenv import load_dotenv
import chainlit as cl
from openai import AsyncOpenAI

# =============================================================================
# 1. 初期設定
# =============================================================================
load_dotenv()                                              # .env を読み込み
DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"           # デバッグ判定
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # OpenAI クライアント

# =============================================================================
# 2. OpenAI へ問い合わせるヘルパ関数
# =============================================================================
async def ask_openai(
    client: AsyncOpenAI,
    user_message: str,
    history: list[dict] | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 1024,
):
    """
    Chat Completion をストリーミングで取得。
    DEBUG_MODE 時は OpenAI を呼ばずにダミー応答を返す。
    """
    if DEBUG_MODE:
        # ---------- デバッグ：ダミーのストリームを返す ----------
        async def fake_stream():
            # OpenAI ストリームの形式に簡易的に似せたオブジェクトを yield
            class DummyDelta:
                def __init__(self, content): self.content = content

            class DummyChoice:
                def __init__(self, content): self.delta = DummyDelta(content)

            class DummyChunk:
                def __init__(self, content): self.choices = [DummyChoice(content)]

            # 実際は少しずつ文章を送る
            for part in ["（デバッグ）", "これは ", "OpenAI を ", "呼び出して ", "いません。"]:
                yield DummyChunk(part)
        return fake_stream()

    # ---------- 通常モード：OpenAI へ問い合わせ ----------
    messages = (history or []) + [{"role": "user", "content": user_message}]
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

# =============================================================================
# 3. チャット開始時
# =============================================================================
@cl.on_chat_start
async def start():
    """
    ルーム生成直後に 1 回だけ実行。
    デバッグ時はモード表示を追加。
    """
    prefix = "🛠️【デバッグモード】\n" if DEBUG_MODE else ""
    await cl.Message(
        content=f"{prefix}質問してください：",
        actions=[cl.Action(name="save", value="save", label="保存", payload={})],
    ).send()

# =============================================================================
# 4. 「保存」ボタン押下時
# =============================================================================
@cl.action_callback("save")
async def save_history_to_file(action: cl.Action):
    """
    会話履歴 (chat_history) を JSON に保存してダウンロードリンクを提示。
    """
    history = cl.user_session.get("chat_history", [])
    if not history:
        return

    log_dir = Path("chatlogs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"session_{timestamp}.json"
    log_file = log_dir / file_name

    with log_file.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    await cl.Message(
        content="このチャネルでのやり取りを保存しました。",
        elements=[cl.File(name=file_name, path=str(log_file), display="inline")],
    ).send()

# =============================================================================
# 5. ユーザーからのメッセージ処理
# =============================================================================
@cl.on_message
async def on_message(message: cl.Message):
    """
    1) 履歴取得 → 2) ask_openai 呼び出し (デバッグ時はダミー) → 3) ストリーム表示
    """
    # ----- 1) 会話履歴を取得しユーザ発言を追加 ------------------------------
    history: list[dict] = cl.user_session.get("chat_history", [])
    history.append({"role": "user", "content": message.content})

    # 画面に空メッセージを置き後で update()
    stream_msg = await cl.Message(content="").send()

    try:
        # ----- 2) ask_openai（内部でデバッグ判定） -------------------------
        stream = await ask_openai(client, user_message=message.content, history=history)

        assistant_text = ""  # GPT 生成文を蓄積

        # ----- 3) ストリームを逐次受信し UI 更新 --------------------------
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                stream_msg.content += delta
                await stream_msg.update()

        # GPT 完了後に履歴へ追加
        history.append({"role": "assistant", "content": assistant_text})

    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {e}").send()

    finally:
        # 履歴をセッションへ保存
        cl.user_session.set("chat_history", history)

        # 完了メッセージ＋保存ボタン
        await cl.Message(
            content="✅ 応答完了！次の操作を選んでください：",
            actions=[cl.Action(name="save", value="save", label="保存", payload={})],
        ).send()
