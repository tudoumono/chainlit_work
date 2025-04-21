/**
 * main.js ― Electron ラッパー（Windows でも完全にプロセスを止める版）
 * - tree-kill で親子プロセスを一括終了
 * - console.* は UTF‑8 ログファイルにのみ出力
 */

const { app, BrowserWindow } = require('electron');
const { spawn }              = require('child_process');
const net   = require('net');
const path  = require('path');
const fs    = require('fs');
const treeKill = require('tree-kill');      // ★ 親子プロセス強制終了
let iconv;
try { iconv = require('iconv-lite'); } catch {}

/* ---------- ロガー（画面出力ゼロ・追記型） ---------- */
const logPath = path.join(__dirname, 'electron-chainlit.log');
const log     = fs.createWriteStream(logPath, { flags:'a', encoding:'utf8' });
const stamp   = () => new Date().toISOString().replace('T',' ').substring(0,19);
['log','error','warn'].forEach(m => console[m]=(...msg)=>log.write(`[${stamp()}] ${msg.join(' ')}\n`));

/* ---------- 起動パラメータ ---------- */
const PORT = 8000;
const DIR  = path.join(__dirname,'..','chainlit_app');
const CMD  = ['run','chainlit','run','main.py','-h']; // -h=headless

let python; let killed=false;

/* ---------- Chainlit 起動 ---------- */
function startChainlit(){
  python = spawn('poetry', CMD, { cwd:DIR,  env: {CHAINLIT_CONFIG_PATH: path.join(DIR, '.chainlit', 'config.toml'), } ,shell:true });
  const dec = b => iconv ? iconv.decode(b,'cp932') : b.toString();
  python.stdout.on('data',d=>console.log('[Chainlit]',dec(d).trim()));
  python.stderr.on('data',d=>console.error('[Chainlit★ERR]',dec(d).trim()));
}

/* ---------- ポート待機 ---------- */
function waitPort(timeout=15000){
  return new Promise((ok,ng)=>{
    const st=Date.now(); const t=setInterval(()=>{
      const s=new net.Socket();
      s.once('connect',()=>{clearInterval(t);s.destroy();ok();})
       .once('error',()=>{s.destroy(); if(Date.now()-st>timeout){clearInterval(t);ng('port timeout');}})
       .connect(PORT,'127.0.0.1');
    },300);
  });
}

/* ---------- ウィンドウ生成 ---------- */
function openUI(){
  const win=new BrowserWindow({width:1000,height:800});
  win.loadURL(`http://localhost:${PORT}`);

  const killTree=()=>{
    if(killed||!python) return; killed=true;
    console.log('[Electron] tree‑kill PID', python.pid);
    treeKill(python.pid, 'SIGTERM', err=>{
      if(err) console.error('[tree-kill★ERR]', err);
    });
  };
  win.on('close', killTree);   // × を押した瞬間
  win.on('closed', killTree);  // 完全に閉じた後
}

/* ---------- アプリ起動 ---------- */
app.whenReady().then(async()=>{
  startChainlit();
  try{ await waitPort(); openUI(); }
  catch(e){ console.error('[Electron★ERR]',e); if(python) treeKill(python.pid); app.quit(); }
});

app.on('window-all-closed',()=>{ if(python&&!killed) treeKill(python.pid); app.quit(); });










/* 参考
 * tree-kill : https://github.com/pkrumins/node-tree-kill
 * child_process.spawn : https://nodejs.org/api/child_process.html
 */
