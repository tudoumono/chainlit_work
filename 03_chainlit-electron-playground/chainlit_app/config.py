"""
config.py - 設定と初期化モジュール
===============================
環境変数の読み込み、パスの設定、初期化処理を行います。
"""

import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# ディレクトリパス関連の設定
def setup_environment():
    """環境変数とディレクトリパスの設定"""
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
    UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(EXE_DIR, "uploads"))

    # デバッグ出力
    print(f"[DEBUG] EXE_DIR: {EXE_DIR}")
    print(f"[DEBUG] ENV_PATH: {ENV_PATH}")
    print(f"[DEBUG] CONSOLE_LOG_DIR: {CONSOLE_LOG_DIR}")
    print(f"[DEBUG] CHAT_LOG_DIR: {CHAT_LOG_DIR}")
    print(f"[DEBUG] UPLOADS_DIR: {UPLOADS_DIR}")

    # ディレクトリが存在しない場合は作成
    os.makedirs(CONSOLE_LOG_DIR, exist_ok=True)
    os.makedirs(CHAT_LOG_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # 環境変数の読み込み
    DEBUG_MODE = os.getenv("DEBUG_MODE") == "1"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # APIキーのバリデーション
    API_KEY_VALID = validate_api_key(OPENAI_API_KEY)
    
    # 検証結果をログに出力
    if API_KEY_VALID:
        print(f"[INFO] OpenAI API key validation: OK")
    else:
        print(f"[WARNING] OpenAI API key validation: INVALID or MISSING")

    # セッションID（チャット履歴の識別子）
    SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 設定をまとめて返す
    return {
        "EXE_DIR": EXE_DIR,
        "ENV_PATH": ENV_PATH,
        "CONSOLE_LOG_DIR": CONSOLE_LOG_DIR,
        "CHAT_LOG_DIR": CHAT_LOG_DIR,
        "UPLOADS_DIR": UPLOADS_DIR,
        "DEBUG_MODE": DEBUG_MODE,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "API_KEY_VALID": API_KEY_VALID,
        "SESSION_ID": SESSION_ID
    }

# デバッグモード用のプレフィックス
def get_prefix(debug_mode=False):
    """デバッグモード用のプレフィックスを返す"""
    return "🛠️【デバッグモード】\n" if debug_mode else ""

def validate_api_key(api_key):
    """APIキーの形式を検証する（改良版）"""
    if not api_key:
        return False
    
    # OpenAI APIキーのパターン（各種キー形式に対応）
    patterns = [
        r'^sk-[a-zA-Z0-9]{20,}',          # 標準キー
        r'^sk-proj-[a-zA-Z0-9]{20,}',      # プロジェクトキー
        r'^sk-ant-[a-zA-Z0-9]{20,}',       # Anthropicフォーマット
        r'^sk-org-[a-zA-Z0-9]{20,}'        # 組織キー
    ]
    
    # いずれかのパターンに一致すればOK
    for pattern in patterns:
        if re.match(pattern, api_key):
            return True
    
    return False

def sanitize_input(text):
    """ユーザー入力をサニタイズする"""
    if not text:
        return ""
    
    # 簡易的なサニタイズ
    # スクリプトタグの削除
    text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
    
    # 基本的なHTMLタグのエスケープ
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    return text