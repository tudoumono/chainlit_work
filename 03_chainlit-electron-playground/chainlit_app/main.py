"""
main.py － Chainlit + OpenAI チャットアプリ
=========================================
このファイルを実行すると、ブラウザでチャット UI が立ち上がります。
利用者は「GPT‑3.5 / GPT‑4 / GPT‑4o」を途中でも自由に切り替えて対話できます。

追加機能:
- 複数ファイル形式対応（PDF、Excel、Word、PowerPoint、画像、Markdown、テキスト）
- アップロードファイルの処理と表示

--------------------------------------------------------------------------
💡 "ざっくり全体像"
--------------------------------------------------------------------------
1. **初期化**      : 環境変数を読み込み、OpenAI クライアントを作成
2. **モデル選択UI**: 起動時にボタンを表示（`show_model_selection()`）
3. **チャット処理**: ユーザー発言を受け取り、OpenAI へ問合せて返却
4. **履歴保存**    : 「保存」ボタンで TXT にエクスポート & 自動TXT保存機能追加
5. **モデル変更**  : いつでも「モデル変更」ボタンで再選択できる
6. **停止・再開**  : ⏹ で生成中断、▶ で続きから再開
7. **ファイル処理** : 各種ファイル形式のアップロード・表示・処理
"""

# ────────────────────────────────────────────────────────────────
# 0. ライブラリの読み込み
# ────────────────────────────────────────────────────────────────
import os, json, sys
from datetime import datetime
from pathlib import Path
import shutil

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
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(EXE_DIR, "uploads"))  # アップロードディレクトリを追加

# デバッグ出力
print(f"[DEBUG] EXE_DIR: {EXE_DIR}")
print(f"[DEBUG] ENV_PATH: {ENV_PATH}")
print(f"[DEBUG] CONSOLE_LOG_DIR: {CONSOLE_LOG_DIR}")
print(f"[DEBUG] CHAT_LOG_DIR: {CHAT_LOG_DIR}")
print(f"[DEBUG] UPLOADS_DIR: {UPLOADS_DIR}")

# ディレクトリが存在しない場合は作成
os.makedirs(CONSOLE_LOG_DIR, exist_ok=True)
os.makedirs(CHAT_LOG_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)  # アップロードディレクトリを作成

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
# 2. ファイル処理関連の設定
# ────────────────────────────────────────────────────────────────
# MIMEタイプの定義（受け付けるファイル形式）
ACCEPTED_MIME_TYPES = {
    # テキスト系
    "text/plain": [".txt", ".log", ".py", ".js", ".html", ".css", ".json", ".xml", ".csv"],
    "text/markdown": [".md", ".markdown"],
    # オフィス系
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "application/vnd.ms-excel": [".xls"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
    "application/vnd.ms-powerpoint": [".ppt"],
    # 画像系
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
    "image/svg+xml": [".svg"],
}

# ファイルタイプに応じた表示名を取得
def get_file_type_name(mime_type):
    """MIMEタイプからユーザーフレンドリーなファイルタイプ名を返す"""
    if "text/plain" in mime_type:
        return "テキストファイル"
    elif "text/markdown" in mime_type:
        return "Markdownファイル"
    elif "application/pdf" in mime_type:
        return "PDFファイル"
    elif "spreadsheet" in mime_type or "excel" in mime_type:
        return "Excelファイル"
    elif "wordprocessing" in mime_type or "msword" in mime_type:
        return "Wordファイル"
    elif "presentation" in mime_type or "powerpoint" in mime_type:
        return "PowerPointファイル"
    elif "image" in mime_type:
        return "画像ファイル"
    else:
        return "ファイル"

# アップロードされたファイルを処理する関数の修正版
async def process_uploaded_file(file):
    """アップロードされたファイルを処理し、表示用の情報を返す"""
    try:
        # ファイル情報を取得（新しいAPIに対応）
        file_name = file.name
        file_path = file.path
        file_size = os.path.getsize(file_path) / 1024  # KBに変換
        
        # MIMEタイプを拡張子から推測
        file_extension = os.path.splitext(file_name)[1].lower()
        mime_type = get_mime_from_extension(file_extension)
        file_type = get_file_type_name(mime_type)
        
        # アップロードディレクトリに保存（永続化）
        saved_path = os.path.join(UPLOADS_DIR, file_name)
        shutil.copy2(file_path, saved_path)
        
        # 処理結果を返す
        return {
            "success": True,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": f"{file_size:.2f} KB",
            "mime_type": mime_type,
            "path": saved_path
        }
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "file_name": getattr(file, "name", "不明なファイル")
        }

