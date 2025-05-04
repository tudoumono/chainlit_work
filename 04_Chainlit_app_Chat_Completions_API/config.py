"""
設定関連のモジュール
アプリケーションの設定値や環境変数を管理します
"""

import os
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Any
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# ロギングヘルパーからロガーを取得
from log_helper import get_logger

# このモジュール用のロガーを取得
logger = get_logger(__name__)

# APIキーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

# APIキーのチェック
if not OPENAI_API_KEY:
    logger.warning("OpenAI APIキーが設定されていません。.envファイルを確認してください。")

# チャット履歴の保存先
CHAT_HISTORY_DIR = os.path.join(os.getcwd(), "chat_history")

# チャット履歴ディレクトリが存在しない場合は作成
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)
    logger.info(f"チャット履歴ディレクトリを作成しました: {CHAT_HISTORY_DIR}")

# 現在の日時を使用してチャット履歴のファイル名を生成
CHAT_HISTORY_FILE = os.path.join(
    CHAT_HISTORY_DIR,
    f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)

# 利用可能なモデルのリスト（表示名, APIモデル名）
MODELS: List[Tuple[str, str]] = [
    # 効率的・低コストモデル
    ("GPT‑3.5 Turbo(軽量・高速・低価格)", "gpt-3.5-turbo"),         # 軽量・高速・低価格
    ("GPT‑4o mini(GPT-4oの軽量版)", "gpt-4o-mini"),             # GPT-4oの軽量版
    ("GPT‑4.1 nano(最速・最安・100万トークン文脈)", "gpt-4.1-nano"),           # 最速・最安・100万トークン文脈
    
    # 標準モデル
    ("GPT‑4 Turbo(GPT‑4ベースの高速モデル)", "gpt-4-turbo"),             # GPT‑4ベースの高速モデル
    ("GPT‑4o(マルチモーダル対応)", "gpt-4o"),                       # マルチモーダル対応
    
    # 高性能モデル
    ("GPT‑4.1 mini(100万トークン文脈、コード特化)", "gpt-4.1-mini"),           # 100万トークン文脈、コード特化
    ("GPT‑4.1(最新・100万トークン文脈、コード特化)", "gpt-4.1"),                     # 最新・100万トークン文脈、コード特化
]

# デフォルトのモデル
DEFAULT_MODEL = "gpt-4o"

# 受け入れるファイルタイプ
ACCEPTED_FILE_TYPES = ["text/plain", "text/x-log"]

# ファイルの拡張子と対応するMIMEタイプの辞書
MIME_TYPES: Dict[str, str] = {
    ".txt": "text/plain",
    ".log": "text/x-log",
    # 将来的に拡張する際に追加可能
    # ".csv": "text/csv",
    # ".pdf": "application/pdf",
}

# ファイルアップロード設定
MAX_FILES = 10
MAX_FILE_SIZE_MB = 100