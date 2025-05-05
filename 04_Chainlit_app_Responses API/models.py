# ロギングヘルパーからロガーを取得
from log_helper import get_logger

# このモジュール用のロガーを取得
logger = get_logger(__name__)
"""
モデル関連のモジュール
OpenAI APIとの通信や利用可能なモデルの管理を行います
"""

import logging
import traceback
from typing import Dict, Any, List, Optional, AsyncGenerator

from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam
import chainlit as cl

from config import OPENAI_API_KEY, OPENAI_ORGANIZATION_ID, DEFAULT_MODEL, MODELS



# OpenAI APIクライアントの初期化
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID if OPENAI_ORGANIZATION_ID else None
)

# 現在のモデル（デフォルト値）
current_model = DEFAULT_MODEL


async def get_available_models() -> List[str]:
    """
    OpenAI APIから利用可能なモデルのリストを取得します。
    
    Returns:
        List[str]: 利用可能なモデル名のリスト
    """
    try:
        models_list = await client.models.list()
        model_ids = [model.id for model in models_list.data]
        logger.info(f"利用可能なモデルを取得しました: {len(model_ids)} モデル")
        logger.debug(f"利用可能なモデル一覧: {model_ids}")
        return model_ids
    except Exception as e:
        error_msg = f"モデルの取得中にエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        
        # エラーが発生した場合は、設定ファイルで定義されたモデルリストを返す
        fallback_models = [model[1] for model in MODELS]
        logger.info(f"フォールバック: 設定済みモデルリストを使用します: {fallback_models}")
        return fallback_models


def get_model_details(model_id: str) -> Dict[str, Any]:
    """
    モデルの詳細情報を取得します。
    
    Args:
        model_id (str): モデルのID
        
    Returns:
        Dict[str, Any]: モデルの詳細情報
    """
    # モデルIDを使って、そのモデルの詳細説明を返す
    for display_name, api_name in MODELS:
        if api_name == model_id:
            return {
                "display_name": display_name,
                "api_name": api_name,
                "description": display_name.split('(')[1].replace(')', '') if '(' in display_name else ""
            }
    
    # リストに見つからない場合、基本情報のみ返す
    return {
        "display_name": model_id,
        "api_name": model_id,
        "description": "カスタムモデル"
    }


async def check_model_availability(model_id: str) -> bool:
    """
    指定されたモデルが利用可能かどうかを確認します。
    
    Args:
        model_id (str): 確認するモデルのID
        
    Returns:
        bool: モデルが利用可能な場合はTrue、そうでない場合はFalse
    """
    try:
        available_models = await get_available_models()
        return model_id in available_models
    except Exception as e:
        error_msg = f"モデル利用可能性の確認中にエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        
        # エラーが発生した場合は、設定されたモデルとして扱う
        models_in_config = [model[1] for model in MODELS]
        is_available = model_id in models_in_config
        logger.info(f"フォールバック: モデル {model_id} は設定ファイル内に{'' if is_available else '不'}存在します")
        return is_available


async def set_current_model(model_id: str) -> Dict[str, Any]:
    """
    現在使用するモデルを設定します。
    
    Args:
        model_id (str): 設定するモデルのID
        
    Returns:
        Dict[str, Any]: 設定されたモデルの詳細情報
    """
    global current_model
    
    # モデルの利用可能性を確認
    is_available = await check_model_availability(model_id)
    
    if is_available:
        current_model = model_id
        logger.info(f"現在のモデルを設定しました: {model_id}")
        return get_model_details(model_id)
    else:
        logger.warning(f"モデル {model_id} は利用できません。デフォルトモデルを使用します: {current_model}")
        return get_model_details(current_model)


def get_current_model() -> str:
    """
    現在設定されているモデルのIDを取得します。
    
    Returns:
        str: 現在のモデルID
    """
    return current_model


async def chat_completion(
    messages: List[ChatCompletionMessageParam], 
    model: Optional[str] = None,
    temperature: float = 0.7,
    stream: bool = True
) -> AsyncGenerator[ChatCompletionChunk, None] | Dict[str, Any]:
    """
    OpenAI APIを使用してチャット応答を生成します。
    
    Args:
        messages (List[ChatCompletionMessageParam]): チャットメッセージのリスト
        model (Optional[str]): 使用するモデル（指定がない場合は現在のモデルを使用）
        temperature (float): 応答の多様性を制御するパラメータ
        stream (bool): ストリーミングモードを使用するかどうか
        
    Returns:
        AsyncGenerator[ChatCompletionChunk, None] | Dict[str, Any]: 
            ストリーミングモードの場合はチャンクのジェネレータ、そうでない場合は応答全体の辞書
    """
    try:
        model_to_use = model or current_model
        
        # ストリーミングモードの場合
        if stream:
            response_stream = await client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            return response_stream
        # 非ストリーミングモードの場合
        else:
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                stream=False
            )
            return response
    except Exception as e:
        error_msg = f"チャット応答の生成中にエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        
        # エラーメッセージを表示用に返す
        return {
            "error": True,
            "message": error_msg
        }