# 拡張子からMIMEタイプを推測する関数
def get_mime_from_extension(extension):
    """ファイル拡張子からMIMEタイプを推測する"""
    extension = extension.lower()
    
    # テキスト系
    if extension in ['.txt', '.log']:
        return "text/plain"
    elif extension == '.md':
        return "text/markdown"
    elif extension == '.csv':
        return "text/csv"
    elif extension == '.py':
        return "text/x-python"
    elif extension == '.js':
        return "application/javascript"
    elif extension == '.html':
        return "text/html"
    elif extension == '.css':
        return "text/css"
    elif extension == '.json':
        return "application/json"
    elif extension == '.xml':
        return "application/xml"
    
    # オフィス系
    elif extension == '.pdf':
        return "application/pdf"
    elif extension == '.xlsx':
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif extension == '.xls':
        return "application/vnd.ms-excel"
    elif extension == '.docx':
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif extension == '.doc':
        return "application/msword"
    elif extension == '.pptx':
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif extension == '.ppt':
        return "application/vnd.ms-powerpoint"
    
    # 画像系
    elif extension == '.png':
        return "image/png"
    elif extension in ['.jpg', '.jpeg']:
        return "image/jpeg"
    elif extension == '.gif':
        return "image/gif"
    elif extension == '.webp':
        return "image/webp"
    elif extension == '.svg':
        return "image/svg+xml"
    
    # 不明な場合
    else:
        return "application/octet-stream"

# ファイルをUIに表示する関数
async def display_file_in_ui(file_info):
    """ファイルタイプに応じた適切なUI要素を作成"""
    elements = []
    mime_type = file_info["mime_type"]
    file_path = file_info["path"]
    
    # ファイルタイプに応じて適切なUIを選択
    try:
        # PDFを表示
        if "application/pdf" in mime_type:
            elements.append(
                cl.Pdf(name=f"pdf_{file_info['file_name']}", path=file_path, display="side")
            )
        # 画像を表示
        elif "image" in mime_type:
            elements.append(
                cl.Image(name=f"img_{file_info['file_name']}", path=file_path, display="inline")
            )
        # テキスト系ファイルを表示（プレーンテキストとMarkdown）
        elif any(txt in mime_type for txt in ["text/plain", "text/markdown", "text/csv"]):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                # 言語を識別（拡張子から）
                lang = None
                if file_path.endswith(".py"):
                    lang = "python"
                elif file_path.endswith(".js"):
                    lang = "javascript"
                elif file_path.endswith(".md"):
                    lang = "markdown"
                elif file_path.endswith(".json"):
                    lang = "json"
                
                elements.append(
                    cl.Text(
                        name=f"text_{file_info['file_name']}",
                        content=content,
                        language=lang,
                        display="side"
                    )
                )
            except Exception as e:
                # テキスト表示に失敗した場合はファイルダウンロード用のリンクを提供
                print(f"Error displaying text: {str(e)}")
                elements.append(
                    cl.File(name=file_info["file_name"], path=file_path)
                )
        # その他のファイルはダウンロードリンクとして提供
        else:
            elements.append(
                cl.File(name=file_info["file_name"], path=file_path)
            )
    except Exception as e:
        print(f"Error creating UI element: {str(e)}")
        # エラー時はファイルダウンロード用のリンクを提供
        elements.append(
            cl.File(name=file_info["file_name"], path=file_path)
        )
    
    return elements

