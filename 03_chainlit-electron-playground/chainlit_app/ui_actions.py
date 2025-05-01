"""
ui_actions.py - UIアクション関連のユーティリティ
============================================
ボタンアクション、UIコンポーネント生成に関する機能を提供します。
Chainlit 2.5.5の機能を最大限に活用した実装です。
"""

import json
import chainlit as cl
import time
from typing import List, Dict, Any, Optional, Tuple, Union

def common_actions(show_resume: bool = False) -> List[cl.Action]:
    """画面下に並べるボタンを共通関数で管理（DRY）"""
    actions = [
        cl.Action(
            name="save", 
            label="保存",
            description="会話を保存します", 
            payload={"action": "save"}
        ),
        cl.Action(
            name="change_model", 
            label="モデル変更",
            description="使用するAIモデルを変更します", 
            payload={"action": "change_model"}
        ),
        cl.Action(
            name="upload_file", 
            label="ファイルアップロード",
            description="ファイルをアップロードして分析します", 
            payload={"action": "upload_file"}
        ),
        cl.Action(
            name="cancel", 
            label="停止",
            description="生成を中断します", 
            payload={"action": "cancel"}
        ),
        cl.Action(
            name="shutdown", 
            label="プロセス完全終了",
            description="アプリケーションを終了します", 
            payload={"action": "shutdown"}
        ),
    ]
    
    # 停止後にだけ「続き」ボタンを出す
    if show_resume:
        actions.append(
            cl.Action(
                name="resume", 
                label="続き",
                description="中断した生成を再開します", 
                payload={"action": "resume"}
            )
        )
    
    return actions

async def show_model_selection(models: List[Tuple[str, str]], debug_prefix: str = "") -> None:
    """モデル選択UIの表示（改善版）"""
    # 現在選択されているモデルを取得
    current_model = cl.user_session.get("selected_model", "")
    
    # タイムスタンプ（同一アクションを複数回使用するため）
    timestamp = int(time.time())
    
    # モデル選択メッセージ
    await cl.Message(
        content=f"{debug_prefix}使用するモデルを選んでください：",
        actions=[
            cl.Action(
                name="select_model", 
                label=f"{label} {' ✓' if val == current_model else ''}", 
                description=f"モデル: {val}",
                payload={"model": val, "timestamp": timestamp}
            )
            for label, val in models
        ]
    ).send()

async def show_welcome_message(models: List[Tuple[str, str]]) -> None:
    """ウェルカムメッセージの表示（改善版）"""
    welcome_message = (
        "**OpenAI APIを使ったチャットボットへようこそ！**\n\n"
        "このアプリでは以下のことができます：\n"
        "- 好きなモデルを選んでAIと対話\n"
        "- ファイルをアップロードしてAIに分析してもらう\n"
        "- 生成途中でも中断して、続きから再開\n"
        "- 会話内容を保存\n\n"
        "はじめに使用するモデルを選択してください："
    )
    
    # タイムスタンプ（同一アクションを複数回使用するため）
    timestamp = int(time.time())
    
    await cl.Message(
        content=welcome_message,
        actions=[
            cl.Action(
                name="select_model", 
                label=label, 
                description=f"モデル: {val}",
                payload={"model": val, "timestamp": timestamp}
            )
            for label, val in models
        ]
    ).send()

async def show_action_buttons(show_resume: bool = False, message: str = "次の操作を選んでください：") -> None:
    """アクションボタンを単独で表示（新機能）"""
    await cl.Message(
        content=f"{message}",
        actions=common_actions(show_resume)
    ).send()

async def show_processing_status(start_message: str) -> cl.Message:
    """処理中ステータスの表示（新機能）"""
    message = cl.Message(content=f"{start_message}...")
    await message.send()
    return message

async def show_model_info_selection(models: List[Tuple[str, str]], model_info: Dict[str, Dict[str, Any]]) -> None:
    """モデル選択UIを詳細情報付きで表示（新機能）"""
    # 現在選択されているモデル
    current_model = cl.user_session.get("selected_model", "gpt-4o")
    
    message_content = (
        "## 使用するモデルを選択してください\n\n"
        "モデルによって機能や価格が異なります。目的に合わせて選択してください。\n\n"
    )
    
    # モデルごとの情報を表に整形
    model_table = "| モデル | 特徴 | 文脈窓 | トレーニングデータ |\n"
    model_table += "| --- | --- | --- | --- |\n"
    
    for label, model_id in models:
        info = model_info.get(model_id, {})
        selected_mark = " ✓" if model_id == current_model else ""
        
        model_table += (
            f"| {label}{selected_mark} | {info.get('description', 'N/A')} | "
            f"{info.get('context_window', 'N/A')} | {info.get('training_data', 'N/A')} |\n"
        )
    
    message_content += model_table
    
    # タイムスタンプ（同一アクションを複数回使用するため）
    timestamp = int(time.time())
    
    await cl.Message(
        content=message_content,
        actions=[
            cl.Action(
                name="select_model", 
                label=label.split("(")[0], 
                description=f"{model} - {model_info.get(model, {}).get('description', 'N/A')}",
                payload={"model": model, "timestamp": timestamp}
            )
            for label, model in models
        ]
    ).send()