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
import chainlit as cl

# ▼ 自作モジュール
import config               # 設定と初期化
import models_utils         # モデル関連
import history_utils        # チャット履歴保存関連
import ui_actions           # UIアクション関連
import file_utils           # ファイル処理関連

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
    # セッション変数の初期化
    cl.user_session.set("files", {})
    
    if not settings["OPENAI_API_KEY"]:
        # APIキーがない場合は警告表示
        await cl.Message(
            content="❌ **OpenAI APIキーが設定されていません！**\n"
                    "`.env` ファイルに以下のように設定してください：\n"
                    "`OPENAI_API_KEY=\"sk-xxxx...\"`",
            actions=ui_actions.common_actions(),
        ).send()
        return

    # 通常の開始処理
    await ui_actions.show_welcome_message(models_utils.MODELS)

@cl.action_callback("change_model")
async def change_model(_):
    await ui_actions.show_model_selection(models_utils.MODELS, config.get_prefix(settings["DEBUG_MODE"]))

@cl.action_callback("select_model")
async def model_selected(action: cl.Action):
    model = action.payload["model"]
    cl.user_session.set("selected_model", model)
    
    model_label = models_utils.get_model_label(model)
    
    await cl.Message(
        content=f"{config.get_prefix(settings['DEBUG_MODE'])}✅ モデル「{model_label}」を選択しました。質問するか、ファイルをアップロードしてください！",
        actions=ui_actions.common_actions(),
    ).send()

# ★ ファイルアップロードボタン
@cl.action_callback("upload_file")
async def upload_file_action(_):
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

@cl.action_callback("show_details")
async def show_file_details(action):
    file_name = action.payload["file_name"]
    files = cl.user_session.get("files", {})
    
    if file_name not in files:
        await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
        return
    
    file_info = files[file_name]
    
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

@cl.action_callback("analyze_file")
async def analyze_file(action):
    file_name = action.payload["file_name"]
    files = cl.user_session.get("files", {})
    
    if file_name not in files:
        await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
        return
    
    file_info = files[file_name]
    
    # ここで初めて詳細なファイル処理を行う
    try:
        await cl.Message(content=f"ファイル「{file_name}」を詳細に分析しています...").send()
        
        # ファイルタイプに応じた処理
        if file_info["type"] == "csv":
            # ここでCSVを読み込む
            df = pd.read_csv(file_info["path"])
            file_info["dataframe"] = df
            csv_str = df.head(20).to_csv(index=False)
            prompt = (
                f"以下のCSVデータ（「{file_name}」の最初の20行）を分析してください。"
                "基本的な統計情報、データの傾向、および特徴をまとめてください。\n\n"
                f"```\n{csv_str}\n```"
            )
        # その他のファイルタイプも同様に処理
        elif file_info["type"] == "pdf":
            prompt = f"PDFファイル「{file_name}」を分析してください。内容の要約や主要なポイントを説明してください。"
        else:
            prompt = f"ファイル「{file_name}」の分析をお願いします。"
        
        # 分析のためのプロンプトを送信
        msg = cl.Message(content=prompt)
        await on_message(msg)
    
    except Exception as e:
        await cl.Message(content=f"ファイル分析中にエラーが発生しました: {str(e)}").send()

# ★ 停止ボタン
@cl.action_callback("cancel")
async def cancel_stream(_):
    cl.user_session.set("cancel_flag", True)
    await cl.Message(
        content="⏹ 生成を停止します…", 
        actions=ui_actions.common_actions(show_resume=True)
    ).send()

# ★ 再開ボタン
@cl.action_callback("resume")
async def resume_stream(_):
    last_user_msg = cl.user_session.get("last_user_msg")
    if not last_user_msg:
        await cl.Message(content="再開できる会話が見つかりません。").send()
        return
    # 「続きからお願いします」を追加して再度 ask_openai
    await on_message(cl.Message(content="続きからお願いします。", author="user", id="resume"), resume=True)

# ★ 保存ボタン（TXTフォーマットのみ）
@cl.action_callback("save")
async def save_history(_):
    history = cl.user_session.get("chat_history", [])
    if not history:
        return
    
    # TXT形式で保存
    txt_fp = history_utils.save_chat_history_txt(
        history, 
        settings["CHAT_LOG_DIR"], 
        settings["SESSION_ID"], 
        is_manual=True
    )
    
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

# ★ プロセス完全終了ボタン
@cl.action_callback("shutdown")
async def shutdown_app(_):
    await cl.Message(content="🔴 サーバーを終了します…").send()
    await cl.sleep(0.1)  # メッセージ送信猶予
    os._exit(0)          # 即プロセス終了（SystemExitを無視して強制終了）

# メインのメッセージハンドラ
@cl.on_message
async def on_message(msg: cl.Message, resume: bool = False):
    """メインのメッセージハンドラ"""
    # 事前状態のリセットと履歴処理
    cl.user_session.set("cancel_flag", False)
    history = cl.user_session.get("chat_history", [])
    
    if not resume:
        history.append({"role": "user", "content": msg.content})
        cl.user_session.set("last_user_msg", msg.content)

    model = cl.user_session.get("selected_model", "gpt-4o")
    stream_msg = await cl.Message(content="").send()

    try:
        # ファイル参照がないかチェック
        files = cl.user_session.get("files", {})
        message_content = msg.content
        
        # ファイル参照がある場合、関連コンテンツを追加
        message_content = file_utils.get_file_reference_content(message_content, files)
        
        stream = await models_utils.ask_openai(
            client, 
            message_content, 
            history, 
            model, 
            debug_mode=settings["DEBUG_MODE"]
        )
        assistant_text = ""

        async for chunk in stream:
            if cl.user_session.get("cancel_flag"):
                await stream.aclose()
                break

            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                stream_msg.content += delta
                await stream_msg.update()

        if not cl.user_session.get("cancel_flag"):
            history.append({"role": "assistant", "content": assistant_text})
            # 自動保存
            history_utils.save_chat_history_txt(
                history, 
                settings["CHAT_LOG_DIR"], 
                settings["SESSION_ID"]
            )

    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {e}").send()

    finally:
        cl.user_session.set("chat_history", history)
        
        # 停止状態に応じたボタン表示
        await cl.Message(
            content="✅ 応答完了！次の操作を選んでください：",
            actions=ui_actions.common_actions(show_resume=cl.user_session.get("cancel_flag"))
        ).send()

# ────────────────────────────────────────────────────────────────
# 📚 参考リンク
# ────────────────────────────────────────────────────────────────
"""
・Chainlit 公式ドキュメント       : https://docs.chainlit.io
・OpenAI Chat API リファレンス   : https://platform.openai.com/docs/api-reference/chat
・python-dotenv 使い方            : https://pypi.org/project/python-dotenv/
"""