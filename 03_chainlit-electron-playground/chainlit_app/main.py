"""
main.py － Chainlit + OpenAI チャットアプリ
=========================================
このファイルを実行すると、ブラウザでチャット UI が立ち上がります。
利用者は「GPT‑3.5 / GPT‑4 / GPT‑4o」を途中でも自由に切り替えて対話できます。
ファイルアップロード機能により、データの分析も可能です。

Chainlit 2.5.5の機能を最大限に活用した実装です。
"""

# ────────────────────────────────────────────────────────────────
# 0. ライブラリの読み込み
# ────────────────────────────────────────────────────────────────
import os
import sys
import json
import asyncio
import time
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union

import chainlit as cl

# ▼ 自作モジュール
import config               # 設定と初期化
import models_utils         # モデル関連
import history_utils        # チャット履歴保存関連
import ui_actions           # UIアクション関連
import file_utils           # ファイル処理関連
import error_utils  # エラー処理ユーティリティをインポート

# ────────────────────────────────────────────────────────────────
# 1. 初期設定
# ────────────────────────────────────────────────────────────────
# 環境設定を読み込む
settings = config.setup_environment()

# OpenAIクライアントの初期化
client = models_utils.init_openai_client(settings["OPENAI_API_KEY"])

# エラーハンドリング関数
async def handle_error(e: Exception, context: str = "処理中"):
    """エラーを処理し、ユーザーに適切なメッセージを表示する"""
    error_type = type(e).__name__
    error_message = str(e)
    
    # ログにエラー詳細を出力
    stack_trace = traceback.format_exc()
    print(f"[ERROR] {context}: {error_type}: {error_message}\n{stack_trace}")
    
    # エラーレベルに応じたアイコン
    icon = "エラー"
    
    # エラーメッセージの送信
    message = f"{icon} {context}でエラーが発生しました: {error_message}"
    
    await cl.Message(
        content=message,
        actions=[
            cl.Action(name="retry", label="再試行", payload={"action": "retry"})
        ]
    ).send()

# ────────────────────────────────────────────────────────────────
# 2. Chainlit イベントハンドラ
# ────────────────────────────────────────────────────────────────
@cl.on_chat_start
async def start():
    """チャット開始時の処理"""
    try:
        # セッション変数の初期化
        cl.user_session.set("files", {})
        cl.user_session.set("chat_history", [])
        cl.user_session.set("cancel_flag", False)
        cl.user_session.set("partial_response", "")
        cl.user_session.set("selected_model", "gpt-4o")

        
        if not settings["API_KEY_VALID"]:
            # APIキーがない場合は警告表示
            await cl.Message(
                content="**OpenAI APIキーが設定されていないか無効です！**\n"
                        "`.env` ファイルに以下のように設定してください：\n"
                        "`OPENAI_API_KEY=\"sk-xxxx...\"`",
                actions=ui_actions.common_actions(),
            ).send()
            return

        # 通常の開始処理
        await ui_actions.show_welcome_message(models_utils.MODELS)
    
    except Exception as e:
        # エラー発生時の処理
        await handle_error(e, "チャット開始処理中")

@cl.action_callback("change_model")
async def change_model(_):
    """モデル変更アクションのコールバック"""
    try:
        # 詳細情報付きのモデル選択UIを表示
        if hasattr(models_utils, "MODEL_INFO") and models_utils.MODEL_INFO:
            await ui_actions.show_model_info_selection(models_utils.MODELS, models_utils.MODEL_INFO)
        else:
            await ui_actions.show_model_selection(models_utils.MODELS, config.get_prefix(settings["DEBUG_MODE"]))
    except Exception as e:
        await handle_error(e, "モデル選択処理中")

@cl.action_callback("select_model")
async def model_selected(action: cl.Action):
    """モデル選択アクションのコールバック"""
    try:
        model = action.payload.get("model")
        if not model:
            raise ValueError("モデルが指定されていません")
        
        # セッション変数に保存
        cl.user_session.set("selected_model", model)
        
        # モデル情報を取得
        model_label = models_utils.get_model_label(model)
        model_info = None
        
        # MODEL_INFOがあれば利用
        if hasattr(models_utils, "MODEL_INFO") and models_utils.MODEL_INFO:
            model_info = models_utils.MODEL_INFO.get(model, {})
        
        # モデル情報を含むメッセージを表示
        content = f"{config.get_prefix(settings['DEBUG_MODE'])}モデル「{model_label}」を選択しました。\n\n"
        
        if model_info:
            content += (
                f"- **{model_info.get('description', '')}**\n"
                f"- 文脈窓: {model_info.get('context_window', 'N/A')} トークン\n"
                f"- 学習データ: {model_info.get('training_data', 'N/A')}\n\n"
            )
        
        content += "質問するか、ファイルをアップロードしてください！"
        
        await cl.Message(
            content=content,
            actions=ui_actions.common_actions(),
        ).send()
    except Exception as e:
        await handle_error(e, "モデル選択処理中")