# ────────────────────────────────────────────────────────────────
# 3. "どのGPTを使うか" のリスト定義
# ────────────────────────────────────────────────────────────────
# chainlit_select_models.py
MODELS = [
    ("GPT-4.1（高精度・長文）", "gpt-4.1"),
    ("GPT-4o（マルチモーダル）", "gpt-4o"),
    ("GPT-4", "gpt-4"),
    ("GPT-4-1106-preview（※5月廃止）", "gpt-4-1106-preview"),
    ("GPT-3.5 Turbo", "gpt-3.5-turbo"),
    ("GPT-3.5 Turbo 1106", "gpt-3.5-turbo-1106"),
    ("GPT-3.5 Turbo Instruct", "gpt-3.5-turbo-instruct"),
]

get_prefix = lambda: "🛠️【デバッグモード】\n" if DEBUG_MODE else ""

# ────────────────────────────────────────────────────────────────
# 4. チャット履歴の自動保存機能
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
            lines.append(f"ユーザー（質問 {i//2+1}）:")
        elif role == "assistant":
            lines.append(f"AI（回答 {i//2+1}）:")
        else:
            lines.append(f"{role}:")
        
        # 内容を追加（インデント付き）
        for line in content.split("\n"):
            lines.append(f"  {line}")
        
        # メッセージ間に空行を入れる
        lines.append("")
    
    # ファイルに書き込む
    filepath.write_text("\n".join(lines), encoding="utf-8")
    
    return filepath

# ────────────────────────────────────────────────────────────────
# 5. 共通アクション（保存・モデル変更・停止・再開・ファイルアップロード）
# ────────────────────────────────────────────────────────────────
def common_actions(show_resume: bool = False, show_upload: bool = True):
    """画面下に並べるボタンを共通関数で管理（DRY）"""
    base = [
        cl.Action(name="save",          label="保存",        payload={"action": "save"}),
        cl.Action(name="change_model",  label="モデル変更",  payload={"action": "change_model"}),
        cl.Action(name="cancel",        label="停止",      payload={"action": "cancel"}),
        cl.Action(name="shutdown",      label="プロセス完全終了", payload={"action": "shutdown"}),
    ]
    
    # ファイルアップロードボタンを追加
    if show_upload:
        base.append(cl.Action(name="upload_file", label="ファイルをアップロード", payload={"action": "upload_file"}))
    
    # 停止後にだけ「続き」ボタンを出す
    if show_resume:
        base.append(cl.Action(name="resume", label="続き", payload={"action": "resume"}))
    
    return base

# ────────────────────────────────────────────────────────────────
# 6. モデル選択UI
# ────────────────────────────────────────────────────────────────
async def show_model_selection():
    await cl.Message(
        content=f"{get_prefix()}使用するモデルを選んでください：",
        actions=[
            cl.Action(name="select_model", label=label, payload={"model": val})
            for label, val in MODELS
        ],
    ).send()

# ────────────────────────────────────────────────────────────────
# 7. OpenAI へ質問を投げる関数
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
# 8. Chainlit イベントハンドラ
# ────────────────────────────────────────────────────────────────
@cl.on_chat_start
async def start():
    # ファイル・会話履歴のための辞書を初期化
    cl.user_session.set("uploaded_files", [])
    cl.user_session.set("chat_history", [])
    
    if not OPENAI_API_KEY:
        # 🔽 UI側に警告を表示
        await cl.Message(
            content="**OpenAI APIキーが設定されていません！**\n"
                    "`.env` ファイルに以下のように設定してください：\n"
                    "`OPENAI_API_KEY=\"sk-xxxx...\"`\n"
                    "（デバッグ）これは OpenAI を 呼び出して いません。\n"
                    "質問を入力してください。\n"
                    ,
            actions=common_actions(),
        ).send()
        return

    # ✅ 通常の開始処理
    await cl.Message(
        content=f"{get_prefix()}AIチャットアプリへようこそ！\n"
                "以下の機能が利用できます：\n"
                "・チャットでの質問応答\n"
                "・各種ファイルのアップロード（PDF, Excel, Word, PowerPoint, 画像, Markdown, テキスト）\n"
                "・ファイルに関する質問応答\n",
        actions=common_actions()
    ).send()
    
    # モデル選択UIを表示
    await show_model_selection()

