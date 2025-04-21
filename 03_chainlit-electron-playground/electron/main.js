/**
 * main.js ― Electron ラッパー
 * ・起動時に .env エディタを開き、
 *   「Chatを開始」クリックで Chainlit を起動 & ブラウザ表示
 * ・× を押した瞬間／完全に閉じた後に
 *   tree-kill で親子プロセスを強制終了
 */

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');
const fs = require('fs');
const treeKill = require('tree-kill');

// Squirrelイベントチェック（Windows用インストーラー関連）
if (require('electron-squirrel-startup')) app.quit();

let pythonProc = null;
let killed = false;
let mainWindow = null;

const PORT = 8000;

// パス設定 - アプリがパッケージ化されているかどうかで変わる
const isPackaged = app.isPackaged;
const BASE_PATH = isPackaged ? path.join(process.resourcesPath) : path.join(__dirname, '..');
const DIR = path.join(BASE_PATH, 'chainlit_app');
const PY_EMBED = path.join(BASE_PATH, 'python-3.12.4-embed', 'python.exe');

// ユーザーデータディレクトリ設定
const USER_DATA_DIR = app.getPath('userData');
const ENV_DIR = path.join(USER_DATA_DIR, 'env');
const LOG_DIR = path.join(USER_DATA_DIR, 'logs');

// 必要なディレクトリが存在しない場合は作成
if (!fs.existsSync(ENV_DIR)) {
  fs.mkdirSync(ENV_DIR, { recursive: true });
}
if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

// 環境変数ファイルのパス設定
const ENV_PATH = isPackaged 
  ? path.join(ENV_DIR, '.env') 
  : path.join(DIR, '.env');

const LOG_PATH = path.join(LOG_DIR, 'chainlit.log');

// 初回起動時、開発環境の.envをユーザーデータディレクトリにコピー
if (isPackaged && !fs.existsSync(ENV_PATH)) {
  try {
    const defaultEnvPath = path.join(DIR, '.env');
    if (fs.existsSync(defaultEnvPath)) {
      fs.copyFileSync(defaultEnvPath, ENV_PATH);
      console.log('Default .env file copied to user data directory');
    } else {
      // デフォルト環境がない場合は空ファイルを作成
      fs.writeFileSync(ENV_PATH, '', 'utf8');
      console.log('Created empty .env file in user data directory');
    }
  } catch (err) {
    console.error('Error initializing .env file:', err);
  }
}

// ── IPC ハンドラ ───────────────────────────────────────────
// .env の読込
ipcMain.handle('read-env', async () => {
  try {
    return fs.existsSync(ENV_PATH)
      ? fs.readFileSync(ENV_PATH, 'utf8')
      : '';
  } catch (err) {
    console.error('Error reading .env:', err);
    return '';
  }
});

// .env の書込
ipcMain.handle('write-env', async (_, content) => {
  try {
    fs.writeFileSync(ENV_PATH, content, 'utf8');
    return true;
  } catch (err) {
    console.error('Error writing .env:', err);
    return false;
  }
});

// Chainlit 起動＆待機 → 成否を返す
ipcMain.handle('start-chainlit', async () => {
  if (pythonProc) return true;  // 既に起動済みなら何もしない

  // パッケージ環境では.envファイルをChainlitアプリディレクトリにコピー
  if (isPackaged) {
    try {
      // ユーザーデータディレクトリの.envファイルをChainlitアプリディレクトリにコピー
      fs.copyFileSync(ENV_PATH, path.join(DIR, '.env'));
    } catch (err) {
      console.error('Error copying .env file to app directory:', err);
    }
  }

  // Python環境変数の設定
  const pythonEnv = {
    ...process.env,
    PYTHONHOME: path.dirname(PY_EMBED),
    PYTHONPATH: path.join(path.dirname(PY_EMBED), 'site-packages'),
    CHAINLIT_CONFIG_PATH: path.join(DIR, '.chainlit', 'config.toml'),
    // 追加の環境変数
    PATH: `${path.dirname(PY_EMBED)};${process.env.PATH}`
  };

  // Chainlitアプリの実行
  try {
    pythonProc = spawn(PY_EMBED, ['-m', 'chainlit', 'run', path.join(DIR, 'main.py'), '-h'], {
      cwd: DIR,
      env: pythonEnv,
      shell: false,
    });

    // ログファイルへの出力
    const log = fs.createWriteStream(LOG_PATH, { flags: 'a' });
    pythonProc.stdout.pipe(log);
    pythonProc.stderr.pipe(log);

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

    // サーバー起動待機
    await new Promise((resolve, reject) => {
      const start = Date.now();
      const iv = setInterval(() => {
        const sock = new net.Socket();
        sock.once('connect', () => {
          clearInterval(iv);
          sock.destroy();
          resolve();
        })
        .once('error', () => {
          sock.destroy();
          if (Date.now() - start > 30000) {
            clearInterval(iv);
            reject(new Error('Timeout waiting for Chainlit server'));
          }
        })
        .connect(PORT, '127.0.0.1');
      }, 500);
    });
    
    return true;
  } catch (err) {
    console.error('Error starting/waiting for Chainlit server:', err);
    killAll();
    return false;
  }
});

// Chainlitページを開く
ipcMain.handle('open-chainlit', async () => {
  const url = `http://localhost:${PORT}`;
  try {
    await mainWindow.loadURL(url);
    return true;
  } catch (err) {
    console.error('Error opening Chainlit URL:', err);
    // フォールバック：外部ブラウザで開く
    shell.openExternal(url);
    return false;
  }
});

// ── プロセス殺害ヘルパー ───────────────────────────────────
function killAll() {
  if (!pythonProc || killed) return;
  
  console.log('Killing Chainlit process...');
  killed = true;
  
  try {
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
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // 起動時は .env 編集画面を表示
  mainWindow.loadFile(path.join(__dirname, 'env-editor.html'));

  // 閉じるタイミングで Chainlit を強制終了
  mainWindow.on('close', killAll);
  mainWindow.on('closed', () => {
    killAll();
    mainWindow = null;
  });

  // 開発環境ではDevToolsを開く
  if (!isPackaged) {
    mainWindow.webContents.openDevTools();
  }
}

// アプリケーション初期化
app.whenReady().then(() => {
  createWindow();
  
  app.on('activate', () => {
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
  killAll();
  app.quit();
});