"""
file_utils.py - ファイル処理ユーティリティ（改善版）
======================================
アップロードされたファイルの処理、分析、表示に関する機能を提供します。
・非同期処理の改善
・エラーハンドリングの強化
・進行状況の表示
・型安全性の向上
"""

import os
import json
import tempfile
import traceback
import time
import asyncio
import pandas as pd
import chainlit as cl
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# アップロードされたファイルの保存ディレクトリ
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(os.getenv("EXE_DIR", os.getcwd()), "uploads"))


def process_csv(file) -> Dict[str, Any]:
    """CSVファイルを処理してデータフレームに変換"""
    try:
        print(f"CSVファイル処理開始: {file.name}")
        
        # エンコーディング自動検出ロジック
        encodings = ['utf-8', 'cp932', 'shift_jis', 'latin-1']
        df = None
        
        for encoding in encodings:
            try:
                print(f"エンコーディング {encoding} で試行中...")
                df = pd.read_csv(file.path, encoding=encoding)
                print(f"成功: エンコーディング {encoding} で読み込みました")
                break
            except UnicodeDecodeError:
                print(f"エンコーディング {encoding} では読み込めませんでした")
                continue
        
        # すべてのエンコーディングで失敗した場合
        if df is None:
            return {"type": "error", "message": "CSVファイルのエンコーディングを検出できませんでした", "name": file.name}
        
        # データフレームの基本情報を取得
        info = {
            "type": "csv",
            "rows": len(df),
            "columns": list(df.columns),
            "sample": df.head(5).to_dict(orient='records'),
            "path": file.path,
            "dataframe": df,
            "name": file.name,
            "timestamp": time.time()  # 処理時刻を記録
        }
        return info
    except pd.errors.EmptyDataError:
        print("CSVファイルが空です")
        return {"type": "error", "message": "CSVファイルが空です", "name": file.name}
    except pd.errors.ParserError as e:
        print(f"CSVパースエラー: {str(e)}")
        return {"type": "error", "message": f"CSVファイルの解析に失敗しました: {str(e)}", "name": file.name}
    except Exception as e:
        print(f"CSVファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"CSVファイル処理エラー: {str(e)}", "name": file.name}

def process_excel(file) -> Dict[str, Any]:
    """Excelファイルを処理してデータフレームに変換"""
    try:
        print(f"Excelファイル処理開始: {file.name}")
        
        # Excelファイルを読み込む
        try:
            df = pd.read_excel(file.path)
        except Exception as e:
            print(f"Excel読み込みエラー: {str(e)}")
            # シート名を指定して再試行
            import openpyxl
            wb = openpyxl.load_workbook(file.path)
            sheet_names = wb.sheetnames
            print(f"利用可能なシート: {sheet_names}")
            
            if sheet_names:
                df = pd.read_excel(file.path, sheet_name=sheet_names[0])
            else:
                return {"type": "error", "message": "Excelファイルにシートが見つかりません", "name": file.name}
        
        # データフレームの基本情報を取得
        info = {
            "type": "excel",
            "rows": len(df),
            "columns": list(df.columns),
            "sample": df.head(5).to_dict(orient='records'),
            "path": file.path,
            "dataframe": df,
            "name": file.name,
            "timestamp": time.time()  # 処理時刻を記録
        }
        return info
    except Exception as e:
        print(f"Excelファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"Excelファイル処理エラー: {str(e)}", "name": file.name}

def process_text(file) -> Dict[str, Any]:
    """テキストファイルを処理"""
    try:
        print(f"テキストファイル処理開始: {file.name}")
        
        # エンコーディング自動検出ロジック
        encodings = ['utf-8', 'cp932', 'shift_jis', 'latin-1']
        content = None
        
        for encoding in encodings:
            try:
                print(f"エンコーディング {encoding} で試行中...")
                with open(file.path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"成功: エンコーディング {encoding} で読み込みました")
                break
            except UnicodeDecodeError:
                print(f"エンコーディング {encoding} では読み込めませんでした")
                continue
        
        # すべてのエンコーディングで失敗した場合
        if content is None:
            return {"type": "error", "message": "テキストファイルのエンコーディングを検出できませんでした", "name": file.name}
        
        # テキストの基本情報を取得
        lines = content.split('\n')
        info = {
            "type": "text",
            "lines": len(lines),
            "characters": len(content),
            "content": content[:1000] + ("..." if len(content) > 1000 else ""),
            "path": file.path,
            "full_content": content,
            "name": file.name,
            "timestamp": time.time()  # 処理時刻を記録
        }
        return info
    except Exception as e:
        print(f"テキストファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"テキストファイル処理エラー: {str(e)}", "name": file.name}

def process_json(file) -> Dict[str, Any]:
    """JSONファイルを処理"""
    try:
        print(f"JSONファイル処理開始: {file.name}")
        
        # エンコーディング自動検出ロジック
        encodings = ['utf-8', 'cp932', 'shift_jis', 'latin-1']
        content = None
        
        for encoding in encodings:
            try:
                print(f"エンコーディング {encoding} で試行中...")
                with open(file.path, 'r', encoding=encoding) as f:
                    content = json.load(f)
                print(f"成功: エンコーディング {encoding} で読み込みました")
                break
            except UnicodeDecodeError:
                print(f"エンコーディング {encoding} では読み込めませんでした")
                continue
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {str(e)}")
                return {"type": "error", "message": f"JSONファイルの解析に失敗しました: {str(e)}", "name": file.name}
        
        # すべてのエンコーディングで失敗した場合
        if content is None:
            return {"type": "error", "message": "JSONファイルのエンコーディングを検出できませんでした", "name": file.name}
        
        # JSONの基本情報を取得
        info = {
            "type": "json",
            "content": content,
            "path": file.path,
            "name": file.name,
            "timestamp": time.time()  # 処理時刻を記録
        }
        return info
    except Exception as e:
        print(f"JSONファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"JSONファイル処理エラー: {str(e)}", "name": file.name}

def generate_file_description(file_info: Dict[str, Any]) -> str:
    """ファイル情報から説明文を生成"""
    if file_info["type"] == "error":
        return f"❌ エラー: {file_info['message']}"
    
    if file_info["type"] == "csv" or file_info["type"] == "excel":
        columns_str = ", ".join(file_info["columns"][:10])
        if len(file_info["columns"]) > 10:
            columns_str += "..."
        
        return (
            f"📊 **{file_info['type'].upper()}ファイル情報**\n"
            f"- 行数: {file_info['rows']} 行\n"
            f"- 列: {columns_str}\n"
            f"- サンプルデータ (最初の5行): 表示するには '詳細を見る' を選択してください"
        )
    
    elif file_info["type"] == "text":
        return (
            f"📝 **テキストファイル情報**\n"
            f"- 行数: {file_info['lines']} 行\n"
            f"- 文字数: {file_info['characters']} 文字\n"
            f"- 内容プレビュー:\n```\n{file_info['content'][:500]}...\n```"
        )
    
    elif file_info["type"] == "json":
        return f"🔍 **JSONファイル**\nJSONデータが読み込まれました。質問してください。"
    
    elif file_info["type"] == "image":
        return f"🖼️ **画像ファイル**\n画像ファイルがアップロードされました。"
    
    elif file_info["type"] == "pdf":
        return f"📄 **PDFファイル**\nPDFファイルがアップロードされました。"
    
    else:
        return f"❓ **不明なファイル形式**\nこのファイル形式は完全にはサポートされていません。"

async def display_dataframe_details(df: pd.DataFrame, filename: str) -> None:
    """データフレームの詳細情報を表示"""
    try:
        print(f"データフレーム詳細表示: {filename}")
        
        # 統計情報を取得
        numeric_cols = df.select_dtypes(include=['number']).columns
        stats = {}
        
        if len(numeric_cols) > 0:
            stats = df[numeric_cols].describe().to_dict()
        
        # データフレームをHTMLテーブルに変換
        html_table = df.head(10).to_html(index=False, classes="table table-striped table-hover")
        
        # htmlファイルとして一時保存
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        with open(temp_file.name, 'w', encoding='utf-8') as f:
            f.write(f"""
            <html>
            <head>
                <title>データプレビュー: {filename}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    .table-striped tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .table-hover tr:hover {{ background-color: #f0f0f0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #4CAF50; color: white; }}
                </style>
            </head>
            <body>
                <h2>データプレビュー: {filename}</h2>
                <h3>最初の10行:</h3>
                {html_table}
                <div style="margin-top: 20px; color: #666;">
                    <p>表示時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """)
        
        # ファイルをエレメントとして表示
        elements = [
            cl.File(
                name=f"{filename}_preview.html",
                path=temp_file.name,
                display="inline",
                mime="text/html"
            )
        ]
        
        # 統計情報のテキスト作成
        stats_text = "### 統計情報（数値列のみ）\n"
        if stats:
            for col, values in stats.items():
                stats_text += f"\n#### {col}\n"
                for stat, val in values.items():
                    stats_text += f"- {stat}: {val:.2f}\n"
        else:
            stats_text += "\n数値列がありません。"
        
        await cl.Message(
            content=f"## {filename} の詳細\n\n"
                    f"- 行数: {len(df)} 行\n"
                    f"- 列数: {len(df.columns)} 列\n\n"
                    f"{stats_text}",
            elements=elements,
        ).send()
    except Exception as e:
        print(f"データフレーム詳細表示エラー: {str(e)}")
        traceback.print_exc()
        await cl.Message(content=f"エラー: データフレームの詳細表示中に問題が発生しました: {str(e)}").send()

async def handle_file_upload(files, upload_dir=UPLOADS_DIR) -> Dict[str, Dict[str, Any]]:
    """ファイルアップロードを処理する（改善版）"""
    if not files:
        await cl.Message(content="ファイルがアップロードされませんでした。").send()
        return {}
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(upload_dir, exist_ok=True)
    
    processed_files = {}
    
    # 処理開始メッセージ
    processing_msg = cl.Message(content="ファイルを処理しています...")
    await processing_msg.send()
    
    try:
        # 全ファイルを処理
        for file in files:
            try:
                # ファイルメッセージを表示
                file_msg = cl.Message(content=f"ファイル {file.name} を処理中...")
                await file_msg.send()
                
                # デバッグログ追加
                print(f"DEBUG: ファイル処理開始: {file.name}, パス: {file.path}")
                
                # process_fileを呼び出して完全に処理
                file_info = process_file(file)
                print(f"DEBUG: process_file完了: {file.name}, 結果: {file_info['type'] if file_info and 'type' in file_info else 'unknown'}")
                
                # 辞書に情報を保存
                processed_files[file.name] = file_info
                
                # ファイル処理の完了通知と詳細アクション
                file_msg.content = f"### ファイル『{file.name}』が正常に読み込まれました"
                file_msg.actions = [
                    cl.Action(
                        name="analyze_file", 
                        label="🔍 このファイルを分析", 
                        payload={"file_name": file.name},
                        description="AIにファイルの内容を分析させます"
                    ),
                    cl.Action(
                        name="show_details", 
                        label="📋 詳細を見る", 
                        payload={"file_name": file.name},
                        description="ファイルの詳細情報を表示します"
                    )
                ]
                file_msg.tooltip = f"ファイル: {file.name} - {file_info['type']}型"
                await file_msg.update()
                
                # ファイルタイプに応じたプレビュー表示
                if file_info["type"] == "image":
                    await cl.Message(
                        content=f"画像プレビュー: {file.name}",
                        elements=[cl.Image(name=file.name, path=file.path)],
                    ).send()
                elif file_info["type"] == "pdf":
                    await cl.Message(
                        content=f"PDFプレビュー: {file.name}",
                        elements=[cl.File(name=file.name, path=file.path, 
                                         display="inline", mime="application/pdf")],
                    ).send()
                
                # 処理の安定性向上のため短い待機を入れる
                await cl.sleep(0.5)
            
            except Exception as e:
                # エラー処理の改善
                error_msg = f"エラー: {file.name}の処理中に問題が発生しました: {str(e)}"
                print(f"[ERROR] {error_msg}\n{traceback.format_exc()}")
                await cl.Message(content=error_msg).send()
        
        # 処理完了メッセージの更新
        processing_msg.content = "✅ 全てのファイルの処理が完了しました"
        processing_msg.tooltip = f"処理完了: {len(files)}ファイル"
        await processing_msg.update()
        
        # # ヘルプメッセージ
        # if processed_files:
        #     await cl.Message(
        #         content="ファイルについて質問してください。例：\n"
        #                "- このCSVの要約を教えて\n"
        #                "- データの傾向を分析して\n"
        #                "- この画像に何が写っている？",
        #     ).send()
        
        # ★追加部分: ファイル処理後、自動的に最初のファイルの分析を行う
        if processed_files and len(processed_files) > 0:
            first_file_name = list(processed_files.keys())[0]
            
            # ★重要な追加: 最初のファイルを自動的に分析
            analysis_msg = cl.Message(content=f"ファイル「{first_file_name}」の分析結果:")
            await analysis_msg.send()
            
            try:
                # ファイル情報を取得して分析
                file_info = processed_files[first_file_name]
                
                # ファイルタイプに応じた基本分析を実行
                if file_info["type"] == "text" and "full_content" in file_info:
                    content = file_info["full_content"]
                    if len(content) > 1000:
                        content_preview = content[:1000] + "...(省略)..."
                    else:
                        content_preview = content
                    
                    analysis_msg.content = (
                        f"### ファイル「{first_file_name}」の基本分析\n\n"
                        f"**タイプ**: テキストファイル\n"
                        f"**行数**: {content.count('\\n') + 1}行\n"
                        f"**文字数**: {len(content)}文字\n\n"
                        f"**内容プレビュー**:\n```\n{content_preview}\n```\n\n"
                        "より詳細な分析を行うには、質問を入力してください。"
                    )
                    await analysis_msg.update()
                    
                elif file_info["type"] in ["csv", "excel"] and "dataframe" in file_info:
                    df = file_info["dataframe"]
                    csv_preview = df.head(5).to_csv(index=False)
                    
                    analysis_msg.content = (
                        f"### ファイル「{first_file_name}」の基本分析\n\n"
                        f"**タイプ**: {file_info['type'].upper()}ファイル\n"
                        f"**行数**: {len(df)}行\n"
                        f"**列数**: {len(df.columns)}列\n"
                        f"**列名**: {', '.join(df.columns)}\n\n"
                        f"**データプレビュー**:\n```\n{csv_preview}\n```\n\n"
                        "より詳細な分析を行うには、質問を入力してください。"
                    )
                    await analysis_msg.update()
                    
                else:
                    analysis_msg.content = (
                        f"### ファイル「{first_file_name}」の基本情報\n\n"
                        f"**タイプ**: {file_info['type']}\n\n"
                        "このファイルについて質問してください。"
                    )
                    await analysis_msg.update()
                    
            except Exception as e:
                print(f"自動分析エラー: {str(e)}")
                traceback.print_exc()
                analysis_msg.content = f"ファイル「{first_file_name}」の分析中にエラーが発生しました: {str(e)}"
                await analysis_msg.update()
        
    except Exception as e:
        error_msg = f"エラー: ファイル処理中に問題が発生しました: {str(e)}"
        print(f"[ERROR] {error_msg}\n{traceback.format_exc()}")
        await cl.Message(content=error_msg).send()
    
    return processed_files

# file_utils.py - get_file_type関数と関連処理
def get_file_type(extension: str) -> str:
    """ファイル拡張子からタイプを判断する改良関数"""
    # 拡張子を小文字に変換して前のドットを削除
    ext = extension.lower()
    if not ext.startswith('.'):
        ext = '.' + ext
    
    # ★ここが重要な修正★: より詳細な拡張子分類
    # テキスト系
    if ext in ['.txt', '.md', '.py', '.js', '.html', '.css']:
        return "text"
    
    # 構造化データ
    elif ext == '.json':
        return "json"
    
    # 表形式データ
    elif ext == '.csv':
        return "csv"
    elif ext in ['.xlsx', '.xls']:
        return "excel"
    
    # メディア
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
        return "image"
    elif ext == '.pdf':
        return "pdf"
    
    # 未知の形式
    else:
        # MIMEタイプから推測を試みる
        try:
            import mimetypes
            mime_type = mimetypes.guess_type('dummy' + ext)[0]
            if mime_type:
                if mime_type.startswith('text/'):
                    return "text"
                elif mime_type.startswith('image/'):
                    return "image"
                elif 'pdf' in mime_type:
                    return "pdf"
                elif 'json' in mime_type:
                    return "json"
                elif 'csv' in mime_type or 'comma-separated' in mime_type:
                    return "csv"
                elif 'excel' in mime_type or 'spreadsheet' in mime_type:
                    return "excel"
        except:
            pass
        
        # 推測できない場合はunknown
        return "unknown"

# process_file関数の改善
def process_file(file) -> Dict[str, Any]:
    """アップロードされたファイルを処理し、内容を読み取る（改善版）"""
    try:
        # ログ出力を追加して問題を特定しやすくする
        print(f"処理開始: {file.name}, パス: {file.path}")
        
        # ファイルの拡張子とMIMEタイプを取得
        file_extension = os.path.splitext(file.name)[1].lower()
        mime_type = getattr(file, 'mime', None)
        
        print(f"MIME: {mime_type}, 拡張子: {file_extension}")
        
        # ★ここが重要な修正★: 拡張子による明示的な分類（MIMEに依存しない）
        file_type = get_file_type(file_extension)
        
        # MIMEタイプが拡張子と矛盾する場合は修正
        if mime_type == 'application/octet-stream' and file_type != 'unknown':
            # MIMEタイプが未知でも拡張子から判断できる場合
            print(f"MIMEタイプが不明ですが、拡張子から{file_type}と判断します")
        elif mime_type and 'text' in mime_type and file_extension == '.md':
            # Markdownファイルの特別処理
            file_type = 'text'
            print(f"Markdownファイルを{file_type}として処理します")
        
        # ファイル種類に応じた処理
        if file_type == "csv":
            return process_csv(file)
        elif file_type == "excel":
            return process_excel(file)
        elif file_type == "text":
            return process_text(file)
        elif file_type == "json":
            return process_json(file)
        elif file_type == "image":
            return {"type": "image", "path": file.path, "name": file.name}
        elif file_type == "pdf":
            return {"type": "pdf", "path": file.path, "name": file.name}
        else:
            print(f"未対応のファイル形式: {file_extension} (MIME: {mime_type})")
            return {"type": "unknown", "message": f"未対応のファイル形式: {file_extension}", "name": file.name}
    except Exception as e:
        print(f"ファイル処理中にエラーが発生: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"ファイル処理エラー: {str(e)}", "name": file.name}

# file_utils.py - get_file_reference_content関数
def get_file_reference_content(message_content: str, files: Dict[str, Dict[str, Any]]) -> str:
    """メッセージ内のファイル参照を検出し、関連コンテンツを追加（完全再構築版）"""
    try:
        if not files or not message_content:
            return message_content
        
        # デバッグログ
        print(f"ファイル参照検索: メッセージ[{message_content}]")
        print(f"利用可能ファイル: {list(files.keys())}")
        
        # ファイルを自動的に追加するようにする
        # メッセージの内容に関わらず、直近でアップロードされたファイルの内容を添付
        # これにより、ユーザーが明示的にファイル名を参照しなくても内容が反映される
        recent_files = sorted(files.items(), key=lambda x: x[1].get('timestamp', 0), reverse=True)
        
        if recent_files and "```" not in message_content:
            # 最新のファイルを取得
            file_name, file_info = recent_files[0]
            
            # メッセージの先頭に「最近アップロードされたファイル情報を考慮してください」と追加
            message_content = f"以下の最近アップロードされたファイル {file_name} を参照してください:\n\n" + message_content
            
            # ファイルの内容に基づいて適切な情報を追加
            if file_info["type"] in ["csv", "excel"] and "dataframe" in file_info:
                df = file_info["dataframe"]
                csv_str = df.head(10).to_csv(index=False)
                message_content += f"\n\n{file_name}の内容（最初の10行）:\n```\n{csv_str}\n```"
            
            elif file_info["type"] == "text" and "full_content" in file_info:
                content = file_info["full_content"]
                if len(content) > 2000:
                    content = content[:2000] + "...(省略)..."
                message_content += f"\n\n{file_name}の内容:\n```\n{content}\n```"
            
            elif file_info["type"] == "json" and "content" in file_info:
                json_str = json.dumps(file_info["content"], indent=2, ensure_ascii=False)
                if len(json_str) > 2000:
                    json_str = json_str[:2000] + "...(省略)..."
                message_content += f"\n\n{file_name}の内容:\n```json\n{json_str}\n```"
            
            print(f"ファイル内容を追加しました: {file_name}")
        
        return message_content
    except Exception as e:
        print(f"ファイル参照処理エラー: {str(e)}")
        traceback.print_exc()
        return message_content

# 詳細な処理のためのユーティリティ関数（エラーハンドリングのサポート）
async def analyze_file_safely(file_name: str, files: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """ファイルを安全に詳細分析する（エラーハンドリングを含む）"""
    try:
        if file_name not in files:
            await cl.Message(content=f"エラー: ファイル {file_name} が見つかりません。").send()
            return None
        
        file_info = files[file_name]
        
        # まだ詳細処理されていないファイルの場合は完全処理を行う
        if file_info["type"] == "csv" and "dataframe" not in file_info:
            result = process_csv(cl.UploadFile(path=file_info["path"], name=file_name))
            files[file_name].update(result)
            file_info = files[file_name]
        
        elif file_info["type"] == "excel" and "dataframe" not in file_info:
            result = process_excel(cl.UploadFile(path=file_info["path"], name=file_name))
            files[file_name].update(result)
            file_info = files[file_name]
        
        elif file_info["type"] == "text" and "full_content" not in file_info:
            result = process_text(cl.UploadFile(path=file_info["path"], name=file_name))
            files[file_name].update(result)
            file_info = files[file_name]
        
        elif file_info["type"] == "json" and "content" not in file_info:
            result = process_json(cl.UploadFile(path=file_info["path"], name=file_name))
            files[file_name].update(result)
            file_info = files[file_name]
        
        return file_info
    
    except Exception as e:
        error_msg = f"ファイル {file_name} の分析中にエラーが発生しました: {str(e)}"
        print(f"[ERROR] {error_msg}\n{traceback.format_exc()}")
        await cl.Message(content=error_msg).send()
        return None