# モデル変更ボタン
@cl.action_callback("change_model")
async def change_model(_):
    await show_model_selection()

# モデル選択アクション
@cl.action_callback("select_model")
async def model_selected(action: cl.Action):
    cl.user_session.set("selected_model", action.payload["model"])
    await cl.Message(
        content=f"{get_prefix()}モデル「{action.payload['model']}」を選択しました。質問をどうぞ！",
        actions=common_actions(),
    ).send()

# ファイルアップロードボタン - エラーを修正
@cl.action_callback("upload_file")
async def upload_file_action(_):
    """ファイルアップロードダイアログを表示"""
    # ファイルアップロードダイアログを表示
    files = await cl.AskFileMessage(
        content="処理したいファイルをアップロードしてください：",
        accept=ACCEPTED_MIME_TYPES,
        max_size_mb=20,  # 最大ファイルサイズ（MB）
        max_files=5,     # 最大ファイル数
        timeout=300,     # タイムアウト（秒）
    ).send()
    
    if not files:
        await cl.Message(content="ファイルがアップロードされませんでした。").send()
        return
    
    # 処理中メッセージ
    processing_msg = await cl.Message(content="ファイルを処理中...").send()
    
    # アップロードされたファイルを処理
    uploaded_files = cl.user_session.get("uploaded_files", [])
    
    for file in files:
        file_info = await process_uploaded_file(file)
        
        if file_info["success"]:
            # ファイルをセッションに追加
            uploaded_files.append(file_info)
            
            # UIに表示する要素を作成
            elements = await display_file_in_ui(file_info)
            
            # 処理結果メッセージを表示
            await cl.Message(
                content=f"**{file_info['file_name']}** をアップロードしました\n"
                        f"種類: {file_info['file_type']}\n"
                        f"サイズ: {file_info['file_size']}",
                elements=elements
            ).send()
        else:
            # エラーメッセージを表示
            await cl.Message(
                content=f"**{file_info['file_name']}** の処理中にエラーが発生しました：\n{file_info['error']}"
            ).send()
    
    # セッションを更新
    cl.user_session.set("uploaded_files", uploaded_files)
    
    # 処理完了メッセージ - Message.update()は正しく使用
    await processing_msg.send()  # 既存のメッセージを更新する代わりに新しいメッセージを送信
    await cl.Message(content=f"{len(files)}個のファイルの処理が完了しました！").send()
    
    # ファイル一覧メッセージを表示
    if uploaded_files:
        file_list = "\n".join([f"- {f['file_name']}" for f in uploaded_files])
        await cl.Message(
            content=f"**アップロード済みのファイル一覧**：\n{file_list}\n\nこれらのファイルについて質問できます。",
            actions=common_actions()
        ).send()

# ★ 停止ボタン
@cl.action_callback("cancel")
async def cancel_stream(_):
    cl.user_session.set("cancel_flag", True)
    await cl.Message(content="生成を停止します...", actions=common_actions(show_resume=True)).send()

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
    await cl.Message(content="サーバーを終了します...").send()
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

    # ファイル添付があるか確認
    if msg.elements and not resume:
        # 処理中メッセージを表示
        await cl.Message(content="ファイルを処理中...").send()
        
        # アップロードされたファイルを処理
        uploaded_files = cl.user_session.get("uploaded_files", [])
        
        for file in msg.elements:
            file_info = await process_uploaded_file(file)
            
            if file_info["success"]:
                # ファイルをセッションに追加
                uploaded_files.append(file_info)
                
                # UIに表示する要素を作成
                elements = await display_file_in_ui(file_info)
                
                # 処理結果メッセージを表示
                await cl.Message(
                    content=f"**{file_info['file_name']}** をアップロードしました\n"
                            f"種類: {file_info['file_type']}\n"
                            f"サイズ: {file_info['file_size']}",
                    elements=elements
                ).send()
            else:
                # エラーメッセージを表示
                await cl.Message(
                    content=f"**{file_info['file_name']}** の処理中にエラーが発生しました：\n{file_info['error']}"
                ).send()
        
        # セッションを更新
        cl.user_session.set("uploaded_files", uploaded_files)

    model = cl.user_session.get("selected_model", "gpt-4o")

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
                stream_msg.content = stream_msg.content + delta  # 正しい更新方法
                await stream_msg.update()

        if not cl.user_session.get("cancel_flag"):
            history.append({"role": "assistant", "content": assistant_text})
            
            # 自動保存機能
            save_chat_history_txt(history)

    except Exception as e:
        await cl.Message(content=f"エラーが発生しました: {e}").send()

    finally:
        cl.user_session.set("chat_history", history)

        # ★ 停止された場合は ▶ ボタンを表示、それ以外は通常ボタン
        await cl.Message(
            content="応答完了！次の操作を選んでください：",
            actions=common_actions(show_resume=cl.user_session.get("cancel_flag"))
        ).send()

