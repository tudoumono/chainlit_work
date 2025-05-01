/**
 * header_buttons.js ― ヘッダ右端に常駐ボタンを追加
 * ==================================================
 * 1) ⏹ Stop / 🔴 Exit  … Python 側 cancel / shutdown アクションを呼び出し
 * 2) ⚙ 設定             … API Key（パスワードマスク）＋ Debug ON/OFF を保存
 *
 * 使い方（非エンジニア向け）
 * ------------------------------------------------------------------
 * - 本ファイルは .chainlit/client/ に置き、config.toml で custom_js に登録
 * - Chainlit が DOM を描画したあと MutationObserver でヘッダを監視
 * - ボタンを一度だけ挿入し、クリック時は window.clApi.callAction()
 * ------------------------------------------------------------------
 */

/* ============================================================
 * 0. 共通：ヘッダ右端コンテナを取得するヘルパ
 * ========================================================== */
const getHeaderRight = () =>
    document.querySelector('.cly-app-bar__actions'); // 説明書リンク等が入る領域
  
  /* ============================================================
   * 1. ⏹ Stop / 🔴 Exit ボタン
   * ========================================================== */
  // (function mountStopExitButtons() {
  //   const mount = () => {
  //     const right = getHeaderRight();
  //     if (!right || document.getElementById('cly-stop-btn')) return; // 既に追加済み
  
  //     const makeBtn = (id, label, action, color) => {
  //       const btn = document.createElement('button');
  //       btn.id = id;
  //       btn.textContent = label;
  //       btn.style.cssText = `
  //         margin-left:8px; padding:4px 10px; border:none; border-radius:6px;
  //         background:${color}; color:#fff; font-size:0.75rem; cursor:pointer;
  //       `;
  //       btn.onclick = () =>
  //         window.clApi
  //           .callAction({ name: action, payload: {} })
  //           .catch(err => console.error(`[${id}]`, err));
  //       return btn;
  //     };
  //     right.appendChild(makeBtn('cly-stop-btn', '⏹ Stop', 'cancel',  '#ff914d'));
  //     right.appendChild(makeBtn('cly-exit-btn', '🔴 Exit', 'shutdown','#ff4d4d'));
  //     console.info('[HeaderBtn] Stop / Exit mounted');
  //   };
  //   new MutationObserver(mount).observe(document.body, { childList: true, subtree: true });
  // })();
  
  /* ============================================================
   * 2. ⚙ 設定ボタン（API Key + Debug モード保存）
   * ========================================================== */
  (function mountSettingsButton() {
    /* --- 2‑A: ボタン挿入 ------------------------------------------------ */
    const addButton = () => {
      const right = getHeaderRight();
      if (!right || document.getElementById('cly-settings-btn')) return;
  
      const gear = document.createElement('button');
      gear.id = 'cly-settings-btn';
      gear.textContent = '⚙ 設定';
      gear.style.cssText = `
        margin-left:8px; padding:4px 10px; border:none; border-radius:6px;
        background:#5c5c5c; color:#fff; font-size:0.75rem; cursor:pointer;
      `;
      gear.onclick = showSettingsModal;
      right.appendChild(gear);
      console.info('[HeaderBtn] Settings mounted');
    };
    new MutationObserver(addButton).observe(document.body, { childList: true, subtree: true });
  
    /* --- 2‑B: モーダル生成 ---------------------------------------------- */
    function showSettingsModal() {
      /* 既に開いていれば閉じるだけ */
      if (document.getElementById('cly-settings-overlay')) {
        closeModal(); return;
      }
  
      /* オーバーレイ */
      const overlay = document.createElement('div');
      overlay.id = 'cly-settings-overlay';
      overlay.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex;
        align-items:center; justify-content:center; z-index:9999;
      `;
  
      /* モーダル本体 */
      const modal = document.createElement('div');
      modal.style.cssText = `
        background:#1e1e1e; padding:20px 24px; border-radius:8px; width:320px;
        color:#fff; font-size:0.85rem; box-shadow:0 4px 12px rgba(0,0,0,.6);
      `;
  
      /* ラベル + 入力 */
      const lblKey = document.createElement('label');
      lblKey.textContent = 'OpenAI API Key';
      lblKey.htmlFor = 'cly-api-input';
  
      const input = document.createElement('input');
      input.type = 'password';
      input.id   = 'cly-api-input';
      input.placeholder = 'sk-...';
      input.style.cssText = `
        width:100%; padding:6px 8px; margin:6px 0 12px;
        border-radius:4px; border:1px solid #555; background:#2a2a2a; color:#fff;
      `;
  
      /* Debug チェック */
      const chkLabel = document.createElement('label');
      chkLabel.style.display = 'flex'; chkLabel.style.alignItems = 'center';
      chkLabel.style.cursor = 'pointer';
      const chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.id   = 'cly-debug-chk';
      chk.style.marginRight = '6px';
      chkLabel.appendChild(chk);
      chkLabel.appendChild(document.createTextNode('デバッグモードを有効にする'));
  
      /* ボタン */
      const btnSave = document.createElement('button');
      btnSave.textContent = '保存';
      btnSave.style.cssText = `
        margin-top:14px; padding:6px 14px; border:none; border-radius:6px;
        background:#0078d4; color:#fff; cursor:pointer;
      `;
      btnSave.onclick = async () => {
        await window.clApi.callAction({
          name: 'save_settings',
          payload: { key: input.value, debug: chk.checked }
        }).catch(e => console.error('[save_settings]', e));
        closeModal();
      };
  
      /* 閉じる */
      function closeModal() { overlay.remove(); }
  
      /* 組み立て */
      modal.appendChild(lblKey);
      modal.appendChild(input);
      modal.appendChild(chkLabel);
      modal.appendChild(btnSave);
      overlay.appendChild(modal);
      overlay.onclick = e => { if (e.target === overlay) closeModal(); };
      document.body.appendChild(overlay);
    }
  })();
  