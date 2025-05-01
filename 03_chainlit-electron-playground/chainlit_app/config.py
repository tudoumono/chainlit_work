"""
config.py - 設定と初期化モジュール
===============================
環境変数の読み込み、パスの設定、初期化処理を行います。
"""

import os
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
        "SESSION_ID": SESSION_ID
    }

# デバッグモード用のプレフィックス
def get_prefix(debug_mode=False):
    """デバッグモード用のプレフィックスを返す"""
    return "🛠️【デバッグモード】\n" if debug_mode else ""