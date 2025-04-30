@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title パッケージダウンロード

echo ===== Chainlitアプリ用のオフラインパッケージを準備しています =====

REM 必要なディレクトリを作成
mkdir python_packages 2>nul
mkdir npm_packages 2>nul
echo.

REM Pythonパッケージをダウンロード
echo [1/2] Pythonパッケージをダウンロードしています...

REM chainlit_app内のpyproject.tomlまたはrequirements.txtを使用
if exist chainlit_app\pyproject.toml (
    echo Poetry から requirements.txt を生成しています...
    cd chainlit_app
    poetry export -f requirements.txt --output ..\python_packages\requirements.txt --without-hashes
    cd ..
) else if exist chainlit_app\requirements.txt (
    echo 既存のrequirements.txtをコピーしています...
    copy chainlit_app\requirements.txt python_packages\requirements.txt
) else (
    echo エラー: chainlit_app内にrequirements.txtもpyproject.tomlも見つかりません。
    exit /b 1
)

REM Pythonパッケージをダウンロード
echo パッケージをダウンロードしています...
pip download -r python_packages\requirements.txt -d python_packages
echo Pythonパッケージのダウンロードが完了しました。
echo.

REM npmパッケージをダウンロード（ライブラリのみ、ソースコードなし）
echo [2/2] npmライブラリをダウンロードしています...

REM 一時ディレクトリを作成
mkdir npm_temp 2>nul

REM electronディレクトリにアクセス
cd electron

REM ベースディレクトリへの相対パスを保存
set BASE_DIR=..

REM package.jsonをコピー
copy package.json ..\npm_temp\ >nul

REM 一時ディレクトリにpackage.jsonから依存関係のみを抽出した新しいpackage.jsonを作成
echo {> ..\npm_temp\temp_package.json
echo   "name": "temp-package",>> ..\npm_temp\temp_package.json
echo   "version": "1.0.0",>> ..\npm_temp\temp_package.json
echo   "private": true,>> ..\npm_temp\temp_package.json
echo   "dependencies": {>> ..\npm_temp\temp_package.json

REM package.jsonから依存関係だけを抽出
for /f "tokens=1,* delims=:" %%a in ('findstr /C:"\"dependencies\"" package.json') do (
    set deps_line=%%b
    set deps_line=!deps_line:~0,1!
    if "!deps_line!"=="{" (
        for /f "tokens=1,* delims={" %%c in ("%%b") do (
            echo     %%c>> ..\npm_temp\temp_package.json
        )
    ) else (
        echo     %%b>> ..\npm_temp\temp_package.json
    )
)

echo   }>> ..\npm_temp\temp_package.json
echo }>> ..\npm_temp\temp_package.json

REM 一時ディレクトリに移動
cd ..\npm_temp

REM 主要なパッケージを明示的にダウンロード
echo Electronおよび主要パッケージをダウンロードしています...
call npm pack electron electron-builder electron-squirrel-startup tree-kill iconv-lite --quiet

REM パッケージの依存関係をダウンロード
echo temp_package.jsonから依存関係をダウンロードしています...
call npm i --package-lock-only --no-package-lock
call npm pack $(npm list --all --parseable --depth=0 | sed 's/.*node_modules\///' | sort -u) --quiet

REM 全パッケージを移動
move *.tgz ..\npm_packages\ >nul 2>&1

REM 元のディレクトリに戻る
cd ..

REM 一時ディレクトリを削除
rmdir /s /q npm_temp

echo ===== ダウンロード完了 =====
echo python_packagesディレクトリにPythonパッケージが保存されました
echo npm_packagesディレクトリにnpmライブラリが保存されました（ソースコードなし）
echo.
echo パッケージの転送を行い、オフライン環境で02_python_setup.batと03_npm_setup.batを実行してください。
pause
exit /b