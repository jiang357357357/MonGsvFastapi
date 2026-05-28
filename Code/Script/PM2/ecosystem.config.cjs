const path = require("path");
const fs = require("fs");
const os = require("os");

const cfgDir = path.resolve(__dirname, "..", "..", "..");
const launchScript = "Code/Main/launch.py";
const logDir = path.join(cfgDir, "Data", "Logs", "PM2");

const isWin = os.platform() === "win32";
const pythonExe = isWin
  ? path.join(cfgDir, ".venv", "Scripts", "python.exe")
  : path.join(cfgDir, ".venv", "bin", "python");

const monconfigPath = path.join(cfgDir, ".monconfig");

function readConfig(section, key, fallback) {
  try {
    const raw = fs.readFileSync(monconfigPath, "utf-8");
    let cur = "";
    for (const line of raw.split(/\r?\n/)) {
      const s = line.trim();
      if (s.startsWith("[") && s.endsWith("]")) {
        cur = s.slice(1, -1).trim();
        continue;
      }
      if (cur === section && s.startsWith(key + "=")) {
        return s.split("=", 2)[1].trim();
      }
    }
  } catch (_) {}
  return fallback;
}

const backendPort = readConfig("server", "PORT", "40302");
const frontendPort = readConfig("frontend", "PORT", "40031");

if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

module.exports = {
  apps: [
    {
      name: "MonGSV",
      script: launchScript,
      interpreter: pythonExe,
      args: `--port ${backendPort} --frontend-port ${frontendPort}`,
      cwd: cfgDir,
      instances: 1,
      exec_mode: "fork",
      max_memory_restart: "20G",
      env: {
        MON_GSV_ENV: "production",
        PYTHONUTF8: "1",
      },
      error_file: path.join(logDir, "mongsv-error.log"),
      out_file: path.join(logDir, "mongsv-out.log"),
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      autorestart: true,
      max_restarts: 3,
      restart_delay: 5000,
      kill_timeout: 15000,
      stop_exit_codes: [0],
    },
  ],
};
