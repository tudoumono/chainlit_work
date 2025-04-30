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
7. **ファイル添付**: ファイルをアップロードして内容を分析
8. **画像処理**    : DALL-E画像生成と画像URLの表示機能
"""

# ────────────────────────────────────────────────────────────────
# 0. ライブラリの読み込み
# ────────────────────────────────────────────────────────────────
import os, json, sys
import base64
import re
import aiohttp
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

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
TEMP_DIR = os.path.join(EXE_DIR, "temp")  # ファイル一時保存用ディレクトリ
IMG_DIR = os.path.join(TEMP_DIR, "images")  # 画像保存用ディレクトリ

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
DALLE_MODEL = os.getenv("DALLE_MODEL", "dall-e-3")  # DALL-Eモデル設定

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
# 6. 画像生成と処理機能
# ────────────────────────────────────────────────────────────────
async def generate_image_dalle(prompt: str, size: str = "1024x1024", style: str = "vivid") -> Optional[str]:
    """
    DALL-E を使用して画像を生成する
    
    Args:
        prompt: 画像生成の指示テキスト
        size: 画像サイズ ("1024x1024", "1792x1024", "1024x1792" のいずれか)
        style: 画像スタイル ("vivid" または "natural")
        
    Returns:
        生成された画像のURL、もしくはエラー時はNone
    """
    if not client:
        return None
    
    try:
        response = await client.images.generate(
            model=DALLE_MODEL,
            prompt=prompt,
            size=size,
            quality="standard",
            style=style,
            n=1,
        )
        
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        print(f"DALL-E 画像生成エラー: {e}")
        return None

async def download_image(url: str) -> Optional[str]:
    """
    画像URLから画像をダウンロードし、一時ファイルとして保存する
    
    Args:
        url: 画像のURL
        
    Returns:
        保存された画像のパス、もしくはエラー時はNone
    """
    try:
        # ファイル名を生成
        file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = os.path.join(IMG_DIR, file_name)
        
        # 画像をダウンロード
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())
                    return file_path
                else:
                    print(f"画像ダウンロードエラー: ステータスコード {response.status}")
                    return None
    except Exception as e:
        print(f"画像ダウンロードエラー: {e}")
        return None

def extract_image_urls(text: str) -> List[str]:
    """
    テキストから画像URLを抽出する
    
    Args:
        text: 検索対象のテキスト
        
    Returns:
        抽出された画像URLのリスト
    """
    # 一般的な画像URLパターン
    url_pattern = r'https?://[^\s<>"]+\.(jpg|jpeg|png|gif|webp|bmp|svg)(?:\?[^\s<>"]*)?\b'
    # マークダウン画像記法
    md_pattern = r'!\[.*?\]\((https?://[^\s<>"]+\.(jpg|jpeg|png|gif|webp|bmp|svg)(?:\?[^\s<>"]*)?\b)\)'
    
    # 通常のURLを検索
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    # マークダウン記法からURLを抽出
    md_matches = re.findall(md_pattern, text, re.IGNORECASE)
    
    # 結果を結合
    all_urls = []
    for url in urls:
        if url.startswith(('http://', 'https://')):
            all_urls.append(url)
    
    for md_match in md_matches:
        if md_match[0].startswith(('http://', 'https://')):
            all_urls.append(md_match[0])
    
    return list(set(all_urls))  # 重複を除去

async def process_response_with_images(text: str) -> tuple[str, List]:
    """
    レスポンステキストから画像URLを抽出し、ダウンロードして表示用のエレメントを作成する
    
    Args:
        text: OpenAIからのレスポンステキスト
        
    Returns:
        処理されたテキストと画像エレメントのリスト
    """
    image_urls = extract_image_urls(text)
    elements = []
    
    if not image_urls:
        return text, elements
    
    for url in image_urls:
        # 画像をダウンロード
        image_path = await download_image(url)
        if image_path:
            # 画像エレメントを作成
            img_name = os.path.basename(image_path)
            elements.append(cl.Image(path=image_path, name=img_name, display="inline"))
            
            # テキスト内のURLをプレースホルダーに置き換える
            # マークダウン画像記法を検出して置換
            md_pattern = f'!\\[.*?\\]\\({re.escape(url)}\\)'
            if re.search(md_pattern, text):
                text = re.sub(md_pattern, f"[画像: {img_name}]", text)
            else:
                # 通常のURLを置換
                text = text.replace(url, f"[画像: {img_name}]")
    
    return text, elements

# ────────────────────────────────────────────────────────────────
# 7. OpenAI へ質問を投げる関数
# ────────────────────────────────────────────────────────────────
async def ask_openai(user_message: str,
                     history: list[dict],
                     model: str,
                     files: List[Dict[str, Any]] = None,
                     temperature: float = 0.7,
                     max_tokens: int = 1024):
    """
    * 普段:   OpenAI に問い合わせ、ストリーミングで返す
    * デバッグ: ダミー文字列を返す
    
    files: アップロードされたファイルのリスト (オプション)
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
    
    # ファイルがある場合はマルチモーダルメッセージに変換
    if files and model in ["gpt-4o", "gpt-4-vision"]:
        content_parts = []
        
        # テキストメッセージ部分
        content_parts.append({"type": "text", "text": user_message})
        
        # 画像ファイル部分
        for file_info in files:
            if file_info["type"].startswith("image/"):
                try:
                    with open(file_info["path"], "rb") as img_file:
                        base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file_info['type']};base64,{base64_image}"
                        }
                    })
                except Exception as e:
                    print(f"Error processing image {file_info['name']}: {e}")
        
        # 最後のメッセージを更新
        messages[-1] = {"role": "user", "content": content_parts}
    
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

