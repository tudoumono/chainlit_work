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
    
    // パス情報を表示
    if (pathsElement) {
      pathsElement.innerHTML = `
        <div>
          <p><span class="path-info">環境設定ファイル:</span> <span class="path-value">${paths.envPath}</span></p>
          <p><span class="path-info">ログファイル:</span> <span class="path-value">${paths.logPath}</span></p>
          <p><span class="path-info">実行ディレクトリ:</span> <span class="path-value">${paths.exeDir}</span></p>
        </div>
      `;
    }
  } catch (err) {
    console.error('パス情報の取得に失敗しました:', err);
    if (pathsElement) {
      pathsElement.innerHTML = `
        <div class="error">
          <p>パス情報の取得に失敗しました: ${err.message}</p>
        </div>
      `;
    }
  }

  // ログファイルを開くボタンのイベントリスナー
  if (openLogButton) {
    openLogButton.addEventListener('click', async () => {
      try {
        await window.api.openLogFile();
      } catch (err) {
        showMessage('ログファイルを開けませんでした: ' + err.message, true);
      }
    });
  }

  // 実行ディレクトリを開くボタンのイベントリスナー
  if (openDirButton) {
    openDirButton.addEventListener('click', async () => {
      try {
        await window.api.showExeDir();
      } catch (err) {
        showMessage('ディレクトリを開けませんでした: ' + err.message, true);
      }
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