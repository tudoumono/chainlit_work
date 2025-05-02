"""
チャット処理関連のモジュール
メッセージの処理、チャット履歴の管理を行います
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import chainlit as cl
from openai.types.chat import ChatCompletionMessageParam

from models import chat_completion, get_current_model
from config import CHAT_HISTORY_FILE
from file_handler import get_file_content

# ロギング設定
logger = logging.getLogger(__name__)

# チャット履歴
chat_history: List[Dict[str, Any]] = []


async def process_message(
    message: str,
    files: Optional[List[cl.File]] = None,
    system_prompt: str = "あなたは親切なAIアシスタントです。簡潔かつ正確な回答を心がけてください。",
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    ユーザーメッセージを処理し、AIからの応答を取得します。
    
    Args:
        message (str): ユーザーのメッセージ
        files (Optional[List[cl.File]]): 添付ファイルのリスト
        system_prompt (str): システムプロンプト
        temperature (float): 応答の多様性を制御するパラメータ
        
    Returns:
        Dict[str, Any]: 処理結果を含む辞書
    """
    try:
        # 現在のモデルを取得
        model = get_current_model()
        
        # メッセージ履歴を作成
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
        ]
        
        # チャット履歴から過去のメッセージを追加（最大10ターン）
        recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
        for entry in recent_history:
            if entry["role"] in ["user", "assistant"]:
                messages.append({"role": entry["role"], "content": entry["content"]})
        
        # 添付ファイルの内容を取得して、ユーザーメッセージに追加
        file_contents = []
        if files:
            for file in files:
                try:
                    content = await file.get_content()
                    file_contents.append(
                        f"\n\n### ファイル: {file.name} ###\n{content.decode('utf-8', errors='replace')}"
                    )
                except Exception as e:
                    logger.error(f"ファイル内容の取得中にエラーが発生しました: {e}")
                    file_contents.append(f"\n\n### ファイル: {file.name} (読み込みエラー) ###")
        
        # ファイル内容をメッセージに追加
        user_message = message
        if file_contents:
            user_message += "\n" + "\n".join(file_contents)
        
        # ユーザーメッセージを追加
        messages.append({"role": "user", "content": user_message})
        
        # チャット履歴に追加
        chat_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "files": [f.name for f in files] if files else []
        })
        
        # OpenAI APIを使用して応答を取得
        response_stream = await chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True
        )
        
        # APIからエラーが返された場合
        if isinstance(response_stream, dict) and response_stream.get("error"):
            logger.error(f"APIエラー: {response_stream.get('message')}")
            return {
                "success": False,
                "error": response_stream.get("message"),
                "model": model
            }
        
        return {
            "success": True,
            "stream": response_stream,
            "model": model
        }
        
    except Exception as e:
        logger.error(f"メッセージ処理中にエラーが発生しました: {e}")
        return {
            "success": False,
            "error": f"メッセージ処理中にエラーが発生しました: {str(e)}",
            "model": get_current_model()
        }


def add_to_chat_history(role: str, content: str, files: Optional[List[str]] = None) -> None:
    """
    メッセージをチャット履歴に追加します。
    
    Args:
        role (str): メッセージの役割（'user'または'assistant'）
        content (str): メッセージの内容
        files (Optional[List[str]]): 添付ファイル名のリスト
    """
    chat_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "files": files or []
    })
    logger.debug(f"チャット履歴に {role} のメッセージを追加しました")


def save_chat_history() -> bool:
    """
    チャット履歴をファイルに保存します。
    
    Returns:
        bool: 保存に成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # チャット履歴をJSONファイルに保存
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
        
        logger.info(f"チャット履歴を保存しました: {CHAT_HISTORY_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"チャット履歴の保存中にエラーが発生しました: {e}")
        return False


def get_chat_history() -> List[Dict[str, Any]]:
    """
    チャット履歴を取得します。
    
    Returns:
        List[Dict[str, Any]]: チャット履歴
    """
    return chat_history


def clear_chat_history() -> None:
    """
    チャット履歴をクリアします。
    """
    chat_history.clear()
    logger.info("チャット履歴をクリアしました")