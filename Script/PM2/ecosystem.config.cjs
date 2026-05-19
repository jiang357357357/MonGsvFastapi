const path = require('path');

const SCRIPT_DIR = __dirname;
const PROJECT_ROOT = path.resolve(SCRIPT_DIR, '..', '..');

// 从 .monconfig 读取端口（默认值兜底）
const fs = require('fs');
let backendPort = 40302;
let frontendPort = 40031;
try {
  const config = fs.readFileSync(path.join(PROJECT_ROOT, '.monconfig'), 'utf-8');
  const serverMatch = config.match(/^\[server\][\s\S]*?^PORT\s*=\s*(\d+)/m);
  const frontendMatch = config.match(/^\[frontend\][\s\S]*?^PORT\s*=\s*(\d+)/m);
  if (serverMatch) backendPort = parseInt(serverMatch[1], 10);
  if (frontendMatch) frontendPort = parseInt(frontendMatch[1], 10);
} catch (e) {
  // 忽略读取错误
}

const logDir = path.join(PROJECT_ROOT, 'Data', 'Logs', 'PM2');

module.exports = {
  apps: [
    {
      name: 'MonGsvBackend',
      script: path.join(PROJECT_ROOT, '.venv', 'bin', 'python'),
      args: path.join(PROJECT_ROOT, 'Code', 'FastApi', 'Main', 'run_gateway.py'),
      cwd: PROJECT_ROOT,
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '20G',
      env: {
        PYTHONUNBUFFERED: '1',
      },
      error_file: path.join(logDir, 'backend-error.log'),
      out_file: path.join(logDir, 'backend-out.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
    },
    {
      name: 'MonGsvFrontend',
      script: path.join(PROJECT_ROOT, 'Code', 'GptSov_Front', 'node_modules', '.bin', 'vite'),
      args: `preview --port ${frontendPort} --host 0.0.0.0`,
      cwd: path.join(PROJECT_ROOT, 'Code', 'GptSov_Front'),
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
      },
      error_file: path.join(logDir, 'frontend-error.log'),
      out_file: path.join(logDir, 'frontend-out.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
    },
  ],
};
