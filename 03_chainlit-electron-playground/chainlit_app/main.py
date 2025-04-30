"""
main.py － Chainlit + OpenAI チャットアプリ
=========================================
このファイルを実行すると、ブラウザでチャット UI が立ち上がります。
利用者は「GPT‑3.5 / GPT‑4 / GPT‑4o」を途中でも自由に切り替えて対話できます。

--------------------------------------------------------------------------
💡 "ざっくり全体像"
--------------------------------------------------------------------------
1. **初期化**      : 環境変数を読み込み、OpenAI クライアントを作成
2. **モデル選択UI**: 起動時にボタンを表示（`show_model_selection()`）
3. **チャット処理**: ユーザー発言を受け取り、OpenAI へ問合せて返却
4. **履歴保存**    : 「保存」ボタンで TXT にエクスポート & 自動TXT保存機能追加
5. **モデル変更**  : いつでも「モデル変更」ボタンで再選択できる
6. **停止・再開**  : ⏹ で生成中断、▶ で続きから再開
"""

# ────────────────────────────────────────────────────────────────
# 0. ライブラリの読み込み
# ────────────────────────────────────────────────────────────────
import os, json, sys
from datetime import datetime
from pathlib import Path

# ▼ サードパーティ（外部）ライブラリ
from dotenv import load_dotenv, find_dotenv           # .env から変数を読むお手軽ユーティリティ
import chainlit as cl                    # チャットUIを超簡単に作れるフレームワーク
from openai import AsyncOpenAI           # OpenAI (GPT など) とやり取りする公式クライアント

# ────────────────────────────────────────────────────────────────
# 1. 初期設定とパス設定
# ────────────────────────────────────────────────────────────────
# Electronから渡されるEXE_DIRを取得（アプリケーションの実行ディレクトリ）
EXE_DIR = os.getenv("EXE_DIR", os.getcwd())

