// -------------------------------------------------
// Renderer Process: DOM 操作担当
// -------------------------------------------------
document.getElementById('open').addEventListener('click', async () => {
    const content = await window.electronAPI.openFile(); // Preload 経由で Main へ
    if (!content) return;
  
    const obj = JSON.parse(content);        // ここはブラウザ側だけで完結
    const count = Object.keys(obj).length;
    document.getElementById('result').textContent =
      `キー数は ${count} 件です`;
  });

// ✅ ログ表示用の関数を最初に追加
function addLog(msg) {
  const li = document.createElement('li');
  li.textContent = msg;
  document.getElementById('log-area').appendChild(li);
}

  // 🔽 ここから追加（ウィンドウ制御ボタンの動作）🔽
document.getElementById('min-btn').onclick = () => window.electronAPI.minimize();
document.getElementById('max-btn').onclick = () => window.electronAPI.maximize();
document.getElementById('close-btn').onclick = () => window.electronAPI.close();



// 各ボタンにイベントを設定
document.getElementById('send-on').onclick = () => {
  window.electronAPI.sendOn();
};

document.getElementById('send-once').onclick = () => {
  window.electronAPI.sendOnce();
};

document.getElementById('send-invoke').onclick = async () => {
  const result = await window.electronAPI.sendInvoke();
  addLog(`invoke結果 → ${result}`);
};

// Main から受信したログを画面に出す
window.electronAPI.onLogReply((msg) => {
  addLog(`Mainから → ${msg}`);
});

// ブラウザアクセス
document.getElementById('load-btn').onclick = () => {
  const url = document.getElementById('url-input').value;
  if (url) {
    window.electronAPI.loadURL(url);
  }
};