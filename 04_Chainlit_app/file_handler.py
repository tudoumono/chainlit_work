"""
ファイル処理関連のモジュール
ファイルのアップロード、読み込み、検証を行います
"""

import os
import logging
from typing import List, Dict, Any, Optional
import traceback
import mimetypes
import json
from datetime import datetime

import chainlit as cl
from config import ACCEPTED_FILE_TYPES, MAX_FILES, MAX_FILE_SIZE_MB, MIME_TYPES

# ロギングヘルパーからロガーを取得
from log_helper import get_logger

# このモジュール用のロガーを取得
logger = get_logger(__name__)

# アップロードされたファイルを格納する辞書
# キー: ファイルID、値: ファイルの内容と情報
uploaded_files: Dict[str, Dict[str, Any]] = {}


def validate_file_type(file: cl.File) -> bool:
    """
    ファイルの種類が許可されているかを検証します。
    
    Args:
        file (cl.File): 検証するファイル
        
    Returns:
        bool: ファイルが許可されている場合はTrue、そうでない場合はFalse
    """
    # ファイル名から拡張子を取得
    file_ext = os.path.splitext(file.name)[1].lower()
    
    # 拡張子から許可されているかを確認
    return file_ext in ['.txt', '.log']


def validate_file_size(file: cl.File) -> bool:
    """
    ファイルサイズが制限内かを検証します。
    
    Args:
        file (cl.File): 検証するファイル
        
    Returns:
        bool: ファイルサイズが制限内の場合はTrue、そうでない場合はFalse
    """
    try:
        # 現在のChainlitバージョンではsizeプロパティが異なる可能性がある
        # try-exceptでプロパティが存在するか確認
        if hasattr(file, 'size'):
            size_mb = file.size / (1024 * 1024)
        else:
            # ファイルのサイズが不明の場合、許可する
            logger.warning(f"ファイル {file.name} のサイズが取得できません。処理を続行します。")
            return True
        
        return size_mb <= MAX_FILE_SIZE_MB
    except Exception as e:
        logger.error(f"ファイルサイズの検証中にエラーが発生しました: {e}")
        # エラーが発生した場合は、安全のために許可する
        return True


async def process_uploaded_file(file: cl.File) -> Dict[str, Any]:
    """
    アップロードされたファイルを処理します。
    
    Args:
        file (cl.File): 処理するファイル
        
    Returns:
        Dict[str, Any]: 処理結果を含む辞書
    """
    try:
        # ファイルの種類を検証
        if not validate_file_type(file):
            return {
                "success": False,
                "error": f"非対応のファイル形式です。対応形式: .txt, .log"
            }
        
        # ファイルサイズを検証
        if not validate_file_size(file):
            return {
                "success": False,
                "error": f"ファイルサイズが大きすぎます。最大サイズ: {MAX_FILE_SIZE_MB}MB"
            }
        
        # ファイルの内容を読み込む（Chainlit 2.5.5での正しい方法）
        # get_contentメソッドが存在しないので、直接contentプロパティを使用
        try:
            # バイナリデータがあるか確認
            if hasattr(file, 'content') and file.content:
                content = file.content
            elif hasattr(file, 'path') and file.path:
                # ファイルパスから読み込む
                with open(file.path, 'rb') as f:
                    content = f.read()
            else:
                logger.error(f"ファイル {file.name} の内容を取得できません")
                return {
                    "success": False,
                    "error": f"ファイル内容を取得できません。ファイル形式を確認してください。"
                }
        except Exception as content_error:
            logger.error(f"ファイル内容の読み込み中にエラーが発生しました: {content_error}")
            return {
                "success": False,
                "error": f"ファイル内容の読み込み中にエラーが発生しました: {str(content_error)}"
            }
        
        # アップロードされたファイルを辞書に保存
        file_info = {
            "id": file.id,
            "name": file.name,
            "mime_type": mimetypes.guess_type(file.name)[0],
            "size": len(content) if content else 0,
            "content": content.decode('utf-8', errors='replace') if content else "",  # UTF-8でデコード、エラーは置換
            "upload_time": datetime.now().isoformat()
        }
        
        uploaded_files[file.id] = file_info
        
        logger.info(f"ファイルが正常にアップロードされました: {file.name} (サイズ: {file_info['size']} bytes)")
        
        return {
            "success": True,
            "file_info": {k: v for k, v in file_info.items() if k != "content"}  # contentは除外
        }
        
    except Exception as e:
        error_msg = f"ファイル処理中にエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        return {
            "success": False,
            "error": error_msg
        }


def get_uploaded_file(file_id: str) -> Optional[Dict[str, Any]]:
    """
    アップロードされたファイルの情報を取得します。
    
    Args:
        file_id (str): 取得するファイルのID
        
    Returns:
        Optional[Dict[str, Any]]: ファイルの情報、存在しない場合はNone
    """
    return uploaded_files.get(file_id)


def get_all_uploaded_files() -> List[Dict[str, Any]]:
    """
    すべてのアップロードされたファイル情報のリストを取得します（内容は除く）。
    
    Returns:
        List[Dict[str, Any]]: ファイル情報のリスト
    """
    return [
        {k: v for k, v in file_info.items() if k != "content"}
        for file_info in uploaded_files.values()
    ]


def get_file_content(file_id: str) -> Optional[str]:
    """
    ファイルの内容を取得します。
    
    Args:
        file_id (str): 取得するファイルのID
        
    Returns:
        Optional[str]: ファイルの内容、存在しない場合はNone
    """
    file_info = uploaded_files.get(file_id)
    if file_info:
        return file_info.get("content")
    return None


def clear_uploaded_files() -> None:
    """
    アップロードされたファイルの情報をクリアします。
    """
    uploaded_files.clear()
    logger.info("アップロードされたファイル情報をクリアしました")


def save_uploaded_files_info(filepath: str) -> bool:
    """
    アップロードされたファイルの情報（内容を除く）をJSONファイルに保存します。
    
    Args:
        filepath (str): 保存先のファイルパス
        
    Returns:
        bool: 保存に成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 内容を除いたファイル情報を生成
        files_info = []
        for file_id, file_info in uploaded_files.items():
            info_without_content = {k: v for k, v in file_info.items() if k != "content"}
            files_info.append(info_without_content)
        
        # JSONファイルに保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(files_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"ファイル情報を保存しました: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"ファイル情報の保存中にエラーが発生しました: {e}")
        return False