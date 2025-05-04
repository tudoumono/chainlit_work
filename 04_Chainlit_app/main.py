"""
メイン実行ファイル
アプリケーションのエントリーポイントです
"""

import os
import logging
from typing import Dict, Any, List, Optional
from debug_helper import log_object_info
import traceback

import chainlit as cl
from chainlit.input_widget import Select
from openai.types.chat import ChatCompletionChunk

from config import CHAT_HISTORY_FILE, CHAT_HISTORY_DIR, MODELS, DEFAULT_MODEL, ACCEPTED_FILE_TYPES, MAX_FILES, MAX_FILE_SIZE_MB
from models import set_current_model, get_current_model, get_model_details
from chat_handler import process_message, add_to_chat_history, save_chat_history
from file_handler import process_uploaded_file, get_all_uploaded_files
from utils import create_model_display_list, save_thread

# ロギング設定のインポート
from log_helper import setup_logging, get_logger

# ロギングをセットアップして、現在のログファイルのパスを取得
log_file = setup_logging()

# このモジュール用のロガーを取得
logger = get_logger(__name__)

# アプリケーション起動ログ
logger.info("アプリケーションを起動しました。ログファイル: %s", log_file)

# 現在のチャット設定
chat_settings: Dict[str, Any] = {
    "model": DEFAULT_MODEL,
    "temperature": 0.7,
    "system_prompt": "あなたは親切なAIアシスタントです。簡潔かつ正確な回答を心がけてください。"
}


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


@cl.on_chat_start
async def on_chat_start():
    """
    チャットセッション開始時の処理です。
    """
    logger.info("新しいチャットセッションが開始されました")
    
    # チャットの保存先を表示
    await cl.Message(
        content=f"📁 チャット履歴の保存先: {CHAT_HISTORY_DIR}",
        author="システム"
    ).send()
    
    logger.info(f"チャット履歴保存先を通知: {CHAT_HISTORY_DIR}")
    
    try:
        # 使用可能なモデルリストを表示
        model_values = [model[1] for model in MODELS]  # APIモデル名
        model_display = [model[0] for model in MODELS]  # 表示名
        
        # モデル選択ウィジェットを作成
        logger.debug(f"モデル選択ウィジェットを作成: {model_values}")
        settings = await cl.ChatSettings(
            [
                Select(
                    id="model",
                    label="OpenAIモデル",
                    values=model_values,
                    description="使用するOpenAIモデルを選択してください",
                    initial_index=model_values.index(DEFAULT_MODEL) if DEFAULT_MODEL in model_values else 0
                )
            ]
        ).send()
        
        # 初期モデルを設定
        if "model" in settings:
            chat_settings["model"] = settings["model"]
            model_info = await set_current_model(settings["model"])
            
            logger.info(f"ユーザーによりモデルが選択されました: {settings['model']}")
            
            # モデル設定の通知
            await cl.Message(
                content=f"📝 モデルを**{model_info['display_name']}**に設定しました。",
                author="システム"
            ).send()
        else:
            # デフォルトモデルを設定
            model_info = await set_current_model(DEFAULT_MODEL)
            logger.info(f"デフォルトモデルを設定: {DEFAULT_MODEL}")
            
            await cl.Message(
                content=f"📝 デフォルトモデル**{model_info['display_name']}**を使用します。",
                author="システム"
            ).send()
    except Exception as e:
        error_msg = f"モデル設定中にエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        
        await cl.Message(
            content=f"⚠️ モデル設定中にエラーが発生しました。デフォルト設定を使用します。",
            author="システム"
        ).send()
    
    # ファイルアップロード情報を表示
    try:
        file_types = ", ".join([f"*{ext}" for ext in [".txt", ".log"]])
        await cl.Message(
            content=f"📄 **ファイルアップロード**\nサポートされるファイル形式: {file_types}\n最大ファイル数: {MAX_FILES}ファイル\n最大ファイルサイズ: {MAX_FILE_SIZE_MB}MB",
            author="システム"
        ).send()
        logger.info(f"ファイルアップロード情報を通知: {file_types}, 最大 {MAX_FILES}ファイル, 最大 {MAX_FILE_SIZE_MB}MB")
    except Exception as e:
        logger.error(f"ファイルアップロード情報表示中にエラーが発生しました: {e}")
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")