# ────────────────────────────────────────────────────────────────
# 8. ファイル処理機能
# ────────────────────────────────────────────────────────────────
@cl.on_file_upload(accept=["text/plain", "application/pdf", "image/jpeg", "image/png"])
async def handle_file_upload(file: cl.File):
    """ファイルアップロードのハンドラ"""
    try:
        # ファイルの保存先パス
        file_path = os.path.join(TEMP_DIR, file.name)
        
        # ファイルの内容を保存
        content = await file.content()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # セッションにファイル情報を追加
        files = cl.user_session.get("files", [])
        file_info = {
            "name": file.name,
            "path": file_path,
            "type": file.mime,
            "size": len(content)
        }
        files.append(file_info)
        cl.user_session.set("files", files)
        
        # ファイルの種類に応じたメッセージ
        file_type_msg = ""
        if file.mime.startswith("image/"):
            file_type_msg = "画像ファイル"
        elif file.mime == "text/plain":
            file_type_msg = "テキストファイル"
        elif file.mime == "application/pdf":
            file_type_msg = "PDFファイル"
        else:
            file_type_msg = f"{file.mime}ファイル"
        
        # 成功メッセージの送信
        await cl.Message(
            content=f"✅ {file_type_msg}「{file.name}」をアップロードしました。\nこのファイルについて質問してください。",
        ).send()
        
    except Exception as e:
        # エラーメッセージの送信
        await cl.Message(content=f"❌ ファイルのアップロードに失敗しました: {str(e)}").send()

# ────────────────────────────────────────────────────────────────
# 9. 画像生成コマンド
# ────────────────────────────────────────────────────────────────
@cl.on_message(starts_with="/image")
async def handle_image_command(message: cl.Message):
    """
    /image コマンドを処理する
    形式: /image 描画したいものの説明
    
    オプション:
    --size=1024x1024 (1024x1024, 1792x1024, 1024x1792 のいずれか)
    --style=vivid (vivid または natural)
    """
    # コマンドの処理
    content = message.content.replace("/image", "", 1).strip()
    
    # オプションの抽出
    size = "1024x1024"
    style = "vivid"
    
    # サイズオプションの処理
    size_match = re.search(r'--size=(\S+)', content)
    if size_match:
        size_value = size_match.group(1)
        if size_value in ["1024x1024", "1792x1024", "1024x1792"]:
            size = size_value
        content = re.sub(r'--size=\S+', '', content).strip()
    
    # スタイルオプションの処理
    style_match = re.search(r'--style=(\S+)', content)
    if style_match:
        style_value = style_match.group(1).lower()
        if style_value in ["vivid", "natural"]:
            style = style_value
        content = re.sub(r'--style=\S+', '', content).strip()
    
    # プロンプトが空の場合
    if not content:
        await cl.Message(content="""
画像の説明を入力してください。例:
`/image 青い海と白い砂浜`

オプション:
`--size=1024x1024` (1024x1024, 1792x1024, 1024x1792 から選択)
`--style=vivid` (vivid または natural)
        """).send()
        return
    
    # 生成開始メッセージ
    await cl.Message(content=f"🎨 「{content}」の画像を生成しています...\nサイズ: {size}, スタイル: {style}").send()
    
    try:
        # 画像生成API呼び出し
        image_url = await generate_image_dalle(content, size, style)
        
        if image_url:
            # 画像ダウンロードと表示
            image_path = await download_image(image_url)
            
            if image_path:
                img_name = os.path.basename(image_path)
                elements = [cl.Image(path=image_path, name=img_name, display="inline")]
                
                await cl.Message(
                    content=f"✅ 画像が生成されました:\n**プロンプト**: {content}",
                    elements=elements
                ).send()
            else:
                await cl.Message(content="❌ 画像のダウンロードに失敗しました。").send()
        else:
            await cl.Message(content="❌ 画像の生成に失敗しました。").send()
    
    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {str(e)}").send()

