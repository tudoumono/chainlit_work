"""
main.py － Chainlit + OpenAI チャットアプリ
=========================================
このファイルを実行すると、ブラウザでチャット UI が立ち上がります。
利用者は「GPT‑3.5 / GPT‑4 / GPT‑4o」を途中でも自由に切り替えて対話できます。
ファイルアップロード機能により、データの分析も可能です。

--------------------------------------------------------------------------
💡 "ざっくり全体像"
--------------------------------------------------------------------------
1. **初期化**      : 環境変数を読み込み、OpenAI クライアントを作成
2. **モデル選択UI**: 起動時にボタンを表示（`show_model_selection()`）
3. **チャット処理**: ユーザー発言を受け取り、OpenAI へ問合せて返却
4. **履歴保存**    : 「保存」ボタンで TXT にエクスポート & 自動TXT保存機能追加
5. **モデル変更**  : いつでも「モデル変更」ボタンで再選択できる
6. **停止・再開**  : ⏹ で生成中断、▶ で続きから再開
7. **ファイル分析**: ファイルアップロード機能で様々なファイルに関する分析が可能
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
import error_utils          # エラー処理関連（新規追加）

# ────────────────────────────────────────────────────────────────
# 1. 初期設定
# ────────────────────────────────────────────────────────────────
# 環境設定を読み込む
settings = config.setup_environment()

# OpenAIクライアントの初期化
client = models_utils.init_openai_client(settings["OPENAI_API_KEY"])

# ────────────────────────────────────────────────────────────────
# 2. Chainlit イベントハンドラ
# ────────────────────────────────────────────────────────────────
@cl.on_chat_start
async def start():
    """チャット開始時の処理"""
    try:
        # 並列処理で初期化
        tasks = [
            # セッション変数の初期化
            init_session(),
            
            # アバターの設定
            setup_avatars(),
            
            # API確認
            check_api_status()
        ]
        
        # 並列実行
        await asyncio.gather(*tasks)
        
        if not settings["API_KEY_VALID"]:
            # APIキーがない場合は警告表示
            await cl.Message(
                content="❌ **OpenAI APIキーが設定されていないか無効です！**\n"
                        "`.env` ファイルに以下のように設定してください：\n"
                        "`OPENAI_API_KEY=\"sk-xxxx...\"`",
                actions=ui_actions.common_actions(),
                tooltip="APIキーエラー"
            ).send()
            return

        # 通常の開始処理
        await ui_actions.show_welcome_message(models_utils.MODELS)
    
    except Exception as e:
        # エラー発生時の処理
        await error_utils.handle_error(e, "チャット開始処理中")

async def init_session():
    """セッション変数の初期化"""
    # 型付きセッション変数の設定
    cl.user_session.set_typed("files", {}, Dict[str, Dict[str, Any]])
    cl.user_session.set_typed("chat_history", [], List[Dict[str, str]])
    cl.user_session.set_typed("cancel_flag", False, bool)
    cl.user_session.set_typed("partial_response", "", str)
    cl.user_session.set_typed("selected_model", "gpt-4o", str)

async def setup_avatars():
    """アバターの設定"""
    # システムアバターの設定
    await cl.Avatar(
        name="assistant",
        url="https://avatars.githubusercontent.com/u/128686189?v=4"
    ).send()
    
    # ユーザーアバターの設定（オプション）
    await cl.Avatar(
        name="user",
        url="https://ui-avatars.com/api/?name=U&background=random"
    ).send()

async def check_api_status():
    """API状態の確認"""
    if not client:
        print("[WARNING] OpenAIクライアントが初期化されていません")
        return
    
    try:
        # 軽量なAPI呼び出しでステータス確認（オプション）
        if settings["DEBUG_MODE"]:
            print("[DEBUG] API接続状態の確認をスキップしました（デバッグモード）")
    except Exception as e:
        print(f"[WARNING] API接続確認中にエラーが発生: {str(e)}")

@cl.action_callback("change_model")
async def change_model(_):
    """モデル変更アクションのコールバック"""
    try:
        await models_utils.show_model_selection_with_info()
    except Exception as e:
        await error_utils.handle_error(e, "モデル選択処理中")

@cl.action_callback("select_model")
async def model_selected(action: cl.Action):
    """モデル選択アクションのコールバック"""
    try:
        model = action.payload.get("model")
        if not model:
            raise ValueError("モデルが指定されていません")
        
        # 型付きセッション変数に保存
        cl.user_session.set_typed("selected_model", model, str)
        
        # モデル情報を取得
        model_label = models_utils.get_model_label(model)
        model_info = models_utils.get_model_info(model)
        
        # 選択したモデル情報の表示
        await cl.Message(
            content=f"{config.get_prefix(settings['DEBUG_MODE'])}✅ モデル「{model_label}」を選択しました。\n\n"
                    f"- **{model_info['description']}**\n"
                    f"- 文脈窓: {model_info['context_window']} トークン\n"
                    f"- 学習データ: {model_info['training_data']}\n\n"
                    "質問するか、ファイルをアップロードしてください！",
            actions=ui_actions.common_actions(),
            tooltip=f"モデル: {model} - {model_info['description']}"
        ).send()
    except Exception as e:
        await error_utils.handle_error(e, "モデル選択処理中")

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
            tooltip="アップロード可能なファイル形式: CSV, Excel, テキスト, JSON, PDF, 画像"
        ).send()

        # ファイル処理を切り出したモジュールに委譲
        processed_files = await file_utils.handle_file_upload(files, settings["UPLOADS_DIR"])
        
        # 処理したファイル情報をセッションに保存（型付き）
        current_files = cl.user_session.get_typed("files", Dict[str, Dict[str, Any]], {})
        current_files.update(processed_files)
        cl.user_session.set_typed("files", current_files, Dict[str, Dict[str, Any]])
    
    except Exception as e:
        await error_utils.handle_error(e, "ファイルアップロード処理中")

@cl.action_callback("show_details")
async def show_file_details(action):
    """ファイル詳細表示アクションのコールバック"""
    try:
        file_name = action.payload.get("file_name")
        if not file_name:
            raise ValueError("ファイル名が指定されていません")
        
        files = cl.user_session.get_typed("files", Dict[str, Dict[str, Any]], {})
        
        if file_name not in files:
            await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
            return
        
        file_info = files[file_name]
        
        # ファイルタイプに応じた詳細表示
        if file_info["type"] in ["csv", "excel"]:
            # 詳細分析用にファイルを完全処理
            file_info = await file_utils.analyze_file_safely(file_name, files)
            if file_info and "dataframe" in file_info:
                await file_utils.display_dataframe_details(file_info["dataframe"], file_name)
            else:
                await cl.Message(content=f"ファイル {file_name} の詳細表示に失敗しました。").send()
                
        elif file_info["type"] == "text":
            # テキストファイル詳細表示
            file_info = await file_utils.analyze_file_safely(file_name, files)
            if file_info and "full_content" in file_info:
                await cl.Message(
                    content=f"### {file_name} の全文:\n```\n{file_info['full_content']}\n```",
                    tooltip=f"テキストファイル: {file_name}"
                ).send()
            else:
                await cl.Message(content=f"ファイル {file_name} の詳細表示に失敗しました。").send()
                
        elif file_info["type"] == "json":
            # JSONファイル詳細表示
            file_info = await file_utils.analyze_file_safely(file_name, files)
            if file_info and "content" in file_info:
                json_str = json.dumps(file_info["content"], indent=2, ensure_ascii=False)
                await cl.Message(
                    content=f"### {file_name} の内容:\n```json\n{json_str}\n```",
                    tooltip=f"JSONファイル: {file_name}"
                ).send()
            else:
                await cl.Message(content=f"ファイル {file_name} の詳細表示に失敗しました。").send()
                
        else:
            await cl.Message(
                content=f"このファイル形式の詳細表示はサポートされていません: {file_info['type']}",
                tooltip="未サポートのファイル形式"
            ).send()
    
    except Exception as e:
        await error_utils.handle_error(e, "ファイル詳細表示処理中")

@cl.action_callback("analyze_file")
async def analyze_file(action):
    """ファイル分析アクションのコールバック"""
    try:
        file_name = action.payload.get("file_name")
        if not file_name:
            raise ValueError("ファイル名が指定されていません")
        
        files = cl.user_session.get_typed("files", Dict[str, Dict[str, Any]], {})
        
        if file_name not in files:
            await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
            return
        
        # 処理中メッセージの表示
        processing_msg = await ui_actions.show_processing_status(f"ファイル「{file_name}」を詳細に分析しています")
        
        # ファイルの詳細分析
        file_info = await file_utils.analyze_file_safely(file_name, files)
        if not file_info:
            processing_msg.content = f"⚠️ ファイル「{file_name}」の分析に失敗しました"
            await processing_msg.update()
            return
        
        # 処理中メッセージの更新
        processing_msg.content = f"✅ ファイル「{file_name}」の分析が完了しました"
        await processing_msg.update()
        
        # ファイルタイプに応じた処理
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
        
        # 分析のためのプロンプトを送信
        msg = cl.Message(content=prompt)
        await on_message(msg)
    
    except Exception as e:
        await error_utils.handle_error(e, "ファイル分析処理中")

# ★ 停止ボタン
@cl.action_callback("cancel")
async def cancel_stream(_):
    """生成停止アクションのコールバック"""
    try:
        # 型付きセッション変数を使用
        cl.user_session.set_typed("cancel_flag", True, bool)
        
        await cl.Message(
            content="⏹ 生成を停止します…", 
            actions=ui_actions.common_actions(show_resume=True),
            tooltip="生成が停止されました"
        ).send()
    except Exception as e:
        await error_utils.handle_error(e, "生成停止処理中")

# ★ 再開ボタン
@cl.action_callback("resume")
async def resume_stream(_):
    """生成再開アクションのコールバック"""
    try:
        # 型付きセッション変数を使用
        last_user_msg = cl.user_session.get_typed("last_user_msg", str, "")
        partial_response = cl.user_session.get_typed("partial_response", str, "")
        
        if not last_user_msg:
            await cl.Message(
                content="再開できる会話が見つかりません。", 
                tooltip="前の会話情報がありません"
            ).send()
            return
        
        # 部分的な応答があれば表示
        if partial_response:
            await cl.Message(
                content=f"**前回の途中までの応答**:\n\n{partial_response}\n\n---\n\n続きを生成しています...",
                tooltip="前回の部分応答"
            ).send()
        
        # 続きを生成するためのプロンプト
        continuation_prompt = (
            f"{last_user_msg}\n\n"
            f"[前回の応答]:\n{partial_response}\n\n"
            "続きを生成してください。"
        )
        
        # 「続きからお願いします」を追加して再度 ask_openai
        await on_message(cl.Message(content=continuation_prompt, author="user", id="resume"), resume=True)
    
    except Exception as e:
        await error_utils.handle_error(e, "生成再開処理中")

# ★ 保存ボタン（TXTフォーマットのみ）
@cl.action_callback("save")
async def save_history(_):
    """会話履歴保存アクションのコールバック"""
    try:
        # 型付きセッション変数を使用
        history = cl.user_session.get_typed("chat_history", List[Dict[str, str]], [])
        
        if not history:
            await cl.Message(
                content="保存する会話履歴がありません。", 
                tooltip="会話履歴なし"
            ).send()
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
            processing_msg.content = "⚠️ 会話履歴の保存に失敗しました"
            await processing_msg.update()
            return
        
        # 処理中メッセージの更新
        processing_msg.content = "✅ 会話履歴の保存が完了しました"
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
            elements=elements,
            tooltip="保存された会話履歴"
        ).send()
    
    except Exception as e:
        await error_utils.handle_error(e, "会話履歴保存処理中")

# ★ プロセス完全終了ボタン
@cl.action_callback("shutdown")
async def shutdown_app(_):
    """アプリケーション終了アクションのコールバック"""
    await cl.Message(
        content="🔴 サーバーを終了します…",
        tooltip="アプリケーション終了"
    ).send()
    await cl.sleep(0.5)  # メッセージ送信猶予
    os._exit(0)          # 即プロセス終了（SystemExitを無視して強制終了）

# ★ 再試行ボタン
@cl.action_callback("retry")
async def retry_action(action):
    """再試行アクションのコールバック"""
    try:
        # 前回のメッセージを取得して再送信
        last_user_msg = cl.user_session.get_typed("last_user_msg", str, "")
        if not last_user_msg:
            await cl.Message(content="再試行する会話が見つかりません。").send()
            return
        
        # 再試行メッセージを表示
        await cl.Message(content="🔄 リクエストを再試行しています...").send()
        
        # 前回のメッセージを再送信
        await on_message(cl.Message(content=last_user_msg, author="user", id="retry"))
    
    except Exception as e:
        await error_utils.handle_error(e, "再試行処理中")

# メインのメッセージハンドラ
@cl.on_message
async def on_message(msg: cl.Message, resume: bool = False):
    """メインのメッセージハンドラ"""
    try:
        # 事前状態のリセットと履歴処理
        cl.user_session.set_typed("cancel_flag", False, bool)
        history = cl.user_session.get_typed("chat_history", List[Dict[str, str]], [])
        
        if not resume:
            # メッセージをサニタイズ（セキュリティ対策）
            sanitized_content = config.sanitize_input(msg.content)
            
            # 履歴にユーザーメッセージを追加
            history.append({"role": "user", "content": sanitized_content})
            cl.user_session.set_typed("last_user_msg", sanitized_content, str)

        # モデル情報の取得
        model = cl.user_session.get_typed("selected_model", str, "gpt-4o")
        model_info = models_utils.get_model_info(model)
        
        # 応答メッセージの初期化（ツールチップ付き）
        stream_msg = cl.Message(
            content="",
            tooltip=f"モデル: {model} - {model_info['description']}"
        )
        await stream_msg.send()

        try:
            # ファイル参照がないかチェック
            files = cl.user_session.get_typed("files", Dict[str, Dict[str, Any]], {})
            message_content = msg.content
            
            # ファイル参照がある場合、関連コンテンツを追加
            message_content = file_utils.get_file_reference_content(message_content, files)
            
            # OpenAI API呼び出し
            stream = await models_utils.ask_openai(
                client, 
                message_content, 
                history, 
                model, 
                debug_mode=settings["DEBUG_MODE"]
            )
            
            # 応答を構築
            assistant_text = ""
            token_count = 0
            start_time = time.time()

            async for chunk in stream:
                # キャンセルフラグをチェック
                if cl.user_session.get_typed("cancel_flag", bool, False):
                    # ストリームを正しく閉じる
                    await stream.aclose()
                    
                    # 部分的な応答を保存
                    cl.user_session.set_typed("partial_response", assistant_text, str)
                    break
                
                # チャンク内容の取得と追加
                content = chunk.choices[0].delta.content
                if content:
                    assistant_text += content
                    token_count += 1  # 概算
                    stream_msg.content = assistant_text
                    
                    # メタデータがあれば更新
                    if hasattr(chunk, 'metadata') and chunk.metadata:
                        elapsed_ms = chunk.metadata.get("elapsed_ms", 0)
                        stream_msg.tooltip = (
                            f"モデル: {model} - {token_count}トークン - {elapsed_ms}ms"
                        )
                    
                    await stream_msg.update()

            # 応答完了時の処理
            if not cl.user_session.get_typed("cancel_flag", bool, False):
                # 処理時間の計算
                total_time = round((time.time() - start_time) * 1000)
                
                # 履歴に応答を追加
                history.append({"role": "assistant", "content": assistant_text})
                cl.user_session.set_typed("chat_history", history, List[Dict[str, str]])
                
                # 部分的な応答をクリア
                cl.user_session.set_typed("partial_response", "", str)
                
                # 最終的なツールチップ更新
                stream_msg.tooltip = (
                    f"モデル: {model} - {token_count}トークン - {total_time}ms完了"
                )
                await stream_msg.update()
                
                # 自動保存
                history_utils.save_chat_history_txt(
                    history, 
                    settings["CHAT_LOG_DIR"], 
                    settings["SESSION_ID"]
                )
                
                # 完了メッセージとアクション
                await ui_actions.show_action_buttons()

        except Exception as e:
            await error_utils.handle_error(e, "OpenAI API呼び出し中")

    except Exception as e:
        await error_utils.handle_error(e, "メッセージ処理中")
    
    finally:
        # 最終的に状態を保存
        cl.user_session.set_typed("chat_history", history, List[Dict[str, str]])

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""