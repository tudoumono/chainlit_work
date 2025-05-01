"""
ui_actions.py - UIアクション関連のユーティリティ
============================================
ボタンアクション、UIコンポーネント生成に関する機能を提供します。
"""

import json
import chainlit as cl

def common_actions(show_resume: bool = False):
    """画面下に並べるボタンを共通関数で管理（DRY）"""
    actions = [
        cl.Action(name="save", label="保存", payload={"action": "save"}),
        cl.Action(name="change_model", label="モデル変更", payload={"action": "change_model"}),
        cl.Action(name="upload_file", label="📁 ファイルアップロード", payload={"action": "upload_file"}),
        cl.Action(name="cancel", label="⏹ 停止", payload={"action": "cancel"}),
        cl.Action(name="shutdown", label="🔴 プロセス完全終了", payload={"action": "shutdown"}),
    ]
    
    # 停止後にだけ「▶ 続き」ボタンを出す
    if show_resume:
        actions.append(cl.Action(name="resume", label="▶ 続き", payload={"action": "resume"}))
    
    return actions

async def show_model_selection(models, debug_prefix=""):
    """モデル選択UIの表示"""
    await cl.Message(
        content=f"{debug_prefix}🧠 使用するモデルを選んでください：",
        actions=[
            cl.Action(name="select_model", label=label, payload={"model": val})
            for label, val in models
        ],
    ).send()

async def show_welcome_message(models):
    """ウェルカムメッセージの表示"""
    welcome_message = (
        "👋 **OpenAI APIを使ったチャットボットへようこそ！**\n\n"
        "このアプリでは以下のことができます：\n"
        "- 💬 好きなモデルを選んでAIと対話\n"
        "- 📁 ファイルをアップロードしてAIに分析してもらう\n"
        "- ⏹ 生成途中でも中断して、▶で続きから再開\n"
        "- 💾 会話内容を保存\n\n"
        "はじめに使用するモデルを選択してください："
    )
    
    await cl.Message(
        content=welcome_message,
        actions=[
            cl.Action(name="select_model", label=label, payload={"model": val})
            for label, val in models
        ],
    ).send()