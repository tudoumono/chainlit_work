"""
main.py － Chainlit + OpenAI チャットアプリ
=========================================
このファイルを実行すると、ブラウザでチャット UI が立ち上がります。
利用者は「GPT‑3.5 / GPT‑4 / GPT‑4o」を途中でも自由に切り替えて対話できます。

--------------------------------------------------------------------------
💡 “ざっくり全体像”
--------------------------------------------------------------------------
1. **初期化**      : ユーザ設定(JSON)を読み込み（※ .env は読み込まない）
2. **モデル選択UI**: 起動時にボタンを表示（`show_model_selection()`）
3. **チャット処理**: ユーザー発言を受け取り、OpenAI へ問合せて返却
4. **履歴保存**    : 「保存」ボタンで JSON にエクスポート
5. **モデル変更**  : いつでも「モデル変更」ボタンで再選択できる
6. **停止・再開**  : ⏹ で生成中断、▶ で続きから再開
7. **設定⚙**      : API Key（パスワードマスク）と Debug モードの保存・反映

※ なるべく **非エンジニアでも読めるよう**、専門用語を噛み砕きつつ
   コード内コメントを多めに入れています。
"""

# ────────────────────────────────────────────────────────────────
# 0. ライブラリの読み込み
# ────────────────────────────────────────────────────────────────
import os, json
from datetime import datetime
from pathlib import Path

import chainlit as cl            # チャット UI フレームワーク
from openai import AsyncOpenAI   # OpenAI API 非同期クライアント

# ────────────────────────────────────────────────────────────────
# 1. ユーザ設定ファイルのロード／保存（.env は参照しない）
# ────────────────────────────────────────────────────────────────
# main.py のある場所をベースに .chainlit/config.toml を指定
CHAINLIT_CONFIG_PATH = Path(__file__).parent / ".chainlit" / "config.toml"
os.environ["CHAINLIT_CONFIG_PATH"] = str(CHAINLIT_CONFIG_PATH)
USER_SETTINGS_PATH = Path(".chainlit/client/user_settings.json")


