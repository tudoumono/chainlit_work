"""
models_utils.py - モデル関連のユーティリティ
=========================================
OpenAIのモデル定義・接続・呼び出し関連の機能を提供します。
"""

import chainlit as cl
from openai import AsyncOpenAI

# ────────────────────────────────────────────────────────────────
# モデル定義と接続
# ────────────────────────────────────────────────────────────────

# 利用可能なモデルのリスト
MODELS = [
    # 効率的・低コストモデル
    ("GPT‑3.5 Turbo(軽量・高速・低価格)", "gpt-3.5-turbo"),         # 軽量・高速・低価格
    ("GPT‑4o mini(GPT-4oの軽量版)", "gpt-4o-mini"),             # GPT-4oの軽量版
    ("GPT‑4.1 nano(最速・最安・100万トークン文脈)", "gpt-4.1-nano"),           # 最速・最安・100万トークン文脈
    
    # 標準モデル
    ("GPT‑4 Turbo(GPT‑4ベースの高速モデル)", "gpt-4-turbo"),             # GPT‑4ベースの高速モデル
    ("GPT‑4o(マルチモーダル対応)", "gpt-4o"),                       # マルチモーダル対応
    
    # 高性能モデル
    ("GPT‑4.1 mini(100万トークン文脈、コード特化)", "gpt-4.1-mini"),           # 100万トークン文脈、コード特化
    ("GPT‑4.1(最新・100万トークン文脈、コード特化)", "gpt-4.1"),                     # 最新・100万トークン文脈、コード特化
]

# クライアントの初期化
def init_openai_client(api_key):
    """OpenAIクライアントの初期化"""
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key)

# モデル名からラベルを取得
def get_model_label(model_id):
    """モデルIDからラベルを取得"""
    for label, model in MODELS:
        if model == model_id:
            return label
    return model_id

# ────────────────────────────────────────────────────────────────
# OpenAI API呼び出し
# ────────────────────────────────────────────────────────────────
async def ask_openai(client, 
                     user_message: str,
                     history: list[dict],
                     model: str,
                     debug_mode: bool = False,
                     temperature: float = 0.7,
                     max_tokens: int = 1024):
    """
    * 普段:   OpenAI に問い合わせ、ストリーミングで返す
    * デバッグ: ダミー文字列を返す
    """
    if debug_mode:
        # デバッグモード時はダミーレスポンスを生成
        async def fake_stream():
            chunks = ["（デバッグ）", "これは ", "OpenAI を ", "呼び出して ", "いません。"]
            for chunk in chunks:
                yield type("Chunk", (), {
                    "choices": [type("Choice", (), {
                        "delta": type("Delta", (), {"content": chunk})()
                    })()]
                })()
                await cl.sleep(0.5)  # より自然な遅延を追加
        return fake_stream()

    # 通常のOpenAI呼び出し
    messages = history + [{"role": "user", "content": user_message}]
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )