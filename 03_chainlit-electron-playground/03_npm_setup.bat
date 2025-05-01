@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title npmパッケージインストール

echo ===== オフライン環境でnpmパッケージをインストールしています =====

REM npm_packagesディレクトリの存在を確認
if not exist npm_packages (
    echo エラー: npm_packagesディレクトリが見つかりません。
    exit /b 1
)

REM 必要なtarballが十分にあるか確認
set /a TARBALL_COUNT=0
for %%f in (npm_packages\*.tgz) do set /a TARBALL_COUNT+=1
if %TARBALL_COUNT% LSS 5 (
    echo 警告: npm_packagesディレクトリに十分なtarballファイルがありません（%TARBALL_COUNT%個）
    echo 必要なパッケージが不足している可能性があります。
    echo 続行しますか？ (Y/N)
    set /p CONFIRM=
    if /i not "!CONFIRM!"=="Y" exit /b 1
)

cd electron

REM 既存のnode_modulesをクリーンアップ
if exist node_modules (
    echo 既存のnode_modulesをクリーンアップしています...
    rmdir /s /q node_modules 2>nul
)

REM パッケージのインストール方法を選択
echo インストール方法を選択してください:
echo [1] 推奨: npm install --offline (全パッケージをまとめてインストール)
echo [2] 代替: 個別パッケージを順次インストール (問題が発生した場合)
set /p INSTALL_METHOD=選択（1または2）: 

if "%INSTALL_METHOD%"=="2" (
    echo 個別インストールを実行します...

    REM .npmrcファイルを作成
    echo registry=file:../npm_packages> .npmrc
    echo offline=true>> .npmrc

    REM ローカルキャッシュを設定
    mkdir .npm-cache 2>nul
    call npm config set cache ./npm-cache --location=project

    REM 各tarballを個別にインストール
    for %%f in (..\npm_packages\*.tgz) do (
        echo %%~nxf をインストールしています...
        call npm install "%%f" --no-save
        if !errorlevel! neq 0 (
            echo 警告: %%~nxf のインストールに問題がありました。続行します...
        )
    )

    REM .npmrcを削除
    del .npmrc 2>nul
) else (
    echo 一括インストールを実行します...

    REM .npmrcファイルを作成
    echo registry=file:../npm_packages> .npmrc
    echo offline=true>> .npmrc

    REM ローカルキャッシュを設定
    mkdir .npm-cache 2>nul
    call npm config set cache ./npm-cache --location=project

    REM すべてのパッケージを一度にインストール
    echo npmパッケージをインストールしています...
    call npm install --no-registry --offline --omit=dev --production

    if !errorlevel! neq 0 (
        echo エラー: パッケージのインストールに失敗しました。
        echo 代替方法（個別インストール）を試してください。
        del .npmrc 2>nul
        exit /b 1
    )

    REM .npmrcを削除
    del .npmrc 2>nul
)

echo ===== npmパッケージのインストール完了 =====
echo.
echo アプリケーションのビルドを行うには:
echo   cd electron
echo   npm run build
echo.
echo 注意: ビルド時に開発用パッケージが不足している場合は、
echo       npm install --production=false を実行してください。
pause
exit /b