def load_user_settings() -> dict:
    """JSON→dict。無い場合は空 dict"""
    try:
        return json.loads(USER_SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_user_settings(data: dict):
    """dict→JSON（UTF‑8, インデント 2）"""
    USER_SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

conf = load_user_settings()  # 設定読み込み

# ────────────────────────────────────────────────────────────────
# 2. 起動時設定（API Key / Debug モード）
# ────────────────────────────────────────────────────────────────
# 2‑A API Key
if key := conf.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = key   # OS 環境変数に即反映

# 2‑B Debug モード
def str2bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes")

DEBUG_MODE: bool = bool(conf.get("DEBUG_MODE", False))

# 2‑C API Key が無効なら強制 Debug
if not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
    DEBUG_MODE = True

# 2‑D OpenAI クライアント
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_prefix() -> str:
    return "🛠️【デバッグモード】\n" if DEBUG_MODE else ""

# ────────────────────────────────────────────────────────────────
# 3. モデル一覧
# ────────────────────────────────────────────────────────────────
MODELS = [
    ("GPT‑3.5 Turbo", "gpt-3.5-turbo"),
    ("GPT‑4 Turbo",   "gpt-4-turbo"),
    ("GPT‑4o",        "gpt-4o"),
]

# ────────────────────────────────────────────────────────────────
# 4. 共通アクション
# ────────────────────────────────────────────────────────────────
def common_actions(show_resume: bool = False):
    base = [
        cl.Action(name="save",      label="保存",          payload={"action": "save"}),
        cl.Action(name="change_model", label="モデル変更", payload={"action": "change_model"}),
        cl.Action(name="cancel",    label="⏹ 停止",        payload={"action": "cancel"}),
        cl.Action(name="shutdown",  label="🔴 プロセスを停止・終了",        payload={"action": "shutdown"}),
    ]
    if show_resume:
        base.append(cl.Action(name="resume", label="▶ 続き", payload={"action": "resume"}))
    return base

# ────────────────────────────────────────────────────────────────
# 5. モデル選択 UI
# ────────────────────────────────────────────────────────────────
async def show_model_selection():
    await cl.Message(
        content=f"{get_prefix()}🧠 使用するモデルを選んでください：",
        actions=[
            cl.Action(name="shutdown",  label="🔴 プロセスを停止・終了", payload={"action": "shutdown"}),
            *[cl.Action(name="select_model", label=label, payload={"model": val})
              for label, val in MODELS]
        ],
    ).send()

# ────────────────────────────────────────────────────────────────
# 6. OpenAI 呼び出し
# ────────────────────────────────────────────────────────────────
async def ask_openai(msg: str, history: list[dict], model: str,
                     temperature: float = 0.7, max_tokens: int = 1024):
    if DEBUG_MODE:
        async def dummy():
            for t in ["（デバッグ）", "これは ", "OpenAI を ", "呼び出して ", "いません。"]:
                yield type("Chunk", (), {
                    "choices": [type("Choice", (), {
                        "delta": type("Delta", (), {"content": t})()
                    })()]
                })()
        return dummy()

    messages = history + [{"role": "user", "content": msg}]
    return await client.chat.completions.create(
        model=model, messages=messages,
        temperature=temperature, max_tokens=max_tokens, stream=True
    )

# ────────────────────────────────────────────────────────────────
# 7. Chainlit イベントハンドラ
# ────────────────────────────────────────────────────────────────
@cl.on_chat_start
async def start(): await show_model_selection()

@cl.action_callback("change_model")
async def change_model(_): await show_model_selection()

@cl.action_callback("select_model")
async def model_selected(a: cl.Action):
    cl.user_session.set("selected_model", a.payload["model"])
    await cl.Message(
        content=f"{get_prefix()}✅ モデル「{a.payload['model']}」を選択しました。質問をどうぞ！",
        actions=common_actions(),
    ).send()

@cl.action_callback("cancel")
async def cancel(_):
    cl.user_session.set("cancel_flag", True)
    await cl.Message(content="⏹ 生成を停止します…",
                     actions=common_actions(show_resume=True)).send()

@cl.action_callback("resume")
async def resume(_):
    last = cl.user_session.get("last_user_msg")
    if last:
        await on_message(cl.Message(content="続きからお願いします。",
                                    author="user", id="resume"), resume=True)

@cl.action_callback("save")
async def save_hist(_):
    hist = cl.user_session.get("chat_history", [])
    if not hist: return
    out = Path("chatlogs"); out.mkdir(exist_ok=True)
    fp = out / f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
    fp.write_text(json.dumps(hist, indent=2, ensure_ascii=False), "utf-8")
    await cl.Message(content="やり取りを保存しました。",
                     elements=[cl.File(name=fp.name, path=str(fp), display="inline")]).send()

@cl.action_callback("shutdown")
async def shutdown(_):
    await cl.Message(content="🔴 サーバーを終了します…").send()
    await cl.sleep(0.1); os._exit(0)

# ★ 設定保存（API Key＋Debug）
@cl.action_callback("save_settings")
async def save_settings(a: cl.Action):
    global DEBUG_MODE, client
    payload = a.payload or {}
    conf.update({k:v for k,v in {
        "OPENAI_API_KEY": payload.get("key", "").strip() or conf.get("OPENAI_API_KEY", ""),
        "DEBUG_MODE":     payload.get("debug", DEBUG_MODE)
    }.items() if v not in ("", None)})

    # 即時反映
    if conf.get("OPENAI_API_KEY", "").startswith("sk-"):
        os.environ["OPENAI_API_KEY"] = conf["OPENAI_API_KEY"]
        client = AsyncOpenAI(api_key=conf["OPENAI_API_KEY"])
    else:
        DEBUG_MODE = True
    DEBUG_MODE = bool(conf.get("DEBUG_MODE", False)) or not os.getenv("OPENAI_API_KEY", "").startswith("sk-")

    save_user_settings(conf)
    await cl.Message(content="✅ 設定を保存しました").send()

# ――― メインメッセージハンドラ ―――
@cl.on_message
async def on_message(msg: cl.Message, resume: bool = False):
    cl.user_session.set("cancel_flag", False)
    hist = cl.user_session.get("chat_history", [])
    if not resume:
        hist.append({"role": "user", "content": msg.content})
        cl.user_session.set("last_user_msg", msg.content)

    model = cl.user_session.get("selected_model", "gpt-4o")
    stream_msg = await cl.Message(content="").send()

    try:
        stream = await ask_openai(msg.content, hist, model)
        assistant_text = ""
        async for chunk in stream:
            if cl.user_session.get("cancel_flag"): await stream.aclose(); break
            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                stream_msg.content += delta
                await stream_msg.update()
        if not cl.user_session.get("cancel_flag"):
            hist.append({"role": "assistant", "content": assistant_text})

    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {e}").send()

    finally:
        cl.user_session.set("chat_history", hist)
        await cl.Message(
            content="✅ 応答完了！次の操作を選んでください：",
            actions=common_actions(show_resume=cl.user_session.get("cancel_flag"))
        ).send()

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
"""
