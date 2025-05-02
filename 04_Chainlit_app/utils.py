"""
ユーティリティ関数モジュール
アプリケーション全体で使用される汎用的な関数を提供します
"""

import os
import logging
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

import chainlit as cl
from chainlit.types import ThreadDict

from config import CHAT_HISTORY_DIR

# ロギング設定
logger = logging.getLogger(__name__)


def format_timestamp(timestamp: str) -> str:
    """
    ISO形式のタイムスタンプを読みやすい形式に変換します。
    
    Args:
        timestamp (str): ISO形式のタイムスタンプ
        
    Returns:
        str: 読みやすい形式のタイムスタンプ
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp


async def show_processing_indicator(text: str = "処理中...") -> None:
    """
    処理中であることを示すインジケータを表示します。
    
    Args:
        text (str): 表示するテキスト
    """
    await cl.Message(
        content=text,
        author="システム",
        metadata={"is_processing": True}
    ).send()


def create_model_display_list() -> List[Dict[str, Any]]:
    """
    モデル選択用の表示リストを作成します。
    
    Returns:
        List[Dict[str, Any]]: モデル情報のリスト
    """
    from config import MODELS
    
    display_list = []
    
    # モデルカテゴリごとに分類
    categories = {
        "効率的・低コストモデル": [],
        "標準モデル": [],
        "高性能モデル": []
    }
    
    # カテゴリごとにモデルを分類
    for i, (display_name, api_name) in enumerate(MODELS):
        if i < 3:
            category = "効率的・低コストモデル"
        elif i < 5:
            category = "標準モデル"
        else:
            category = "高性能モデル"
        
        categories[category].append({
            "display_name": display_name,
            "api_name": api_name,
            "description": display_name.split('(')[1].replace(')', '') if '(' in display_name else ""
        })
    
    # 各カテゴリの情報を結合
    for category, models in categories.items():
        display_list.append({
            "category": category,
            "models": models
        })
    
    return display_list


def save_thread(thread: ThreadDict, save_dir: Optional[str] = None) -> str:
    """
    スレッドをJSONファイルとして保存します。
    
    Args:
        thread (ThreadDict): 保存するスレッド
        save_dir (Optional[str]): 保存先ディレクトリ（指定がない場合はデフォルトを使用）
        
    Returns:
        str: 保存されたファイルのパス
    """
    directory = save_dir or CHAT_HISTORY_DIR
    
    # ディレクトリが存在しない場合は作成
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # ファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"thread_{timestamp}_{thread['id']}.json"
    filepath = os.path.join(directory, filename)
    
    # JSONとして保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(thread, f, ensure_ascii=False, indent=2)
    
    logger.info(f"スレッドを保存しました: {filepath}")
    return filepath


async def create_file_upload_message() -> None:
    """
    ファイルアップロードを通知するメッセージを表示します。
    """
    from config import ACCEPTED_FILE_TYPES, MAX_FILES, MAX_FILE_SIZE_MB
    
    accepted_types_display = ", ".join([t.split("/")[1] for t in ACCEPTED_FILE_TYPES])
    message = f"""
📂 **ファイルアップロード**

このチャットでは以下の制限でファイルをアップロードできます：
- 対応形式: {accepted_types_display}
- 最大ファイル数: {MAX_FILES}ファイル
- 1ファイルあたりの最大サイズ: {MAX_FILE_SIZE_MB}MB

ファイルをドラッグ＆ドロップするか、クリップアイコンをクリックしてアップロードしてください。
    """
    
    await cl.Message(content=message, author="システム").send()


def get_mime_type_for_extension(extension: str) -> Optional[str]:
    """
    ファイル拡張子からMIMEタイプを取得します。
    
    Args:
        extension (str): ファイル拡張子（例: '.txt'）
        
    Returns:
        Optional[str]: MIMEタイプ、見つからない場合はNone
    """
    from config import MIME_TYPES
    
    # 拡張子が'.'で始まっていない場合は追加
    if not extension.startswith('.'):
        extension = '.' + extension
    
    return MIME_TYPES.get(extension.lower())