# ★ ファイルアップロードボタン
@cl.action_callback("upload_file")
async def upload_file_action(_):
    """ファイルアップロードアクションのコールバック"""
    try:
        files = await cl.AskFileMessage(
            content="分析したいファイルをアップロードしてください。\n"
                    "サポートしているファイル形式: CSV, Excel, テキスト, JSON, PDF, 画像",
            accept=["text/csv", "application/vnd.ms-excel", 
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    "text/plain", "application/json", "application/pdf", 
                    "image/png", "image/jpeg", "image/jpg"],
            max_size_mb=10,
            timeout=180,
        ).send()

        # ファイル処理を切り出したモジュールに委譲
        processed_files = await file_utils.handle_file_upload(files, settings["UPLOADS_DIR"])
        
        # 処理したファイル情報をセッションに保存
        current_files = cl.user_session.get("files", {})
        current_files.update(processed_files)
        cl.user_session.set("files", current_files)
    
    except Exception as e:
        await handle_error(e, "ファイルアップロード処理中")

@cl.action_callback("show_details")
async def show_file_details(action):
    """ファイル詳細表示アクションのコールバック"""
    try:
        file_name = action.payload.get("file_name")
        if not file_name:
            raise ValueError("ファイル名が指定されていません")
        
        files = cl.user_session.get("files", {})
        
        if file_name not in files:
            await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
            return
        
        # ファイル情報を取得
        file_info = files[file_name]
        
        # ファイルタイプに応じた詳細表示
        if file_info["type"] in ["csv", "excel"]:
            await file_utils.display_dataframe_details(file_info["dataframe"], file_name)
        elif file_info["type"] == "text":
            await cl.Message(
                content=f"### {file_name} の全文:\n```\n{file_info['full_content']}\n```"
            ).send()
        elif file_info["type"] == "json":
            json_str = json.dumps(file_info["content"], indent=2, ensure_ascii=False)
            await cl.Message(
                content=f"### {file_name} の内容:\n```json\n{json_str}\n```"
            ).send()
        else:
            await cl.Message(content=f"このファイル形式の詳細表示はサポートされていません: {file_info['type']}").send()
    
    except Exception as e:
        await handle_error(e, "ファイル詳細表示処理中")

@cl.action_callback("analyze_file")
async def analyze_file(action):
    """ファイル分析アクションのコールバック"""
    try:
        file_name = action.payload.get("file_name")
        if not file_name:
            raise ValueError("ファイル名が指定されていません")
        
        files = cl.user_session.get("files", {})
        
        if file_name not in files:
            await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
            return
        
        # 処理中メッセージの表示
        processing_msg = await ui_actions.show_processing_status(f"ファイル「{file_name}」を詳細に分析しています")
        
        file_info = files[file_name]
        
        # ファイルタイプに応じた処理
        try:
            # ファイルの詳細分析
            if file_info["type"] == "csv" and "dataframe" in file_info:
                # CSVデータ分析用プロンプト
                df = file_info["dataframe"]
                csv_str = df.head(20).to_csv(index=False)
                prompt = (
                    f"以下のCSVデータ（「{file_name}」の最初の20行）を分析してください。"
                    "基本的な統計情報、データの傾向、および特徴をまとめてください。\n\n"
                    f"```\n{csv_str}\n```"
                )
            elif file_info["type"] == "excel" and "dataframe" in file_info:
                # Excelデータ分析用プロンプト
                df = file_info["dataframe"]
                excel_str = df.head(20).to_csv(index=False)
                prompt = (
                    f"以下のExcelデータ（「{file_name}」の最初の20行）を分析してください。"
                    "基本的な統計情報、データの傾向、および特徴をまとめてください。\n\n"
                    f"```\n{excel_str}\n```"
                )
            elif file_info["type"] == "text" and "full_content" in file_info:
                # テキスト分析用プロンプト
                content = file_info["full_content"]
                if len(content) > 5000:
                    content = content[:5000] + "..."  # 長すぎる場合は省略
                prompt = (
                    f"以下のテキストファイル「{file_name}」の内容を分析してください。"
                    "主要なポイント、構造、文体、トピックなどをまとめてください。\n\n"
                    f"```\n{content}\n```"
                )
            elif file_info["type"] == "json" and "content" in file_info:
                # JSON分析用プロンプト
                json_str = json.dumps(file_info["content"], indent=2, ensure_ascii=False)
                if len(json_str) > 5000:
                    json_str = json_str[:5000] + "..."  # 長すぎる場合は省略
                prompt = (
                    f"以下のJSONデータ（「{file_name}」）を分析してください。"
                    "データ構造、主要な要素、特徴などをまとめてください。\n\n"
                    f"```json\n{json_str}\n```"
                )
            elif file_info["type"] == "image":
                # 画像分析用プロンプト
                prompt = f"画像ファイル「{file_name}」を分析してください。内容や特徴を説明してください。"
            elif file_info["type"] == "pdf":
                # PDF分析用プロンプト
                prompt = f"PDFファイル「{file_name}」を分析してください。内容の要約や主要なポイントを説明してください。"
            else:
                prompt = f"ファイル「{file_name}」の分析をお願いします。"
            
            # 処理中メッセージの更新
            processing_msg.content = f"ファイル「{file_name}」の分析が完了しました"
            await processing_msg.update()
            
            # 分析のためのプロンプトを送信
            msg = cl.Message(content=prompt)
            await on_message(msg)
        
        except Exception as e:
            processing_msg.content = f"ファイル「{file_name}」の分析中にエラーが発生しました"
            await processing_msg.update()
            raise e
    
    except Exception as e:
        await handle_error(e, "ファイル分析処理中")