@cl.on_settings_update
async def on_settings_update(settings):
    """
    チャット設定が更新されたときの処理です。
    
    Args:
        settings: 更新された設定値
    """
    global chat_settings
    
    # モデルが変更された場合
    if "model" in settings and settings["model"] != chat_settings["model"]:
        old_model = chat_settings["model"]
        new_model = settings["model"]
        
        # 新しいモデルを設定
        model_info = await set_current_model(new_model)
        chat_settings["model"] = new_model
        
        # モデル変更の通知
        await cl.Message(
            content=f"🔄 モデルを変更しました: **{get_model_details(old_model)['display_name']}** → **{model_info['display_name']}**",
            author="システム"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    メッセージを受信したときのイベントハンドラ。
    
    Args:
        message (cl.Message): 受信したメッセージ
    """
    # モデル情報を取得
    model = get_current_model()
    model_info = get_model_details(model)
    
    # 処理中メッセージを表示
    await show_processing_indicator()
    
    # メッセージ処理
    response = await process_message(
        message=message.content,
        files=message.elements,
        system_prompt=chat_settings.get("system_prompt", "あなたは親切なAIアシスタントです。簡潔かつ正確な回答を心がけてください。"),
        temperature=chat_settings.get("temperature", 0.7)
    )
    
    # 処理に失敗した場合
    if not response["success"]:
        await cl.Message(
            content=f"エラーが発生しました: {response.get('error', '不明なエラー')}",
            author="システム"
        ).send()
        return
    
    # AIの応答用メッセージを作成
    ai_message = cl.Message(content="", author=model_info["display_name"])
    await ai_message.send()
    
    # ストリーミングが成功した場合
    if response.get("stream"):
        # Responses APIでのストリーミング処理
        response_stream = response["stream"]
        collected_response = ""
        
        try:
            # イベントストリームを処理
            async for chunk in response_stream:
                # イベントタイプをログ出力（デバッグ用）
                logger.debug(f"受信したイベントタイプ: {type(chunk).__name__}")
                
                # 新しいOpenAI Responsesタイプの処理
                if hasattr(chunk, 'type'):
                    # ResponseCreatedEventの処理
                    if chunk.type == 'response_created':
                        # 初期化イベントなので何もしない
                        logger.debug("Response created event received")
                        continue
                        
                    # TextDeltaEventの処理
                    elif chunk.type == 'text_delta':
                        if hasattr(chunk, 'delta'):
                            text_content = chunk.delta
                            collected_response += text_content
                            # Chainlit 2.5.5でのアップデート方法
                            ai_message.content = collected_response
                            await ai_message.update()
                            
                    # TextStopEventの処理
                    elif chunk.type == 'text_stop':
                        logger.debug("Text stop event received")
                    
                    # その他のイベントタイプ
                    else:
                        logger.debug(f"Unknown event type: {chunk.type}")
                
                # 旧形式の処理 (互換性のため)
                elif hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        text_content = chunk.choices[0].delta.content
                        collected_response += text_content
                        ai_message.content = collected_response
                        await ai_message.update()
                
                # 他のタイプのチャンク（未知の形式）
                else:
                    logger.debug(f"未知のチャンク形式: {chunk}")
                        
        except Exception as e:
            logger.error(f"ストリーミング処理中にエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            ai_message.content = f"{collected_response}\n\n[ストリーミング中にエラーが発生しました]"
            await ai_message.update()
            return
        
        # 応答が終了したら、チャット履歴に追加
        add_to_chat_history("assistant", collected_response)
        save_chat_history()
    else:
        # ストリーミングがない場合、通常の応答を表示
        response_text = response.get("message", "応答を取得できませんでした")
        ai_message.content = response_text
        await ai_message.update()
        
        # チャット履歴に追加
        add_to_chat_history("assistant", response_text)
        save_chat_history()


@cl.on_chat_end
async def on_chat_end():
    """
    チャットセッション終了時の処理です。
    """
    # チャット履歴を保存
    save_chat_history()
    
    # スレッド情報を取得
    thread_data = cl.user_session.get("thread", {})
    if thread_data:
        # スレッドを保存
        filepath = save_thread(thread_data)
        logger.info(f"スレッドを保存しました: {filepath}")


if __name__ == "__main__":
    # 直接実行された場合
    print(f"チャットアプリケーションを起動します。Chainlitを使用して実行してください: chainlit run main.py")
    print(f"チャット履歴の保存先: {CHAT_HISTORY_DIR}")