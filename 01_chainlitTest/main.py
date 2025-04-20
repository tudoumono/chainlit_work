"""
main.py － Chainlit + OpenAI チャットアプリ
=========================================
このファイルを実行すると、ブラウザでチャット UI が立ち上がります。
利用者は「GPT‑3.5 / GPT‑4 / GPT‑4o‑mini」を途中でも自由に切り替えて対話できます。

--------------------------------------------------------------------------
💡 “ざっくり全体像”
--------------------------------------------------------------------------
1. **初期化**      : 環境変数を読み込み、OpenAI クライアントを作成
2. **モデル選択UI**: 起動時にボタンを表示（`show_model_selection()`）
3. **チャット処理**: ユーザー発言を受け取り、OpenAI へ問合せて返却
4. **履歴保存**    : 「保存」ボタンで JSON にエクスポート
5. **モデル変更**  : いつでも「モデル変更」ボタンで再選択できる
6. **デバッグモード**: `DEBUG_MODE=1` で OpenAI を呼ばずダミー応答

※ なるべく **非エンジニアでも読めるよう**、専門用語を噛み砕きつつ
   コード内コメントを多めに入れています。
"""

# ────────────────────────────────────────────────────────────────
# 0. ライブラリの読み込み
# ────────────────────────────────────────────────────────────────
import os
import json
from datetime import datetime
from pathlib import Path

# ▼ サードパーティ（外部）ライブラリ
from dotenv import load_dotenv           # .env から変数を読むお手軽ユーティリティ
import chainlit as cl                    # チャットUIを超簡単に作れるフレームワーク
from openai import AsyncOpenAI           # OpenAI (GPT など) とやり取りする公式クライアント

# ────────────────────────────────────────────────────────────────
# 1. 初期設定
# ────────────────────────────────────────────────────────────────
load_dotenv()                            # .env ファイルから環境変数を取り込む
DEBUG_MODE = os.getenv("DEBUG_MODE") == "1"   # 文字列 "1" ならデバッグ
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#   ↑ ChatGPT と同じモデルを “自分のプログラム” から呼ぶためのクラス
#     非同期版なので大量トラフィックにも強い

# ────────────────────────────────────────────────────────────────
# 2. “どのGPTを使うか” のリスト定義
# ────────────────────────────────────────────────────────────────
MODELS = [
    ("GPT‑3.5 Turbo",       "gpt-3.5-turbo"),        # 軽量・高速・低価格
    ("GPT‑4 Turbo",         "gpt-4-turbo"),          # GPT-4ベースで高速・安価
    ("GPT‑4o",              "gpt-4o"),               # 最新・マルチモーダル（音声・画像・テキスト）
]

get_prefix = lambda: "🛠️【デバッグモード】\n" if DEBUG_MODE else ""

# ────────────────────────────────────────────────────────────────
# 3. モデル選択ボタンを出す共通関数
# ────────────────────────────────────────────────────────────────
async def show_model_selection():
    """モデル選択メニューを1か所で生成（DRY 原則）"""
    await cl.Message(
        content=f"{get_prefix()}🧠 使用するモデルを選んでください：",
        actions=[
            cl.Action(                 # ボタン UI を1つ作る
                name="select_model",   # クリック時トリガーとなる識別子
                label=label,           # ボタンに表示する文字
                payload={"model": val} # “どのモデルか” 情報を渡す箱
            )
            for label, val in MODELS
        ],
    ).send()

# ────────────────────────────────────────────────────────────────
# 4. OpenAI へ質問を投げる小さな関数
# ────────────────────────────────────────────────────────────────
async def ask_openai(user_message: str,
                     history: list[dict],
                     model: str,
                     temperature: float = 0.7,
                     max_tokens: int = 1024):
    """
    * 普段:   OpenAI に問い合わせ、ストリーミングで返す
    * デバッグ: ダミー文字列をちびちび返す（API料金ゼロ）
    """
    # --- デバッグ用ダミー ---
    if DEBUG_MODE:
        async def fake_stream():
            for chunk in ["（デバッグ）", "これは ", "OpenAI を ", "呼び出して ", "いません。"]:
                # Chainlit が期待する “delta.content” 構造を最低限エミュレート
                yield type("Chunk", (), {
                    "choices": [type("Choice", (), {
                        "delta": type("Delta", (), {"content": chunk})()
                    })()]
                })()
        return fake_stream()

    # --- 本番: OpenAI へ問い合わせ ---
    messages = history + [{"role": "user", "content": user_message}]
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,        # ← “文字が生成され次第すぐ送ってね” オプション
    )
    # 参考: https://platform.openai.com/docs/api-reference/chat/create

# ────────────────────────────────────────────────────────────────
# 5. イベントハンドラ群（Chainlit が自動的に呼んでくれる）
# ────────────────────────────────────────────────────────────────

@cl.on_chat_start
async def start():
    """チャットルーム生成直後：まずはモデル選択ボタンを提示"""
    await show_model_selection()

@cl.action_callback("change_model")
async def change_model(_action: cl.Action):
    """途中でもユーザが“モデル変更”ボタンを押したら呼ばれる"""
    await show_model_selection()

@cl.action_callback("select_model")
async def model_selected(action: cl.Action):
    """モデルボタンが押されたらモデル名をセッションに記録"""
    selected = action.payload["model"]            # ボタン側で埋めた値を取得
    cl.user_session.set("selected_model", selected)

    await cl.Message(
        content=f"{get_prefix()}✅ モデル「{selected}」を選択しました。質問をどうぞ！",
        actions=[
            cl.Action(name="save",          label="保存",        payload={"action": "save"}),
            cl.Action(name="change_model",  label="モデル変更",  payload={"action": "change_model"}),
        ],
    ).send()

@cl.action_callback("save")
async def save_history(_action: cl.Action):
    """「保存」ボタン → 履歴を JSON でダウンロード"""
    history = cl.user_session.get("chat_history", [])
    if not history:
        return

    out_dir = Path("chatlogs"); out_dir.mkdir(exist_ok=True)
    fp = out_dir / f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
    fp.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    await cl.Message(
        content="このチャネルでのやり取りを保存しました。",
        elements=[cl.File(name=fp.name, path=str(fp), display="inline")],
    ).send()

@cl.on_message
async def on_message(msg: cl.Message):
    """ユーザーがテキストを送るたびに実行されるメイン処理"""
    # 会話履歴をセッションから取り出し、今回の発言を追加
    history = cl.user_session.get("chat_history", [])
    history.append({"role": "user", "content": msg.content})

    model = cl.user_session.get("selected_model", "gpt-4o-mini")

    # 空メッセージを表示しておき、後で逐次 update()
    stream_msg = await cl.Message(content="").send()

    try:
        # OpenAI からストリーミング応答を受信
        stream = await ask_openai(msg.content, history, model)

        assistant_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                stream_msg.content += delta
                await stream_msg.update()

        history.append({"role": "assistant", "content": assistant_text})

    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {e}").send()

    finally:
        # 更新した履歴をセッションに戻す
        cl.user_session.set("chat_history", history)

        # 応答後、再度操作ボタンを表示
        await cl.Message(
            content="✅ 応答完了！次の操作を選んでください：そのままメッセージ送れば続けて回答します。",
            actions=[
                cl.Action(name="save",          label="保存",        payload={"action": "save"}),
                cl.Action(name="change_model",  label="モデル変更",  payload={"action": "change_model"}),
            ],
        ).send()

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""
