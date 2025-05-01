"""
file_utils.py - ファイル処理ユーティリティ（改善版）
======================================
アップロードされたファイルの処理、分析、表示に関する機能を提供します。
・非同期処理の改善
・エラーハンドリングの強化
・進行状況の表示
"""

import os
import json
import tempfile
import traceback
import pandas as pd
import chainlit as cl
from pathlib import Path

# アップロードされたファイルの保存ディレクトリ
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(os.getenv("EXE_DIR", os.getcwd()), "uploads"))

# ファイル処理関数
def process_file(file):
    """アップロードされたファイルを処理し、内容を読み取る"""
    try:
        # ログ出力を追加して問題を特定しやすくする
        print(f"処理開始: {file.name}, パス: {file.path}")
        
        # ファイルの拡張子を取得
        file_extension = os.path.splitext(file.name)[1].lower()
        
        # 拡張子による明示的な分類（MIMEに依存しない）
        if file_extension in ['.csv']:
            return process_csv(file)
        elif file_extension in ['.xlsx', '.xls']:
            return process_excel(file)
        elif file_extension in ['.txt', '.md', '.py', '.js', '.html', '.css']:
            return process_text(file)
        elif file_extension in ['.json']:
            return process_json(file)
        elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            return {"type": "image", "path": file.path}
        elif file_extension in ['.pdf']:
            return {"type": "pdf", "path": file.path}
        else:
            print(f"未対応のファイル形式: {file_extension}")
            return {"type": "unknown", "message": f"未対応のファイル形式: {file_extension}"}
    except Exception as e:
        print(f"ファイル処理中にエラーが発生: {str(e)}")
        traceback.print_exc()  # スタックトレースを出力
        return {"type": "error", "message": f"ファイル処理エラー: {str(e)}"}

