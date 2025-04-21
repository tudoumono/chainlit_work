# 📁 プロジェクト構成

| ファイル / ディレクトリ | 説明 |
|--------------------------|------|
| `main.py` | Chainlit アプリのメインスクリプト。ユーザー入力を受け取り、OpenAI API またはデバッグ応答で返答します。チャット履歴の保存にも対応。 |
| `pyproject.toml` | Poetry 用の設定ファイル。プロジェクト名、Pythonバージョン、依存ライブラリなどを定義します。 |
| `poetry.lock` | インストールされたライブラリのバージョンを固定するためのファイル。環境の再現性を保ちます。 |
| `README.md` | プロジェクトの概要や使い方を記載する説明ファイルです。 |
| `chainlit.md` | Chainlit 起動時のウェルカム画面に表示される内容をマークダウンで記述します。 |
| `.chainlit/` | Chainlit により自動生成される設定ファイルや翻訳ファイルが格納されます。 |
| `chatlogs/` | チャットの履歴が JSON 形式で保存されるディレクトリです。 |
| `__pycache__/` | Python が自動生成するキャッシュファイルが保存されます。 |

---

## 🧠 対応モデルと切替機能

このアプリでは、以下の OpenAI モデルに対応しています：

- `gpt-3.5-turbo`（高速・低価格）
- `gpt-4-turbo`（高性能・安定性重視）
- `gpt-4o`（最新のマルチモーダルモデル）

起動直後やチャット中にも、画面上の「モデル変更」ボタンで好きなタイミングで切り替え可能です。

---

### 🧪 デバッグモード

APIキーが不要な「デバッグモード」も用意しています。  
環境変数 `.env` に `DEBUG_MODE=1` を指定することで、OpenAI への接続を行わず、ダミー応答が返されます。

これは PowerShell での実行例です：

ありがとうございます。ご提示いただいたMarkdownのコードブロックに対して `MD031`（コードブロックの前後に空行が必要）エラーを解消するための **修正例** は以下の通りです。

---

### ✅ 修正後のMarkdown（MD031対応済み）

これは PowerShell での実行例です：

```bash
# PowerShell の例
$env:DEBUG_MODE="1"; poetry run chainlit run main.py
```

ダミー応答は以下のように送信されます：

```bash
（デバッグ）これは OpenAI を 呼び出して いません。
```

---

### 📝 チャット履歴の保存

- 「保存」ボタンをクリックすることで、やり取りを `chatlogs/` ディレクトリに JSON 形式で保存できます。
- ファイル名にはセッション日時が含まれます（例：`session_20250420_123456.json`）

---

### 📚 参考リンク

- [Chainlit 公式ドキュメント](https://docs.chainlit.io)
- [OpenAI Chat API リファレンス](https://platform.openai.com/docs/api-reference/chat)
- [python-dotenv 公式](https://pypi.org/project/python-dotenv/)
