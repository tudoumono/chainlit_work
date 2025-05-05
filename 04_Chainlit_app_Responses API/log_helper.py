"""
ロギングヘルパーモジュール
アプリケーション全体でのロギング設定を管理します
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# ログのレベル定義
LOG_LEVEL = logging.INFO

# ログの保存先
LOG_DIR = "logs"
LOG_FILE_PREFIX = "app"


def setup_logging() -> str:
    """
    アプリケーション全体のロギング設定をセットアップします。
    
    Returns:
        str: 現在のログファイルのパス
    """
    # ログディレクトリが存在しない場合は作成
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # タイムスタンプを含むログファイル名
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f"{LOG_FILE_PREFIX}_{timestamp}.log")
    
    # 既存のハンドラを削除
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # ロギング設定
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # コンソール出力用ハンドラ
            logging.StreamHandler(),
            # ファイル出力用ハンドラ (10MBごとにローテーション、最大5ファイル保持)
            RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
        ]
    )
    
    # ログ開始メッセージ
    logger = logging.getLogger(__name__)
    logger.info(f"ロギングを開始しました: {log_file}")
    
    return log_file


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得します。
    
    Args:
        name (str): ロガー名（通常はモジュール名）
        
    Returns:
        logging.Logger: 設定済みのロガー
    """
    return logging.getLogger(name)