def process_csv(file):
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
            return {"type": "error", "message": "CSVファイルのエンコーディングを検出できませんでした"}
        
        # データフレームの基本情報を取得
        info = {
            "type": "csv",
            "rows": len(df),
            "columns": list(df.columns),
            "sample": df.head(5).to_dict(orient='records'),
            "path": file.path,
            "dataframe": df
        }
        return info
    except pd.errors.EmptyDataError:
        print("CSVファイルが空です")
        return {"type": "error", "message": "CSVファイルが空です"}
    except pd.errors.ParserError as e:
        print(f"CSVパースエラー: {str(e)}")
        return {"type": "error", "message": f"CSVファイルの解析に失敗しました: {str(e)}"}
    except Exception as e:
        print(f"CSVファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"CSVファイル処理エラー: {str(e)}"}

def process_excel(file):
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
                return {"type": "error", "message": "Excelファイルにシートが見つかりません"}
        
        # データフレームの基本情報を取得
        info = {
            "type": "excel",
            "rows": len(df),
            "columns": list(df.columns),
            "sample": df.head(5).to_dict(orient='records'),
            "path": file.path,
            "dataframe": df
        }
        return info
    except Exception as e:
        print(f"Excelファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"Excelファイル処理エラー: {str(e)}"}

def process_text(file):
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
            return {"type": "error", "message": "テキストファイルのエンコーディングを検出できませんでした"}
        
        # テキストの基本情報を取得
        lines = content.split('\n')
        info = {
            "type": "text",
            "lines": len(lines),
            "characters": len(content),
            "content": content[:1000] + ("..." if len(content) > 1000 else ""),
            "path": file.path,
            "full_content": content
        }
        return info
    except Exception as e:
        print(f"テキストファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"テキストファイル処理エラー: {str(e)}"}

def process_json(file):
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
                return {"type": "error", "message": f"JSONファイルの解析に失敗しました: {str(e)}"}
        
        # すべてのエンコーディングで失敗した場合
        if content is None:
            return {"type": "error", "message": "JSONファイルのエンコーディングを検出できませんでした"}
        
        # JSONの基本情報を取得
        info = {
            "type": "json",
            "content": content,
            "path": file.path
        }
        return info
    except Exception as e:
        print(f"JSONファイル処理エラー: {str(e)}")
        traceback.print_exc()
        return {"type": "error", "message": f"JSONファイル処理エラー: {str(e)}"}

def generate_file_description(file_info):
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

async def display_dataframe_details(df, filename):
    """データフレームの詳細情報を表示"""
    try:
        print(f"データフレーム詳細表示: {filename}")
        
        # 統計情報を取得
        numeric_cols = df.select_dtypes(include=['number']).columns
        stats = {}
        
        if len(numeric_cols) > 0:
            stats = df[numeric_cols].describe().to_dict()
        
        # データフレームをHTMLテーブルに変換
        html_table = df.head(10).to_html(index=False)
        
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
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                </style>
            </head>
            <body>
                <h2>データプレビュー: {filename}</h2>
                <h3>最初の10行:</h3>
                {html_table}
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
            elements=elements
        ).send()
    except Exception as e:
        print(f"データフレーム詳細表示エラー: {str(e)}")
        traceback.print_exc()
        await cl.Message(content=f"エラー: データフレームの詳細表示中に問題が発生しました: {str(e)}").send()

# ファイルアップロード処理
async def handle_file_upload(files, upload_dir=UPLOADS_DIR):
    """ファイルアップロードを処理する"""
    if not files:
        await cl.Message(content="ファイルがアップロードされませんでした。").send()
        return {}
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(upload_dir, exist_ok=True)
    print(f"アップロードディレクトリ: {upload_dir}")
    
    processed_files = {}
    
    # 古いメッセージを使わず、代わりに新しいメッセージを送信する方式に変更
    await cl.Message(content="ファイルを処理しています...").send()
    
    try:
        # 複数ファイルの場合は、それぞれ処理
        for index, file in enumerate(files):
            try:
                # 新しいメッセージを送信（更新ではなく）
                await cl.Message(content=f"ファイル {file.name} を処理中... ({index+1}/{len(files)})").send()
                
                # ファイル処理
                file_info = process_file(file)
                processed_files[file.name] = file_info
                
                # ファイル情報を表示
                file_description = generate_file_description(file_info)
                
                await cl.Message(
                    content=f"### ファイルがアップロードされました: {file.name}\n\n{file_description}",
                    actions=[
                        cl.Action(name="show_details", label="📊 詳細を見る", payload={"file_name": file.name}),
                        cl.Action(name="analyze_file", label="🔍 このファイルを分析", payload={"file_name": file.name})
                    ]
                ).send()

                
                # 画像ファイルの場合はプレビューを表示
                if file_info["type"] == "image":
                    await cl.Message(
                        content=f"画像プレビュー: {file.name}",
                        elements=[cl.Image(name=file.name, path=file.path)]
                    ).send()
                
                # PDFファイルの場合はプレビューを表示
                elif file_info["type"] == "pdf":
                    await cl.Message(
                        content=f"PDFプレビュー: {file.name}",
                        elements=[cl.File(name=file.name, path=file.path, display="inline", mime="application/pdf")]
                    ).send()
                
            except Exception as e:
                print(f"ファイル処理エラー: {str(e)}")
                import traceback
                traceback.print_exc()
                await cl.Message(content=f"エラー: {file.name}の処理中に問題が発生しました: {str(e)}").send()
                continue
        
        # 処理完了メッセージ
        await cl.Message(content="全てのファイルの処理が完了しました").send()
        
    except Exception as e:
        print(f"アップロード全体エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"エラー: ファイルアップロード処理中に問題が発生しました: {str(e)}").send()
    
    return processed_files


def get_file_reference_content(message_content, files):
    """メッセージ内のファイル参照を検出し、関連コンテンツを追加"""
    try:
        # ファイル名が特定のパターンで含まれているか確認 (例: 「ファイル名.csv について教えて」)
        file_references = []
        for file_name in files.keys():
            if file_name.lower() in message_content.lower():
                file_references.append(file_name)
        
        # ファイル参照があれば、そのファイル情報をメッセージに追加
        if file_references and not "```" in message_content:  # コードブロックがなければ
            for file_name in file_references:
                file_info = files[file_name]
                
                if file_info["type"] in ["csv", "excel"]:
                    # データフレームを文字列に変換してプロンプトに追加
                    csv_str = file_info["dataframe"].head(20).to_csv(index=False)
                    message_content += f"\n\n{file_name}の内容（最初の20行）:\n```\n{csv_str}\n```"
                
                elif file_info["type"] == "text" and len(file_info["full_content"]) < 10000:
                    # テキストファイルの内容をプロンプトに追加（短い場合のみ）
                    message_content += f"\n\n{file_name}の内容:\n```\n{file_info['full_content']}\n```"
                
                elif file_info["type"] == "json":
                    # JSONデータを文字列に変換してプロンプトに追加
                    json_str = json.dumps(file_info["content"], indent=2)
                    if len(json_str) < 10000:
                        message_content += f"\n\n{file_name}の内容:\n```json\n{json_str}\n```"
                    else:
                        message_content += f"\n\n{file_name}はJSONファイルですが、サイズが大きすぎるため全文は含めていません。"
        
        return message_content
    except Exception as e:
        print(f"ファイル参照処理エラー: {str(e)}")
        traceback.print_exc()
        # エラーが発生しても元のメッセージは返す
        return message_content