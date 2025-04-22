/**
 * main.js ― Electron ラッパー
 * ・起動時に .env エディタを開き、
 *   「Chatを開始」クリックで Chainlit を起動 & ブラウザ表示
 * ・× を押した瞬間／完全に閉じた後に
 *   tree-kill で親子プロセスを強制終了
 */

// 必要なモジュールの読み込み
const { app, BrowserWindow, ipcMain, shell, Menu, dialog } = require('electron'); // Electronの主要機能（Menuを追加）
const { spawn } = require('child_process'); // 子プロセス（Python）を起動するため
const net = require('net'); // ネットワーク接続確認用
const path = require('path'); // ファイルパス操作用
const fs = require('fs'); // ファイル操作用
const treeKill = require('tree-kill'); // プロセスツリー全体を終了させるため

// Squirrelイベントチェック（Windows用インストーラー関連）
// Windows向けインストーラーの処理中なら、アプリを終了
if (require('electron-squirrel-startup')) app.quit();

// グローバル変数の初期化
let pythonProc = null; // Pythonプロセスを格納する変数
let killed = false; // プロセスが意図的に終了されたかどうか
let mainWindow = null; // メインウィンドウオブジェクト

const PORT = 8000; // Chainlitサーバーのポート番号

// パス設定 - アプリがパッケージ化されているかどうかで変わる
const isPackaged = app.isPackaged; // 本番ビルドかどうか

// 実行ファイルのディレクトリを取得
const EXE_DIR = path.dirname(process.execPath);
const BASE_PATH = isPackaged ? path.join(process.resourcesPath) : path.join(__dirname, '..'); // ベースパス
const DIR = path.join(BASE_PATH, 'chainlit_app'); // Chainlitアプリのディレクトリ
const PY_EMBED = path.join(BASE_PATH, 'python-3.12.4-embed', 'python.exe'); // 埋め込みPythonの実行ファイル

// 設定ファイルとログファイルを実行ファイルのディレクトリに保存
const ENV_DIR = path.join(EXE_DIR, 'env'); // 環境変数ファイル保存ディレクトリ
const LOG_DIR = path.join(EXE_DIR, 'logs'); // ログ保存ディレクトリ

// 必要なディレクトリが存在しない場合は作成
if (!fs.existsSync(ENV_DIR)) {
  fs.mkdirSync(ENV_DIR, { recursive: true }); // 再帰的に（親ディレクトリも含めて）作成
}
if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

// 環境変数ファイルのパス設定
const ENV_PATH = path.join(ENV_DIR, '.env');

const LOG_PATH = path.join(LOG_DIR, 'chainlit.log'); // ログファイルのパス

// 初回起動時、開発環境の.envをEXE_DIRにコピー
if (isPackaged && !fs.existsSync(ENV_PATH)) {
  try {
    const defaultEnvPath = path.join(DIR, '.env');
    if (fs.existsSync(defaultEnvPath)) {
      fs.copyFileSync(defaultEnvPath, ENV_PATH); // デフォルト設定をコピー
      console.log('Default .env file copied to exe directory');
    } else {
      // デフォルト環境がない場合は空ファイルを作成
      fs.writeFileSync(ENV_PATH, '', 'utf8');
      console.log('Created empty .env file in exe directory');
    }
  } catch (err) {
    console.error('Error initializing .env file:', err);
  }
}

// ── IPC ハンドラ ───────────────────────────────────────────
// .env の読込 (レンダラープロセスからの要求に対応)
ipcMain.handle('read-env', async () => {
  try {
    return fs.existsSync(ENV_PATH)
      ? fs.readFileSync(ENV_PATH, 'utf8') // ファイルが存在すれば内容を読み込む
      : ''; // なければ空文字を返す
  } catch (err) {
    console.error('Error reading .env:', err);
    return '';
  }
});

// .env の書込 (レンダラープロセスからの要求に対応)
ipcMain.handle('write-env', async (_, content) => {
  try {
    fs.writeFileSync(ENV_PATH, content, 'utf8'); // 内容をファイルに書き込む
    return true;
  } catch (err) {
    console.error('Error writing .env:', err);
    return false;
  }
});