# ────────────────────────────────────────────────────────────────
# 10. Chainlit イベントハンドラ
# ────────────────────────────────────────────────────────────────
@cl.on_chat_start
async def start():
    # 一時ディレクトリのクリーンアップ
    try:
        for file in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp directory: {e}")
    
    # セッション変数の初期化
    cl.user_session.set("files", [])
    
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
    await cl.Message(
        content="""✅ Chainlitを起動しました。

**利用可能な機能:**
- 画面左下のボタンからファイルをアップロードできます
- `/image [説明]` コマンドで画像を生成できます
  例: `/image 富士山と桜の風景 --size=1024x1024 --style=vivid`
""",
    ).send()
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
    # /imageコマンドは別のハンドラで処理
    if msg.content.startswith("/image") and not resume:
        return
    
    # -- 事前リセットと履歴処理 ------------------------------
    cl.user_session.set("cancel_flag", False)             # ★ 停止フラグを毎回リセット
    history = cl.user_session.get("chat_history", [])
    files = cl.user_session.get("files", [])
    
    if not resume:                                        # 本来のユーザ入力だけ履歴に残す
        history.append({"role": "user", "content": msg.content})
        cl.user_session.set("last_user_msg", msg.content) # ★ 再開用に保持

    model = cl.user_session.get("selected_model", "gpt-4o")

    # 空メッセージを作って、あとで逐次 update()
    stream_msg = await cl.Message(content="").send()

    try:
        # ファイル情報があればそれもコンテキストに含める
        user_message = msg.content
        if files and not resume:
            file_context = _generate_file_context(files)
            if file_context:
                # 履歴に表示される内容はオリジナルのまま
                # OpenAIに送信するメッセージにはファイル情報を付加
                user_message = f"{file_context}\n\n質問: {msg.content}"
        
        # OpenAIに問い合わせ
        stream = await ask_openai(user_message, history, model, files if model in ["gpt-4o", "gpt-4-vision"] else None)
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
            # テキスト内の画像URLを処理
            processed_text, image_elements = await process_response_with_images(assistant_text)
            
            # テキストと画像を含む応答を送信
            if image_elements and processed_text != assistant_text:
                # 元のメッセージを更新（画像URLをプレースホルダーに変更）
                stream_msg.content = processed_text
                await stream_msg.update()
                
                # 画像を含む追加メッセージを送信
                if image_elements:
                    await cl.Message(
                        content="以下は応答内で言及された画像です：",
                        elements=image_elements
                    ).send()
            
            # 履歴に保存（元のテキスト）
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
# 11. ユーティリティ関数
# ────────────────────────────────────────────────────────────────
def _generate_file_context(files: List[Dict[str, Any]]) -> str:
    """ファイルの内容からコンテキスト文字列を生成する"""
    if not files:
        return ""
    
    context = "以下のファイルに関する質問に回答してください：\n\n"
    
    for i, file_info in enumerate(files):
        context += f"【ファイル{i+1}】名前: {file_info['name']}, タイプ: {file_info['type']}\n"
        
        # テキストファイルの場合は内容を読み込む
        if file_info["type"] == "text/plain":
            try:
                with open(file_info["path"], "r", encoding="utf-8") as f:
                    content = f.read()
                    # 長すぎる場合は先頭部分のみ
                    if len(content) > 2000:
                        content = content[:2000] + "...(以下省略)..."
                    context += f"内容:\n{content}\n\n"
            except Exception as e:
                context += f"テキスト内容の読み込みに失敗: {str(e)}\n\n"
        # 画像ファイルの場合
        elif file_info["type"].startswith("image/"):
            if "gpt-4o" in cl.user_session.get("selected_model", ""):
                context += "(このファイルは画像データとして別途送信されます)\n\n"
            else:
                context += "※画像ファイルの内容を理解するには GPT-4o モデルを選択してください\n\n"
        # PDFなど、その他のファイル
        else:
            context += f"(このファイルタイプの内容は直接処理できません)\n\n"
    
    return context

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""