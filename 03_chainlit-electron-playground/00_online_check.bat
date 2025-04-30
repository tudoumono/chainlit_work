@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title オンライン環境準備チェック

echo ===== Chainlitアプリ開発のための環境チェック =====
echo.

REM 結果保存用の変数を初期化
set PYTHON_OK=0
set PIP_OK=0
set POETRY_OK=0
set NPM_OK=0

REM 1. Pythonのインストール状況チェック
echo [1/4] Pythonのインストール状況を確認しています...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%a in ('python --version') do set PYTHON_VERSION=%%a
    echo [OK] Python がインストールされています: !PYTHON_VERSION!
    set PYTHON_OK=1
) else (
    echo [NG] Python がインストールされていません
    echo     インストール方法: https://www.python.org/downloads/
)
echo.

REM 2. pipのインストール状況チェック
echo [2/4] pipのインストール状況を確認しています...
pip --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%a in ('pip --version 2^>^&1') do set PIP_VERSION=%%a
    echo [OK] pip がインストールされています: !PIP_VERSION:~0,30!...
    set PIP_OK=1
) else (
    echo [NG] pip がインストールされていません
    echo     通常はPythonと一緒にインストールされますが、必要に応じて:
    echo     python -m ensurepip --upgrade
)
echo.

REM 3. Poetryのインストール状況チェック
echo [3/4] Poetryのインストール状況を確認しています...
poetry --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%a in ('poetry --version') do set POETRY_VERSION=%%a
    echo [OK] Poetry がインストールされています: !POETRY_VERSION!
    set POETRY_OK=1
) else (
    echo [NG] Poetry がインストールされていません
    echo     インストール方法: 
    echo     pip install poetry
)
echo.

REM 4. npmのインストール状況チェック
echo [4/4] npmのインストール状況を確認しています...
where npm >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%a in ('npm --version 2^>^&1') do (
        set NPM_VERSION=%%a
        echo [OK] npm がインストールされています: !NPM_VERSION!
        set NPM_OK=1
    )
) else (
    echo [NG] npm がインストールされていません
    echo     インストール方法: https://nodejs.org/でNode.jsをインストール
    set NPM_OK=0
)
echo.

REM 総合判定
echo ===== チェック結果のまとめ =====
set /a TOTAL_OK=PYTHON_OK+PIP_OK+POETRY_OK+NPM_OK
if %TOTAL_OK% equ 4 (
    echo [合格] すべての必要なツールがインストールされています。
    echo       01_download_packages.bat を実行してパッケージのダウンロードを開始できます。
) else (
    echo [注意] 一部のツールがインストールされていません。上記の指示に従ってインストールしてください。
    echo       必要なツール: Python, pip, Poetry, npm
    echo       インストール後に再度このスクリプトを実行してください。
)

echo.
echo スクリプトの実行が完了しました。何かキーを押すと終了します...
pause >nul
exit /b