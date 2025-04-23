// DOMが読み込まれたときに実行される関数
document.addEventListener('DOMContentLoaded', async () => {
  // HTML内の要素の参照を取得
  const textArea = document.getElementById('envContent');
  const saveButton = document.querySelector('button.save');
  const startChatButton = document.querySelector('button.start-chat');
  const messageElement = document.getElementById('message');
  const pathsElement = document.getElementById('paths');
  const openLogButton = document.getElementById('openLog');
  const openDirButton = document.getElementById('openDir');

  // パス情報を取得して表示
  try {
    const paths = await window.api.getPaths();
    
    // logsディレクトリ内の最新のTXTファイルを取得するための関数
    async function getLatestChatLogPath() {
      try {
        // アプリから直接最新のログファイルパスを取得（この機能はmain.jsに実装が必要）
        const logFileInfo = await window.api.getLatestChatLog();
        return logFileInfo; // { exists: true/false, path: "パス" }
      } catch (err) {
        console.error('最新のログファイル情報取得に失敗:', err);
        return { exists: false, path: paths.logPath };
      }
    }
    
  // 最新のチャットログ情報を取得
  const latestLogInfo = await window.api.getLatestChatLog();
  
  // パス情報を表示
  if (pathsElement) {
    pathsElement.innerHTML = `
      <div>
        <p><strong>環境設定ファイル:</strong> <span class="path-value">${paths.envPath}</span></p>
        <p><strong>チャットログ:</strong> <span class="path-value">${latestLogInfo.exists ? latestLogInfo.path : '(保存されたログがありません)'}</span></p>
        <p><strong>コンソールログ:</strong> <span class="path-value">${paths.consolePath}</span></p>
        <p><strong>実行ディレクトリ:</strong> <span class="path-value">${paths.exeDir}</span></p>
      </div>
    `;
  }
} catch (err) {
  console.error('パス情報の取得に失敗しました:', err);
}


  // ログファイルを開くボタンのイベントリスナー
  if (openLogButton) {
    openLogButton.addEventListener('click', async () => {
      try {
        // 最新のチャットログを開く（main.jsに実装が必要）
        await window.api.openLatestChatLog();
      } catch (err) {
        // 失敗した場合は元のログファイルを開く
        await window.api.openLogFile();
      }
    });
  }

  // 実行ディレクトリを開くボタンのイベントリスナー
  if (openDirButton) {
    openDirButton.addEventListener('click', async () => {
      await window.api.showExeDir();
    });
  }

  // 環境変数ファイルの内容を読み込む
  try {
    const content = await window.api.readEnv();
    textArea.value = content;
    showMessage('.env ファイルを読み込みました');
  } catch (err) {
    showMessage('読み込みエラー: ' + err.message, true);
  }

  // 保存ボタンのイベントリスナー
  saveButton.addEventListener('click', async () => {
    try {
      await window.api.writeEnv(textArea.value);
      showMessage('保存しました');
    } catch (err) {
      showMessage('保存エラー: ' + err.message, true);
    }
  });

  // Chat開始ボタンのイベントリスナー
  startChatButton.addEventListener('click', async () => {
    startChatButton.disabled = true;
    showMessage('Chainlitサーバーを起動中...');
    
    try {
      // 環境変数を保存
      await window.api.writeEnv(textArea.value);
      
      // Chainlitを起動
      const started = await window.api.startChainlit();
      if (started) {
        showMessage('Chainlitサーバーを起動しました');
        
        // Chainlitページを開く
        const opened = await window.api.openChainlit();
        if (!opened) {
          showMessage('ウィンドウでの表示に失敗しました。外部ブラウザで開きます。', true);
        }
      } else {
        showMessage('Chainlitサーバーの起動に失敗しました', true);
        startChatButton.disabled = false;
      }
    } catch (err) {
      showMessage('エラー: ' + err.message, true);
      startChatButton.disabled = false;
    }
  });

  // メッセージ表示関数
  function showMessage(text, isError = false) {
    if (messageElement) {
      messageElement.textContent = text;
      messageElement.className = isError ? 'error' : '';
    }
  }
});