// パス情報取得 (レンダラープロセスからの要求に対応)
ipcMain.handle('get-paths', async () => {
  return {
    envPath: ENV_PATH,
    logPath: LOG_PATH,
    exeDir: EXE_DIR
  };
});

// Chainlit 起動＆待機 → 成否を返す (レンダラープロセスからの要求に対応)
ipcMain.handle('start-chainlit', async () => {
  if (pythonProc) return true;  // 既に起動済みなら何もしない

  // パッケージ環境では.envファイルをChainlitアプリディレクトリにコピー
  if (isPackaged) {
    try {
      // 実行ディレクトリの.envファイルをChainlitアプリディレクトリにコピー
      fs.copyFileSync(ENV_PATH, path.join(DIR, '.env'));
    } catch (err) {
      console.error('Error copying .env file to app directory:', err);
    }
  }

  // Python環境変数の設定
  const pythonEnv = {
    ...process.env, // 現在の環境変数を引き継ぐ
    PYTHONHOME: path.dirname(PY_EMBED), // Pythonのホームディレクトリ
    PYTHONPATH: path.join(path.dirname(PY_EMBED), 'site-packages'), // Pythonパッケージの場所
    CHAINLIT_CONFIG_PATH: path.join(DIR, '.chainlit', 'config.toml'), // Chainlit設定ファイルの場所
    // 追加の環境変数
    PATH: `${path.dirname(PY_EMBED)};${process.env.PATH}` // PATHにPythonディレクトリを追加
  };

  // Chainlitアプリの実行
  try {
    // Pythonを実行し、Chainlitを起動
    pythonProc = spawn(PY_EMBED, ['-m', 'chainlit', 'run', path.join(DIR, 'main.py'), '-h'], {
      cwd: DIR, // 作業ディレクトリ
      env: pythonEnv, // 環境変数
      shell: false, // シェルを使わない
    });

    // ログファイルへの出力
    const log = fs.createWriteStream(LOG_PATH, { flags: 'a' }); // 'a'は追記モード
    pythonProc.stdout.pipe(log); // 標準出力をログファイルに書き込む
    pythonProc.stderr.pipe(log); // エラー出力をログファイルに書き込む

    // デバッグ用コンソール出力
    pythonProc.stdout.on('data', (data) => {
      console.log(`Chainlit stdout: ${data}`);
    });
    
    pythonProc.stderr.on('data', (data) => {
      console.error(`Chainlit stderr: ${data}`);
    });

    // プロセスエラー処理
    pythonProc.on('error', (err) => {
      console.error('Failed to start Chainlit process:', err);
      killed = true;
      pythonProc = null;
      return false;
    });

    pythonProc.on('exit', (code, signal) => {
      console.log(`Chainlit process exited with code ${code} and signal ${signal}`);
      if (!killed) {
        pythonProc = null;
      }
    });

    // サーバー起動待機（ポートが開くまで待つ）
    await new Promise((resolve, reject) => {
      const start = Date.now();
      const iv = setInterval(() => {
        const sock = new net.Socket(); // ソケット接続を試みる
        sock.once('connect', () => {
          clearInterval(iv); // 接続成功したら定期チェックを停止
          sock.destroy(); // ソケットを閉じる
          resolve();
        })
        .once('error', () => {
          sock.destroy(); // エラー時はソケットを閉じる
          if (Date.now() - start > 30000) { // 30秒以上経過したらタイムアウト
            clearInterval(iv);
            reject(new Error('Timeout waiting for Chainlit server'));
          }
        })
        .connect(PORT, '127.0.0.1'); // ローカルホストの指定ポートに接続
      }, 500); // 500ミリ秒ごとに接続チェック
    });
    
    return true;
  } catch (err) {
    console.error('Error starting/waiting for Chainlit server:', err);
    killAll(); // エラー時はプロセスを終了
    return false;
  }
});

// Chainlitページを開く (レンダラープロセスからの要求に対応)
ipcMain.handle('open-chainlit', async () => {
  const url = `http://localhost:${PORT}`;
  try {
    await mainWindow.loadURL(url); // メインウィンドウにChainlitのURLを読み込む
    return true;
  } catch (err) {
    console.error('Error opening Chainlit URL:', err);
    // フォールバック：外部ブラウザで開く
    shell.openExternal(url); // 代わりに外部ブラウザでURLを開く
    return false;
  }
});

