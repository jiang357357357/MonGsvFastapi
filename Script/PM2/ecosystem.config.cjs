const fs = require('fs');
const path = require('path');

const SCRIPT_DIR = __dirname;
const PROJECT_ROOT = path.resolve(SCRIPT_DIR, '..', '..');
const FRONTEND_DIR = path.join(PROJECT_ROOT, 'Code', 'GptSov_Front');
const LOG_DIR = path.join(PROJECT_ROOT, 'Data', 'Logs', 'PM2');

function readMonConfig() {
  const defaults = {
    backendHost: '0.0.0.0',
    backendPort: 40302,
    frontendHost: '0.0.0.0',
    frontendPort: 40031,
  };
  const configPath = path.join(PROJECT_ROOT, '.monconfig');
  if (!fs.existsSync(configPath)) {
    return defaults;
  }

  const content = fs.readFileSync(configPath, 'utf-8');
  const readValue = (section, key, fallback) => {
    const sectionMatch = content.match(new RegExp(`^\\[${section}\\]([\\s\\S]*?)(?=^\\[|$)`, 'm'));
    if (!sectionMatch) {
      return fallback;
    }
    const keyMatch = sectionMatch[1].match(new RegExp(`^${key}\\s*=\\s*(.+)$`, 'm'));
    return keyMatch ? keyMatch[1].trim() : fallback;
  };

  return {
    backendHost: readValue('server', 'HOST', defaults.backendHost),
    backendPort: Number.parseInt(readValue('server', 'PORT', String(defaults.backendPort)), 10),
    frontendHost: readValue('frontend', 'HOST', defaults.frontendHost),
    frontendPort: Number.parseInt(readValue('frontend', 'PORT', String(defaults.frontendPort)), 10),
  };
}

function pythonExecutable() {
  const candidates = process.platform === 'win32'
    ? [
        path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe'),
        path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python'),
      ]
    : [
        path.join(PROJECT_ROOT, '.venv', 'bin', 'python'),
      ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return 'python';
}

fs.mkdirSync(LOG_DIR, { recursive: true });

const config = readMonConfig();
const viteEntry = path.join(FRONTEND_DIR, 'node_modules', 'vite', 'bin', 'vite.js');
const frontendDist = path.join(FRONTEND_DIR, 'dist');

if (!fs.existsSync(frontendDist)) {
  console.warn(`[pm2] Frontend dist not found: ${frontendDist}`);
  console.warn('[pm2] Run `npm run build` in Code/GptSov_Front before starting production preview.');
}

module.exports = {
  apps: [
    {
      name: 'MonGsvBackend',
      script: path.join(PROJECT_ROOT, 'Code', 'FastApi', 'Main', 'run_gateway.py'),
      args: [
        'start',
        '--host',
        config.backendHost,
        '--port',
        String(config.backendPort),
        '--no-reload',
      ],
      cwd: PROJECT_ROOT,
      interpreter: pythonExecutable(),
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '20G',
      env: {
        MON_GSV_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        PYTHONUTF8: '1',
      },
      error_file: path.join(LOG_DIR, 'backend-error.log'),
      out_file: path.join(LOG_DIR, 'backend-out.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
    },
    {
      name: 'MonGsvFrontend',
      script: viteEntry,
      args: [
        'preview',
        '--host',
        config.frontendHost,
        '--port',
        String(config.frontendPort),
      ],
      cwd: FRONTEND_DIR,
      interpreter: 'node',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        FRONTEND_PORT: String(config.frontendPort),
        MON_GSV_PORT: String(config.backendPort),
      },
      error_file: path.join(LOG_DIR, 'frontend-error.log'),
      out_file: path.join(LOG_DIR, 'frontend-out.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
    },
  ],
};