# ────────────────────────────────────────────────────────────────
# 9. ファイル内容からの質問応答機能（シンプル版）
# ────────────────────────────────────────────────────────────────
async def get_file_content_for_query(file_path):
    """ファイルの内容をテキストとして抽出（シンプルなバージョン）"""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # テキスト系ファイルは直接読み込み
        if file_extension in ['.txt', '.log', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        
        # PDFやOffice系ファイルは複雑なため、簡易的な説明を返す
        file_types = {
            '.pdf': 'PDFファイル',
            '.docx': 'Wordファイル', 
            '.doc': 'Wordファイル',
            '.xlsx': 'Excelファイル',
            '.xls': 'Excelファイル',
            '.pptx': 'PowerPointファイル',
            '.ppt': 'PowerPointファイル',
        }
        
        if file_extension in file_types:
            return f"これは{file_types[file_extension]}です。内容を確認するには高度なパーサーが必要です。"
        
        # 画像ファイルの場合
        if file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']:
            return "これは画像ファイルです。画像解析機能が必要です。"
        
        return f"このファイル形式({file_extension})の内容を直接抽出することはできません。"
    
    except Exception as e:
        return f"ファイル読み込みエラー: {str(e)}"

# ファイルに関する質問を処理する関数（OpenAIに直接問い合わせるシンプル版）
async def process_file_query(user_message, uploaded_files):
    """アップロードされたファイルに関する質問を処理する"""
    if not uploaded_files:
        return "アップロードされたファイルがありません。まず「ファイルをアップロード」ボタンからファイルをアップロードしてください。"
    
    # ファイル一覧の情報を収集
    file_info = []
    for file in uploaded_files:
        file_info.append(f"ファイル名: {file['file_name']}, 種類: {file['file_type']}")
    
    # ファイル一覧をマークダウンで整形
    file_list = "\n".join([f"- {info}" for info in file_info])
    
    # ユーザーの質問にファイル名が含まれているか確認
    mentioned_files = []
    for file in uploaded_files:
        if file['file_name'].lower() in user_message.lower():
            mentioned_files.append(file)
    
    # 言及されたファイルがなければ、すべてのファイルを対象とする
    target_files = mentioned_files if mentioned_files else uploaded_files
    
    # ファイル内容を収集
    file_contents = []
    for file in target_files:
        content = await get_file_content_for_query(file['path'])
        file_contents.append(f"--- {file['file_name']} ---\n{content}")
    
    # ファイル内容を結合
    combined_content = "\n\n".join(file_contents)
    
    # OpenAIに問い合わせるためのプロンプト作成
    prompt = f"""
ユーザーから以下の質問がありました:
"{user_message}"

以下のファイルが提供されています:
{file_list}

ファイルの内容:
{combined_content}

上記のファイルの内容に基づいて、ユーザーの質問に答えてください。
ファイルから得られる情報だけを使用し、わからない場合は正直に「この情報からはわかりません」と答えてください。
"""
    
    return prompt

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""