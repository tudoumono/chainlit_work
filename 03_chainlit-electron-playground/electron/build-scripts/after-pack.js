// build-scripts/after-pack.js
const fs = require('fs');
const path = require('path');

exports.default = async function(context) {
  // ビルド後のパッケージディレクトリのパスを取得
  const appOutDir = context.appOutDir;
  console.log(`Creating directory structure in: ${appOutDir}`);

  // 必要なディレクトリを作成
  const dirs = ['env', 'logs', 'chainlit'];
  dirs.forEach(dir => {
    const dirPath = path.join(appOutDir, dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      console.log(`Created directory: ${dirPath}`);
    }
  });

  // デフォルトの.envファイルを作成
  const defaultEnvContent = `# OpenAI APIキー（必須）
OPENAI_API_KEY=""

# デバッグモード（1=有効、0=無効）
DEBUG_MODE=0

# モデル設定
MODEL_NAME="gpt-4o"
MAX_TOKENS=2000`;

  const envPath = path.join(appOutDir, 'env', '.env');
  if (!fs.existsSync(envPath)) {
    fs.writeFileSync(envPath, defaultEnvContent, 'utf8');
    console.log(`Created default .env file: ${envPath}`);
  }

  // サンプルログファイルの作成（オプション）
  const chainlitLogPath = path.join(appOutDir, 'chainlit', 'chainlit.log');
  if (!fs.existsSync(chainlitLogPath)) {
    fs.writeFileSync(chainlitLogPath, '# Chainlit Console Log\n', 'utf8');
    console.log(`Created placeholder chainlit.log: ${chainlitLogPath}`);
  }

  console.log('After-pack process completed successfully');
};