# ★ 停止ボタン
@cl.action_callback("cancel")
async def cancel_stream(_):
    """生成停止アクションのコールバック"""
    try:
        cl.user_session.set("cancel_flag", True)
        
        await cl.Message(
            content="生成を停止します…", 
            actions=ui_actions.common_actions(show_resume=True)
        ).send()
    except Exception as e:
        await handle_error(e, "生成停止処理中")

# ★ 再開ボタン
@cl.action_callback("resume")
async def resume_stream(_):
    """生成再開アクションのコールバック"""
    try:
        last_user_msg = cl.user_session.get("last_user_msg", "")
        partial_response = cl.user_session.get("partial_response", "")
        
        if not last_user_msg:
            await cl.Message(content="再開できる会話が見つかりません。").send()
            return
        
        # 部分的な応答があれば表示
        if partial_response:
            await cl.Message(
                content=f"**前回の途中までの応答**:\n\n{partial_response}\n\n---\n\n続きを生成しています..."
            ).send()
        
        # 続きを生成するためのプロンプト
        continuation_prompt = (
            f"{last_user_msg}\n\n"
            f"[前回の応答]:\n{partial_response}\n\n"
            "続きを生成してください。"
        )
        
        # 再度 ask_openai
        await on_message(cl.Message(content=continuation_prompt, author="user", id="resume"), resume=True)
    
    except Exception as e:
        await handle_error(e, "生成再開処理中")

# ★ 保存ボタン（TXTフォーマットのみ）
@cl.action_callback("save")
async def save_history(_):
    """会話履歴保存アクションのコールバック"""
    try:
        history = cl.user_session.get("chat_history", [])
        
        if not history:
            await cl.Message(content="保存する会話履歴がありません。").send()
            return
        
        # 処理中メッセージの表示
        processing_msg = await ui_actions.show_processing_status("会話履歴を保存しています")
        
        # TXT形式で保存
        txt_fp = history_utils.save_chat_history_txt(
            history, 
            settings["CHAT_LOG_DIR"], 
            settings["SESSION_ID"], 
            is_manual=True
        )
        
        if not txt_fp:
            processing_msg.content = "会話履歴の保存に失敗しました"
            await processing_msg.update()
            return
        
        # 処理中メッセージの更新
        processing_msg.content = "会話履歴の保存が完了しました"
        await processing_msg.update()
        
        # 保存したファイルを表示
        elements = [
            cl.File(
                name=txt_fp.name, 
                path=str(txt_fp), 
                display="inline", 
                mime="text/plain", 
                description="テキスト形式（読みやすい形式）"
            )
        ]
        
        await cl.Message(
            content=f"このチャネルでのやり取りを保存しました。\n保存先: {settings['CHAT_LOG_DIR']}",
            elements=elements
        ).send()
    
    except Exception as e:
        await handle_error(e, "会話履歴保存処理中")

# ★ プロセス完全終了ボタン
@cl.action_callback("shutdown")
async def shutdown_app(_):
    """アプリケーション終了アクションのコールバック"""
    await cl.Message(content="サーバーを終了します…").send()
    await cl.sleep(0.5)  # メッセージ送信猶予
    os._exit(0)          # 即プロセス終了（SystemExitを無視して強制終了）