# 適切な .env ファイルを読み込む（優先順位: env/.env > .env）
ENV_PATH = os.path.join(EXE_DIR, "env", ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print(f"Loading .env from: {ENV_PATH}")
else:
    # 従来のパスをフォールバックとして使用
    load_dotenv(find_dotenv())
    print(f"Loading .env from default location")

# 各種ディレクトリパスの設定（環境変数から取得または既定値を使用）
CONSOLE_LOG_DIR = os.getenv("CONSOLE_LOG_DIR", os.path.join(EXE_DIR, "chainlit"))
CHAT_LOG_DIR = os.getenv("CHAT_LOG_DIR", os.path.join(EXE_DIR, "logs"))
TEMP_DIR = os.getenv("TEMP_DIR", os.path.join(EXE_DIR, "temp"))
IMG_DIR = os.getenv("IMG_DIR", os.path.join(TEMP_DIR, "images"))

# デバッグ出力
print(f"[DEBUG] EXE_DIR: {EXE_DIR}")
print(f"[DEBUG] ENV_PATH: {ENV_PATH}")
print(f"[DEBUG] CONSOLE_LOG_DIR: {CONSOLE_LOG_DIR}")
print(f"[DEBUG] CHAT_LOG_DIR: {CHAT_LOG_DIR}")
print(f"[DEBUG] TEMP_DIR: {TEMP_DIR}")
print(f"[DEBUG] IMG_DIR: {IMG_DIR}")

# ディレクトリが存在しない場合は作成
os.makedirs(CONSOLE_LOG_DIR, exist_ok=True)
os.makedirs(CHAT_LOG_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# 環境変数の読み込み
DEBUG_MODE = os.getenv("DEBUG_MODE") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# セッションID（チャット履歴の識別子）
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

# ここではクライアントの初期化はまだしない（APIキーがないかもしれないため）
client = None
if OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ────────────────────────────────────────────────────────────────
# 2. "どのGPTを使うか" のリスト定義
# ────────────────────────────────────────────────────────────────
MODELS = [
    ("GPT‑4.1 (高精度・長文処理)", "gpt-4.1"),                 # 一部アクセス制限あり
    ("GPT‑4o (マルチモーダル)", "gpt-4o"),                     # 音声・画像対応
    ("GPT‑4 (高性能)", "gpt-4"),                               # 旧バージョン
    ("GPT‑4-1106-preview (高速)", "gpt-4-1106-preview"),       # 推奨設定が多い
    ("GPT‑3.5 Turbo (コスト重視)", "gpt-3.5-turbo"),           # 最も一般的
    ("GPT‑3.5 Turbo 1106 (安定版)", "gpt-3.5-turbo-1106"),     # 安定動作
    ("GPT‑3.5 Turbo Instruct (単発応答)", "gpt-3.5-turbo-instruct")  # 単発指示
]
get_prefix = lambda: "🛠️【デバッグモード】\n" if DEBUG_MODE else ""

# ────────────────────────────────────────────────────────────────
# 3. チャット履歴の自動保存機能
# ────────────────────────────────────────────────────────────────
def save_chat_history_txt(history, is_manual=False):
    """
    チャット履歴をTXTファイルに保存する
    is_manual: 手動保存の場合はTrue（保存ボタンが押された場合）
    """
    if not history:
        return None
    
    # 出力ディレクトリはCHAT_LOG_DIRを使用
    out_dir = Path(CHAT_LOG_DIR)
    out_dir.mkdir(exist_ok=True)
    
    # ファイル名（自動保存と手動保存で区別）
    prefix = "manual" if is_manual else "auto"
    filename = f"{prefix}_chat_{SESSION_ID}.txt"
    filepath = out_dir / filename
    
    # チャット履歴をテキスト形式に変換
    lines = ["===== チャット履歴 =====", f"日時: {datetime.now():%Y/%m/%d %H:%M:%S}", ""]
    
    for i, msg in enumerate(history):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 役割に応じて整形（ユーザーとアシスタントを分かりやすく）
        if role == "user":
            lines.append(f"👤 ユーザー（質問 {i//2+1}）:")
        elif role == "assistant":
            lines.append(f"🤖 AI（回答 {i//2+1}）:")
        else:
            lines.append(f"📝 {role}:")
        
        # 内容を追加（インデント付き）
        for line in content.split("\n"):
            lines.append(f"  {line}")
        
        # メッセージ間に空行を入れる
        lines.append("")
    
    # ファイルに書き込む
    filepath.write_text("\n".join(lines), encoding="utf-8")
    
    return filepath

# ────────────────────────────────────────────────────────────────
# 4. 共通アクション（保存・モデル変更・停止・再開）
# ────────────────────────────────────────────────────────────────
def common_actions(show_resume: bool = False):
    """画面下に並べるボタンを共通関数で管理（DRY）"""
    base = [
        cl.Action(name="save",          label="保存",        payload={"action": "save"}),
        cl.Action(name="change_model",  label="モデル変更",  payload={"action": "change_model"}),
        cl.Action(name="cancel",        label="⏹ 停止",      payload={"action": "cancel"}),
        cl.Action(name="shutdown",      label="🔴 プロセス完全終了", payload={"action": "shutdown"}),
    ]
    # 停止後にだけ「▶ 続き」ボタンを出す
    if show_resume:
        base.append(cl.Action(name="resume", label="▶ 続き", payload={"action": "resume"}))
    return base

# ────────────────────────────────────────────────────────────────
# 5. モデル選択UI
# ────────────────────────────────────────────────────────────────
async def show_model_selection():
    await cl.Message(
        content=f"{get_prefix()}🧠 使用するモデルを選んでください：",
        actions=[
            cl.Action(name="select_model", label=label, payload={"model": val})
            for label, val in MODELS
        ],
    ).send()

# ────────────────────────────────────────────────────────────────
# 6. OpenAI へ質問を投げる関数
# ────────────────────────────────────────────────────────────────
async def ask_openai(user_message: str,
                     history: list[dict],
                     model: str,
                     temperature: float = 0.7,
                     max_tokens: int = 1024):
    """
    * 普段:   OpenAI に問い合わせ、ストリーミングで返す
    * デバッグ: ダミー文字列を返す
    """
    if DEBUG_MODE:
        async def fake_stream():
            for chunk in ["（デバッグ）", "これは ", "OpenAI を ", "呼び出して ", "いません。"]:
                yield type("Chunk", (), {
                    "choices": [type("Choice", (), {
                        "delta": type("Delta", (), {"content": chunk})()
                    })()]
                })()
        return fake_stream()

    messages = history + [{"role": "user", "content": user_message}]
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

# ────────────────────────────────────────────────────────────────
# 7. ファイル処理機能
# ────────────────────────────────────────────────────────────────
async def process_uploaded_files(files):
    """アップロードされたファイルを処理する関数"""
    results = []
    
    for file in files:
        file_info = {
            "name": file.name,
            "mime": file.mime,
            "size": os.path.getsize(file.path) if os.path.exists(file.path) else 0,
            "path": file.path,
        }
        
        # ファイルタイプに応じた処理
        if "text/plain" in file.mime:
            try:
                with open(file.path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # テキストファイルの内容を表示（長すぎる場合は省略）
                    summary = content[:500] + "..." if len(content) > 500 else content
                    file_info["summary"] = summary
            except Exception as e:
                file_info["error"] = f"テキストファイル読み込みエラー: {str(e)}"
        
        elif "application/pdf" in file.mime:
            file_info["summary"] = "PDFファイルがアップロードされました。"
            # PDFパーサーがある場合は、ここでPDFの内容を抽出することもできます
        
        elif "image/" in file.mime:
            # 画像ファイルの処理
            # 一時ディレクトリに保存するなどの処理を行う
            file_info["summary"] = "画像ファイルがアップロードされました。"
        
        results.append(file_info)
    
    return results

# ────────────────────────────────────────────────────────────────
# 8. Chainlit イベントハンドラ
# ────────────────────────────────────────────────────────────────
@cl.on_chat_start
async def start():
    if not OPENAI_API_KEY:
        # 🔽 UI側に警告を表示
        await cl.Message(
            content="❌ **OpenAI APIキーが設定されていません！**\n"
                    "`.env` ファイルに以下のように設定してください：\n"
                    "`OPENAI_API_KEY=\"sk-xxxx...\"`\n"
                    "（デバッグ）これは OpenAI を 呼び出して いません。\n"
                    "質問を入力してください。\n"
                    ,
            actions=common_actions(),
        ).send()
        return

    # ✅ 通常の開始処理
    await show_model_selection()

@cl.action_callback("change_model")
async def change_model(_):
    await show_model_selection()

@cl.action_callback("select_model")
async def model_selected(action: cl.Action):
    cl.user_session.set("selected_model", action.payload["model"])
    await cl.Message(
        content=f"{get_prefix()}✅ モデル「{action.payload['model']}」を選択しました。質問をどうぞ！",
        actions=common_actions(),
    ).send()

# ★ 停止ボタン
@cl.action_callback("cancel")
async def cancel_stream(_):
    cl.user_session.set("cancel_flag", True)
    await cl.Message(content="⏹ 生成を停止します…", actions=common_actions(show_resume=True)).send()

# ★ 再開ボタン
@cl.action_callback("resume")
async def resume_stream(_):
    last_user_msg = cl.user_session.get("last_user_msg")
    if not last_user_msg:
        await cl.Message(content="再開できる会話が見つかりません。").send()
        return
    # 「続きからお願いします」を追加して再度 ask_openai
    await on_message(cl.Message(content="続きからお願いします。", author="user", id="resume"), resume=True)

# ★ 保存ボタン（TXTフォーマットのみ）
@cl.action_callback("save")
async def save_history(_):
    history = cl.user_session.get("chat_history", [])
    if not history:
        return
    
    # JSON形式での保存はコメントアウト
    # out_dir = Path(CHAT_LOG_DIR)
    # out_dir.mkdir(exist_ok=True)
    # json_fp = out_dir / f"manual_chat_{SESSION_ID}.json"
    # json_fp.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # TXT形式で保存
    txt_fp = save_chat_history_txt(history, is_manual=True)
    
    # 保存したファイルを表示
    elements = [
        cl.File(name=txt_fp.name, path=str(txt_fp), display="inline", 
                mime="text/plain", description="テキスト形式（読みやすい形式）")
    ]
    
    await cl.Message(
        content=f"このチャネルでのやり取りを保存しました。\n保存先: {CHAT_LOG_DIR}",
        elements=elements
    ).send()

# ★ プロセス完全終了ボタン
@cl.action_callback("shutdown")
async def shutdown_app(_):
    await cl.Message(content="🔴 サーバーを終了します…").send()
    await cl.sleep(0.1)           # メッセージ送信猶予
    os._exit(0)                   # 即プロセス終了（SystemExitを無視して強制終了）

# メインのメッセージハンドラ
@cl.on_message
async def on_message(msg: cl.Message, resume: bool = False):
    """
    resume=True のときは「続きからお願いします」などの内部呼び出し用
    """
    # -- 事前リセットと履歴処理 ------------------------------
    cl.user_session.set("cancel_flag", False)             # ★ 停止フラグを毎回リセット
    history = cl.user_session.get("chat_history", [])
    if not resume:                                        # 本来のユーザ入力だけ履歴に残す
        history.append({"role": "user", "content": msg.content})
        cl.user_session.set("last_user_msg", msg.content) # ★ 再開用に保持

    model = cl.user_session.get("selected_model", "gpt-4o")

    # -- ファイルの処理 --------------------------------------
    # メッセージに添付されたファイルを処理
    if msg.elements and not resume:
        # ファイルをフィルタリング
        files = [elem for elem in msg.elements if hasattr(elem, 'path') and hasattr(elem, 'mime')]
        
        if files:
            # 処理中メッセージを表示
            processing_msg = await cl.Message(content=f"📂 {len(files)}個のファイルを処理中...").send()
            
            try:
                # ファイルを処理
                file_results = await process_uploaded_files(files)
                
                # 処理結果メッセージを作成
                file_info = [f"**{result['name']}** ({result['mime']})" for result in file_results]
                file_summary = "\n".join(file_info)
                
                # Message.update()にはcontent引数は使わず、直接新しい内容を渡す
                processing_msg.content = f"📂 ファイルを受け取りました：\n{file_summary}"
                await processing_msg.update()
                
                # 必要に応じてファイルの内容を表示するための要素を作成
                elements = []
                for result in file_results:
                    if "text/plain" in result['mime'] and "summary" in result:
                        # テキストファイルの内容を表示要素として追加
                        elements.append(
                            cl.Text(
                                name=f"contents_{result['name']}",
                                content=result.get("summary", "内容を表示できません"),
                                display="side"
                            )
                        )
                
                if elements:
                    await cl.Message(
                        content="📄 アップロードされたテキストファイルの内容：",
                        elements=elements
                    ).send()
                
                # ユーザーメッセージにファイル情報を追加
                file_info_for_ai = "\n".join([
                    f"[ファイル {i+1}]: {result['name']} ({result['mime']})"
                    for i, result in enumerate(file_results)
                ])
                
                # 履歴のユーザーメッセージを更新（ファイル情報を追加）
                if history:
                    history[-1]["content"] = f"{msg.content}\n\n添付ファイル情報:\n{file_info_for_ai}"
                
            except Exception as e:
                # エラー処理も同様に修正
                processing_msg.content = f"❌ ファイル処理中にエラーが発生しました: {str(e)}"
                await processing_msg.update()

    # 空メッセージを作って、あとで逐次 update()
    stream_msg = await cl.Message(content="").send()

    try:
        stream = await ask_openai(msg.content, history, model)
        assistant_text = ""

        async for chunk in stream:
            # ★ 停止ボタンが押されたら break
            if cl.user_session.get("cancel_flag"):
                await stream.aclose()     # ストリームを閉じて即終了
                break

            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                stream_msg.content += delta
                await stream_msg.update()

        if not cl.user_session.get("cancel_flag"):
            history.append({"role": "assistant", "content": assistant_text})
            
            # 自動保存機能
            save_chat_history_txt(history)

    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {e}").send()

    finally:
        cl.user_session.set("chat_history", history)

        # ★ 停止された場合は ▶ ボタンを表示、それ以外は通常ボタン
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
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""