// .env設定画面に戻る
ipcMain.handle('return-to-settings', async () => {
  try {
    // Chainlitを終了
    killAll();
    
    // .env設定画面を表示
    mainWindow.loadFile(path.join(__dirname, 'env-editor.html'));
    return true;
  } catch (err) {
    console.error('Error returning to settings:', err);
    return false;
  }
});

// ファイルを選択してログファイルを開く
ipcMain.handle('open-log-file', async () => {
  try {
    shell.openPath(LOG_PATH);
    return true;
  } catch (err) {
    console.error('Error opening log file:', err);
    return false;
  }
});

// フォルダを表示 (実行ファイルのディレクトリ)
ipcMain.handle('show-exe-dir', async () => {
  try {
    shell.openPath(EXE_DIR);
    return true;
  } catch (err) {
    console.error('Error opening directory:', err);
    return false;
  }
});

// ── プロセス殺害ヘルパー ───────────────────────────────────
function killAll() {
  if (!pythonProc || killed) return; // プロセスがないか既に終了済みなら何もしない
  
  console.log('Killing Chainlit process...');
  killed = true;
  
  try {
    // treeKillはプロセスIDを指定して、そのプロセスとその子プロセスをすべて終了させる
    treeKill(pythonProc.pid, 'SIGTERM', err => {
      if (err) console.error('tree-kill error:', err);
      pythonProc = null;
    });
  } catch (err) {
    console.error('Error in killAll function:', err);
    pythonProc = null;
  }
}

// ── ウィンドウ生成 ─────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // プリロードスクリプト
      nodeIntegration: false, // Nodeの機能をレンダラープロセスで使わない（セキュリティ対策）
      contextIsolation: true, // レンダラープロセスとプリロードスクリプトを分離（セキュリティ対策）
      webSecurity: true // Webセキュリティを有効化
    }
  });

  // CSPヘッダーの設定
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        ]
      }
    });
  });

  // 起動時は .env 編集画面を表示
  mainWindow.loadFile(path.join(__dirname, 'env-editor.html'));

  // 閉じるタイミングで Chainlit を強制終了
  mainWindow.on('close', killAll);
  mainWindow.on('closed', () => {
    killAll();
    mainWindow = null;
  });

  // 開発者ツールを開かないように変更
  // if (!isPackaged) {
  //   mainWindow.webContents.openDevTools();
  // }
}

// メニューを作成
function createMenu() {
  const template = [
    {
      label: 'ファイル',
      submenu: [
        {
          label: '設定に戻る',
          accelerator: 'CmdOrCtrl+,', // ショートカットキー
          click: async () => {
            killAll();
            mainWindow.loadFile(path.join(__dirname, 'env-editor.html'));
          }
        },
        { type: 'separator' },
        {
          label: 'ログを表示',
          click: async () => {
            shell.openPath(LOG_PATH);
          }
        },
        {
          label: '実行ディレクトリを開く',
          click: async () => {
            shell.openPath(EXE_DIR);
          }
        },
        { type: 'separator' },
        { role: 'quit', label: '終了' }
      ]
    },
    // 開発者メニュー（開発時のみ表示）
    ...(isPackaged ? [] : [
      {
        label: '開発',
        submenu: [
          { role: 'reload', label: '再読み込み' },
          { role: 'forceReload', label: '強制再読み込み' },
          { role: 'toggleDevTools', label: '開発者ツール' }
        ]
      }
    ])
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// アプリケーション初期化
app.whenReady().then(() => {
  createWindow();
  createMenu(); // メニューを作成
  
  app.on('activate', () => {
    // macOSでは、Dockアイコンクリック時に
    // 他のウィンドウが開いていなければ、アプリのウィンドウを再作成するのが一般的
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  killAll();
  
  // MacOSでは全ウィンドウが閉じられてもアプリは終了しない（標準的な動作）
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// プロセス終了時のクリーンアップ
process.on('exit', killAll);
process.on('SIGINT', () => {
  killAll(); // Ctrl+Cなどの割り込みシグナルでプロセスを終了
  app.quit();
});