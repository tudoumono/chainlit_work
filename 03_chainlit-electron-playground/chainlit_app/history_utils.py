"""
history_utils.py - チャット履歴管理ユーティリティ
=============================================
チャット履歴の保存、セッション管理、ファイル出力に関する機能を提供します。
"""

import os
from pathlib import Path
from datetime import datetime

def save_chat_history_txt(history, chat_log_dir, session_id, is_manual=False):
    """チャット履歴をTXTファイルに保存する"""
    if not history:
        return None
    
    # 出力ディレクトリ設定
    out_dir = Path(chat_log_dir)
    out_dir.mkdir(exist_ok=True)
    
    # ファイル名（自動保存と手動保存で区別）
    prefix = "manual" if is_manual else "auto"
    filename = f"{prefix}_chat_{session_id}.txt"
    filepath = out_dir / filename
    
    # チャット履歴をテキスト形式に変換
    lines = [
        "===== チャット履歴 =====", 
        f"日時: {datetime.now():%Y/%m/%d %H:%M:%S}", 
        ""
    ]
    
    for i, msg in enumerate(history):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 役割に応じて整形
        prefix = {
            "user": f"👤 ユーザー（質問 {i//2+1}）:", 
            "assistant": f"🤖 AI（回答 {i//2+1}）:"
        }.get(role, f"📝 {role}:")
        
        lines.append(prefix)
        
        # 内容を追加（インデント付き）
        lines.extend(f"  {line}" for line in content.split("\n"))
        lines.append("")  # メッセージ間の空行
    
    # ファイルに書き込む
    filepath.write_text("\n".join(lines), encoding="utf-8")
    
    return filepath