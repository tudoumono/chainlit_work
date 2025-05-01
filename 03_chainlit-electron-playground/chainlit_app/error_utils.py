"""
error_utils.py - エラー処理ユーティリティ
===========================================
アプリケーション全体で統一したエラー処理を提供します。
"""

import traceback
import chainlit as cl
from typing import Optional, Dict, Any

# エラーレベルの定義
ERROR = "error"
WARNING = "warning"
INFO = "info"

async def handle_error(e: Exception, context: str = "処理中", level: str = ERROR) -> None:
    """エラーを処理し、ユーザーに適切なメッセージを表示する"""
    error_type = type(e).__name__
    error_message = str(e)
    
    # ログにエラー詳細を出力
    stack_trace = traceback.format_exc()
    print(f"[{level.upper()}] {context}: {error_type}: {error_message}\n{stack_trace}")
    
    # エラーレベルに応じたアイコンとスタイル
    icons = {
        ERROR: "エラー",
        WARNING: "警告",
        INFO: "情報",
    }
    icon = icons.get(level, "問題")
    
    # エラータイプに応じたメッセージ
    if isinstance(e, ValueError):
        message = f"{icon} 入力値エラー: {error_message}"
    elif isinstance(e, ConnectionError):
        message = f"{icon} 接続エラー: APIサーバーに接続できませんでした。ネットワーク接続を確認してください。"
    elif isinstance(e, TimeoutError):
        message = f"{icon} タイムアウト: 処理に時間がかかりすぎています。後でもう一度お試しください。"
    else:
        # 一般的なエラーメッセージ
        message = f"{icon} エラーが発生しました ({context}): {error_message}"
    
    # アクションボタンの追加（適切な場合）
    actions = []
    if level == ERROR:
        actions.append(cl.Action(name="retry", label="再試行", payload={"action": "retry"}))
    
    # エラーメッセージの送信
    await cl.Message(content=message, actions=actions).send()

def log_error(e: Exception, context: str = "処理中", level: str = ERROR) -> None:
    """エラーをログに記録するだけ（UIには表示しない）"""
    error_type = type(e).__name__
    error_message = str(e)
    
    # ログにエラー詳細を出力
    stack_trace = traceback.format_exc()
    print(f"[{level.upper()}] {context}: {error_type}: {error_message}\n{stack_trace}")