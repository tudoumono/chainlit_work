"""
models_utils.py - モデル関連のユーティリティ
=========================================
OpenAIのモデル定義・接続・呼び出し関連の機能を提供します。
型安全性とパフォーマンスを向上させた2.5.5対応版。
"""

import time
import json
import asyncio
import traceback
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator, Union, Callable

import chainlit as cl
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

# ────────────────────────────────────────────────────────────────
# モデル定義と接続
# ────────────────────────────────────────────────────────────────

# 利用可能なモデルのリスト
MODELS: List[Tuple[str, str]] = [
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

# モデル情報マップ（参照用）
MODEL_INFO: Dict[str, Dict[str, Any]] = {
    "gpt-3.5-turbo": {
        "description": "軽量・高速・低価格のモデル",
        "context_window": 16385,
        "training_data": "2023年9月まで",
        "price_per_1k": "$0.0005",
        "strengths": ["高速", "低コスト", "一般的なタスク"]
    },
    "gpt-4o-mini": {
        "description": "GPT-4oの軽量版",
        "context_window": 128000,
        "training_data": "2023年4月まで",
        "price_per_1k": "$0.0015",
        "strengths": ["長文処理", "低コスト", "基本的な生成タスク"]
    },
    "gpt-4.1-nano": {
        "description": "最速・最安・100万トークン文脈対応",
        "context_window": 1000000,
        "training_data": "2023年12月まで",
        "price_per_1k": "$0.001",
        "strengths": ["超長文処理", "低コスト", "基本的なタスク"]
    },
    "gpt-4-turbo": {
        "description": "GPT‑4ベースの高速モデル",
        "context_window": 128000,
        "training_data": "2023年4月まで",
        "price_per_1k": "$0.01",
        "strengths": ["複雑な推論", "高品質な文章生成", "長文処理"]
    },
    "gpt-4o": {
        "description": "マルチモーダル対応の万能モデル",
        "context_window": 128000,
        "training_data": "2023年12月まで",
        "price_per_1k": "$0.01",
        "strengths": ["画像理解", "高品質な文章生成", "複雑な推論"]
    },
    "gpt-4.1-mini": {
        "description": "100万トークン文脈対応、コード特化",
        "context_window": 1000000,
        "training_data": "2023年12月まで",
        "price_per_1k": "$0.015",
        "strengths": ["超長文処理", "コード生成", "複雑なタスク"]
    },
    "gpt-4.1": {
        "description": "最新・100万トークン文脈対応、コード特化",
        "context_window": 1000000,
        "training_data": "2023年12月まで",
        "price_per_1k": "$0.03",
        "strengths": ["超長文処理", "最高品質の文章生成", "最先端の推論能力"]
    }
}

# クライアントの初期化
def init_openai_client(api_key: Optional[str]) -> Optional[AsyncOpenAI]:
    """OpenAIクライアントの初期化"""
    if not api_key:
        print("[WARNING] APIキーが設定されていません。OpenAIクライアントは初期化されません。")
        return None
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        print("[INFO] OpenAIクライアントが正常に初期化されました。")
        return client
    except Exception as e:
        print(f"[ERROR] OpenAIクライアントの初期化に失敗しました: {str(e)}")
        traceback.print_exc()
        return None

# モデル名からラベルを取得
def get_model_label(model_id: str) -> str:
    """モデルIDからラベルを取得"""
    for label, model in MODELS:
        if model == model_id:
            return label
    return model_id

# モデル情報の取得
def get_model_info(model_id: str) -> Dict[str, Any]:
    """モデルIDから詳細情報を取得"""
    return MODEL_INFO.get(model_id, {
        "description": "情報がありません",
        "context_window": "不明",
        "training_data": "不明",
        "price_per_1k": "不明",
        "strengths": []
    })

# ────────────────────────────────────────────────────────────────
# OpenAI API呼び出し
# ────────────────────────────────────────────────────────────────
async def ask_openai(
    client: AsyncOpenAI, 
    user_message: str,
    history: List[Dict[str, str]],
    model: str,
    debug_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    system_prompt: Optional[str] = None
) -> AsyncGenerator[ChatCompletionChunk, None]:
    """
    OpenAI APIに問い合わせ、ストリーミングで返すか、デバッグモードではダミー応答を返す
    
    Args:
        client: OpenAIクライアントインスタンス
        user_message: ユーザーのメッセージ
        history: 会話履歴
        model: 使用するモデル名
        debug_mode: デバッグモードのフラグ
        temperature: 生成の多様性（0.0～2.0）
        max_tokens: 最大トークン数
        system_prompt: システムプロンプト（指定があれば）
        
    Returns:
        ストリーミングレスポンスまたはダミーレスポンス
    """
    start_time = time.time()  # 処理時間計測の開始
    
    if debug_mode:
        # デバッグモード時はダミーレスポンスを生成
        async def fake_stream():
            chunks = ["（デバッグ）", "これは ", "OpenAI を ", "呼び出して ", "いません。", 
                    f"\n\nモデル: {model}", f"\n温度: {temperature}"]
            
            for chunk in chunks:
                yield type("Chunk", (), {
                    "choices": [type("Choice", (), {
                        "delta": type("Delta", (), {"content": chunk})()
                    })()],
                    "model": model,
                    "metadata": {
                        "elapsed_ms": 100,
                        "debug": True
                    }
                })()
                await asyncio.sleep(0.5)  # より自然な遅延を追加
        
        # デバッグモードをコンソールに記録
        print(f"[DEBUG] モデル: {model}, 温度: {temperature}, トークン: {max_tokens}")
        print(f"[DEBUG] ユーザーメッセージ: {user_message[:50]}...")
        
        return fake_stream()

    try:
        # メッセージの準備
        messages = []
        
        # システムプロンプトが指定されていれば追加
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 履歴を追加
        messages.extend(history)
        
        # 最新のユーザーメッセージを追加
        messages.append({"role": "user", "content": user_message})
        
        # APIコール時間とモデル情報をトラッキング
        print(f"[INFO] OpenAI API呼び出し: モデル={model}, 温度={temperature}, トークン={max_tokens}")
        
        response_stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        
        # 測定データの追加
        elapsed_ms = round((time.time() - start_time) * 1000)
        
        class EnhancedStream:
            """
            拡張されたストリームクラス - メタデータを追加
            """
            def __init__(self, original_stream, metadata):
                self.original_stream = original_stream
                self.metadata = metadata
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                try:
                    chunk = await self.original_stream.__anext__()
                    # メタデータをチャンクに追加
                    setattr(chunk, 'metadata', self.metadata)
                    return chunk
                except StopAsyncIteration:
                    raise StopAsyncIteration
            
            async def aclose(self):
                await self.original_stream.aclose()
        
        # 拡張したストリームを返す
        metadata = {
            "elapsed_ms": elapsed_ms,
            "model": model,
            "temperature": temperature,
            "start_time": start_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return EnhancedStream(response_stream, metadata)
    
    except Exception as e:
        # エラー情報を詳細に記録
        error_message = f"OpenAI API呼び出しエラー: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_message}")
        traceback.print_exc()
        
        # エラー内容をコンソールに詳細表示
        if hasattr(e, 'response'):
            try:
                error_data = e.response.json()
                print(f"[ERROR] API応答詳細: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"[ERROR] API応答の詳細取得に失敗")
        
        # エラー発生時はダミーレスポンスでエラーメッセージを返す
        async def error_stream():
            error_chunks = [
                "⚠️ APIエラーが発生しました: ",
                f"{str(e)}",
                "\n\n別のモデルを試すか、設定を変更してみてください。"
            ]
            
            for chunk in error_chunks:
                yield type("Chunk", (), {
                    "choices": [type("Choice", (), {
                        "delta": type("Delta", (), {"content": chunk})()
                    })()],
                    "model": model,
                    "metadata": {
                        "elapsed_ms": round((time.time() - start_time) * 1000),
                        "error": True,
                        "error_type": type(e).__name__
                    }
                })()
                await asyncio.sleep(0.2)
                
        return error_stream()

# モデル選択UI表示（情報付き）
async def show_model_selection_with_info() -> None:
    """モデル選択UIを詳細情報付きで表示"""
    # 現在選択されているモデルを取得
    current_model = cl.user_session.get_typed("selected_model", str, "gpt-4o")
    
    message_content = (
        "## 🧠 使用するモデルを選択してください\n\n"
        "モデルによって機能や価格が異なります。目的に合わせて選択してください。\n\n"
    )
    
    # モデルごとの詳細情報を表示
    for label, model_id in MODELS:
        info = get_model_info(model_id)
        selected_mark = " ✓" if model_id == current_model else ""
        
        message_content += (
            f"### {label}{selected_mark}\n"
            f"- {info['description']}\n"
            f"- 文脈窓: {info['context_window']} トークン\n"
            f"- 価格: {info['price_per_1k']}/1,000トークン\n\n"
        )
    
    # タイムスタンプの追加（キャッシュ回避）
    timestamp = int(time.time())
    
    await cl.Message(
        content=message_content,
        actions=[
            cl.Action(
                name="select_model", 
                label=label.split("(")[0], 
                description=f"{model} - {get_model_info(model)['description']}",
                payload={"model": model, "timestamp": timestamp}
            )
            for label, model in MODELS
        ],
        tooltip="各モデルの特徴と最適な用途"
    ).send()