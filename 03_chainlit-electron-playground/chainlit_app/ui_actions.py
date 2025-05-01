"""
ui_actions.py - UIアクション関連のユーティリティ
============================================
ボタンアクション、UIコンポーネント生成に関する機能を提供します。
型安全性と拡張性を向上させた2.5.5対応版。
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
            label="💾 保存", 
            description="会話を保存します",
            payload={"action": "save", "format": "txt"}
        ),
        cl.Action(
            name="change_model", 
            label="🔄 モデル変更", 
            description="使用するAIモデルを変更します",
            payload={"action": "change_model"}
        ),
        cl.Action(
            name="upload_file", 
            label="📁 ファイルアップロード", 
            description="ファイルをアップロードして分析します",
            payload={"action": "upload_file"}
        ),
        cl.Action(
            name="cancel", 
            label="⏹ 停止", 
            description="生成を中断します",
            payload={"action": "cancel"}
        ),
        cl.Action(
            name="shutdown", 
            label="🔴 プロセス完全終了", 
            description="アプリケーションを終了します",
            payload={"action": "shutdown"}
        ),
    ]
    
    # 停止後にだけ「▶ 続き」ボタンを出す
    if show_resume:
        actions.append(
            cl.Action(
                name="resume", 
                label="▶ 続き", 
                description="中断した生成を再開します",
                payload={"action": "resume"}
            )
        )
    
    return actions

async def show_model_selection(models: List[Tuple[str, str]], debug_prefix: str = "") -> None:
    """モデル選択UIの表示（改善版）"""
    # 現在選択されているモデルを取得
    current_model = cl.user_session.get_typed("selected_model", str, "")
    
    # 現在時刻（微小の遅延を防ぐためにタイムスタンプをつける）
    timestamp = int(time.time())
    
    await cl.Message(
        content=f"{debug_prefix}🧠 使用するモデルを選んでください：",
        actions=[
            cl.Action(
                name="select_model", 
                label=f"{label} {' ✓' if val == current_model else ''}", 
                description=f"モデル: {val}",
                payload={"model": val, "timestamp": timestamp}
            )
            for label, val in models
        ],
        tooltip="モデル選択メニュー"  # ツールチップの追加
    ).send()

async def show_welcome_message(models: List[Tuple[str, str]]) -> None:
    """ウェルカムメッセージの表示（改善版）"""
    welcome_message = (
        "👋 **OpenAI APIを使ったチャットボットへようこそ！**\n\n"
        "このアプリでは以下のことができます：\n"
        "- 💬 好きなモデルを選んでAIと対話\n"
        "- 📁 ファイルをアップロードしてAIに分析してもらう\n"
        "- ⏹ 生成途中でも中断して、▶で続きから再開\n"
        "- 💾 会話内容を保存\n\n"
        "はじめに使用するモデルを選択してください："
    )
    
    # タイムスタンプの追加（微小の遅延を防ぐため）
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
        ],
        tooltip="ようこそメッセージ"  # ツールチップの追加
    ).send()

async def show_action_buttons(show_resume: bool = False, message: str = "次の操作を選んでください：") -> None:
    """アクションボタンを単独で表示（新規追加機能）"""
    await cl.Message(
        content=f"✅ {message}",
        actions=common_actions(show_resume),
        tooltip="操作メニュー"
    ).send()

async def show_error_message(error_text: str, offer_retry: bool = True) -> None:
    """エラーメッセージの表示（新規追加機能）"""
    actions = []
    if offer_retry:
        actions.append(
            cl.Action(name="retry", label="🔄 再試行", description="もう一度試す")
        )
    
    await cl.Message(
        content=f"❌ **エラーが発生しました**\n\n{error_text}",
        actions=actions,
        tooltip="エラーメッセージ"
    ).send()

async def show_success_message(success_text: str) -> None:
    """成功メッセージの表示（新規追加機能）"""
    await cl.Message(
        content=f"✅ **成功しました**\n\n{success_text}",
        tooltip="成功メッセージ"
    ).send()

async def show_processing_status(start_message: str) -> cl.Message:
    """処理中ステータスの表示（新規追加機能）"""
    message = cl.Message(content=f"⏳ {start_message}...")
    await message.send()
    return message

# チャットプロファイル関連（新規追加機能）
class ChatProfile:
    """チャットプロファイル設定情報"""
    def __init__(
        self, 
        name: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None
    ):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatProfile':
        """辞書からインスタンスを作成"""
        return cls(
            name=data.get("name", "デフォルト"),
            model=data.get("model", "gpt-4o"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1024),
            system_prompt=data.get("system_prompt")
        )

async def show_profile_selection(profiles: List[ChatProfile]) -> None:
    """プロファイル選択UIの表示（新規追加機能）"""
    # 現在のプロファイル名を取得
    current_profile_name = cl.user_session.get_typed("current_profile_name", str, "")
    
    await cl.Message(
        content="📋 **使用するプロファイルを選択してください**",
        actions=[
            cl.Action(
                name="select_profile",
                label=f"{profile.name} {' ✓' if profile.name == current_profile_name else ''}",
                description=f"モデル: {profile.model}, 温度: {profile.temperature}",
                payload={"profile_name": profile.name}
            )
            for profile in profiles
        ],
        tooltip="プロファイル選択"
    ).send()