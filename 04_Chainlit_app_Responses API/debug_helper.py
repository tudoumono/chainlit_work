"""
デバッグヘルパーモジュール
アプリケーションのデバッグに役立つユーティリティ関数を提供します
"""

import sys
import inspect
from typing import Any, Dict, List, Optional

from log_helper import get_logger

# このモジュール用のロガーを取得
logger = get_logger(__name__)


def get_object_attributes(obj: Any) -> Dict[str, Any]:
    """
    オブジェクトの属性を取得します。
    
    Args:
        obj (Any): 属性を取得するオブジェクト
        
    Returns:
        Dict[str, Any]: キーが属性名、値が属性値の辞書
    """
    if obj is None:
        return {"error": "オブジェクトはNoneです"}
    
    try:
        # 呼び出し可能でない属性のみを取得
        attrs = {}
        for attr in dir(obj):
            if not attr.startswith('_'):  # 内部属性を除外
                try:
                    value = getattr(obj, attr)
                    if not callable(value):  # メソッドを除外
                        # 複雑なオブジェクトは型情報のみ
                        if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict, tuple)):
                            attrs[attr] = f"<{type(value).__name__}>"
                        else:
                            attrs[attr] = value
                except Exception as e:
                    attrs[attr] = f"<エラー: {str(e)}>"
        
        return attrs
    except Exception as e:
        return {"error": f"属性取得中にエラーが発生しました: {str(e)}"}


def log_object_info(obj: Any, prefix: str = "オブジェクト情報") -> None:
    """
    オブジェクトの情報をログに記録します。
    
    Args:
        obj (Any): ログに記録するオブジェクト
        prefix (str): ログメッセージの接頭辞
    """
    try:
        attrs = get_object_attributes(obj)
        logger.debug(f"{prefix}: {type(obj).__name__}")
        for attr, value in attrs.items():
            logger.debug(f"  {attr}: {value}")
    except Exception as e:
        logger.error(f"オブジェクト情報のログ記録中にエラーが発生しました: {e}")


def log_traceback() -> None:
    """
    現在のスタックトレースをログに記録します。
    """
    import traceback
    logger.debug("スタックトレース:")
    for line in traceback.format_stack():
        logger.debug(line.strip())


def dump_frames() -> None:
    """
    すべてのスタックフレームの情報をダンプします。
    デバッグ困難な問題の調査に使用します。
    """
    frames = inspect.stack()
    logger.debug(f"=== スタックフレーム ({len(frames)}フレーム) ===")
    
    for i, frame_info in enumerate(frames):
        frame = frame_info.frame
        logger.debug(f"フレーム {i}: {frame_info.function} in {frame_info.filename}:{frame_info.lineno}")
        
        # ローカル変数
        if frame.f_locals:
            logger.debug("  ローカル変数:")
            for key, value in frame.f_locals.items():
                # 大きなオブジェクトは型のみ表示
                if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool)):
                    logger.debug(f"    {key}: <{type(value).__name__}>")
                else:
                    logger.debug(f"    {key}: {value}")