# ★ 再試行ボタン
@cl.action_callback("retry")
async def retry_action(action):
    """再試行アクションのコールバック"""
    try:
        # 前回のメッセージを取得して再送信
        last_user_msg = cl.user_session.get("last_user_msg", "")
        if not last_user_msg:
            await cl.Message(content="再試行する会話が見つかりません。").send()
            return
        
        # 再試行メッセージを表示
        await cl.Message(content="リクエストを再試行しています...").send()
        
        # 前回のメッセージを再送信
        await on_message(cl.Message(content=last_user_msg, author="user", id="retry"))
    
    except Exception as e:
        await handle_error(e, "再試行処理中")

# メインのメッセージハンドラ
# main.py - on_message関数の修正
@cl.on_message
async def on_message(msg: cl.Message):
    """メインのメッセージハンドラ（改善版）"""
    try:
        # 事前状態のリセットと履歴処理
        cl.user_session.set("cancel_flag", False)
        history = cl.user_session.get("chat_history", [])
        
        # メッセージをサニタイズ（セキュリティ対策）
        sanitized_content = config.sanitize_input(msg.content)
        
        # 履歴にユーザーメッセージを追加
        history.append({"role": "user", "content": sanitized_content})
        cl.user_session.set("last_user_msg", sanitized_content)
        cl.user_session.set("chat_history", history)  # 重要: ここで履歴を保存

        # モデル情報の取得
        model = cl.user_session.get("selected_model", "gpt-4o")
        
        # 応答メッセージの初期化
        stream_msg = cl.Message(content="")
        await stream_msg.send()

        try:
            # ファイル参照がないかチェック
            files = cl.user_session.get("files", {})
            message_content = sanitized_content
            
            # ファイル参照がある場合、関連コンテンツを追加
            message_content = file_utils.get_file_reference_content(message_content, files)
            
            # ★重要な修正: APIキーチェック
            if not settings["API_KEY_VALID"]:
                stream_msg.content = "**OpenAI APIキーが設定されていないか無効です。** .envファイルを確認してください。"
                await stream_msg.update()
                return  # 早期リターンで処理を終了
            
            # ★重要な修正: タイムアウト付きAPI呼び出し
            try:
                # OpenAI API呼び出し処理のタイムアウト設定
                api_task = asyncio.create_task(models_utils.ask_openai(
                    client, 
                    message_content, 
                    history, 
                    model, 
                    debug_mode=settings["DEBUG_MODE"]
                ))
                
                # 30秒のタイムアウトを設定
                stream = await asyncio.wait_for(api_task, timeout=30.0)
            except asyncio.TimeoutError:
                stream_msg.content = "APIリクエストがタイムアウトしました。もう一度試すか、設定を確認してください。"
                await stream_msg.update()
                return  # 早期リターンで処理を終了
            
            # 応答を構築
            assistant_text = ""
            
            # ★重要な修正: 明示的に処理完了を示す変数
            processing_completed = False
            
            try:
                async for chunk in stream:
                    # キャンセルフラグをチェック
                    if cl.user_session.get("cancel_flag", False):
                        await stream.aclose()
                        cl.user_session.set("partial_response", assistant_text)
                        break
                    
                    # チャンク内容の取得と追加
                    content = chunk.choices[0].delta.content
                    if content:
                        assistant_text += content
                        stream_msg.content = assistant_text
                        await stream_msg.update()
                
                # 明示的に処理完了を設定
                processing_completed = True
            
            except Exception as e:
                stream_msg.content = f"エラーが発生しました: {str(e)}"
                await stream_msg.update()
                print(f"ストリーム処理エラー: {str(e)}")
                traceback.print_exc()
            
            # 処理が完了したらのみ履歴に追加
            if processing_completed and not cl.user_session.get("cancel_flag", False):
                # 履歴に応答を追加
                history.append({"role": "assistant", "content": assistant_text})
                cl.user_session.set("chat_history", history)
                cl.user_session.set("partial_response", "")
                
                # 明示的に処理完了メッセージを表示
                await cl.Message(content="✅ 応答が完了しました").send()
            
        except Exception as e:
            error_message = f"エラーが発生しました: {str(e)}"
            stream_msg.content = error_message
            await stream_msg.update()
            print(f"処理エラー: {error_message}")
            traceback.print_exc()

    except Exception as e:
        print(f"全体エラー: {str(e)}")
        traceback.print_exc()
        await cl.Message(content=f"エラーが発生しました: {str(e)}").send()

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""