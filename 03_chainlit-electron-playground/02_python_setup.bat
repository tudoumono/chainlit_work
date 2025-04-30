@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title Pythonパッケージインストール

echo ===== オフライン環境でPythonパッケージをインストールしています =====

REM requirements.txtが存在することを確認
if not exist python_packages\requirements.txt (
    echo エラー: python_packages\requirements.txt が見つかりません。
    exit /b 1
)

REM 仮想環境を作成（任意）
echo 仮想環境を作成しています...
python -m venv venv
call venv\Scripts\activate

REM ローカルにダウンロードしたパッケージをインストール
echo パッケージをインストールしています...
pip install --no-index --find-links=python_packages -r python_packages\requirements.txt

echo ===== Pythonパッケージのインストール完了 =====
pause
exit /b