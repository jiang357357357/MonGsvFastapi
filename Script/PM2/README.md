# PM2 Runtime

PM2 管理两个独立进程：

- `MonGsvBackend`: FastAPI 网关
- `MonGsvFrontend`: 带热更新（HMR）的 Vite 开发服务

## Windows

```powershell
.\Script\PM2\start.ps1
.\Script\PM2\status.ps1
.\Script\PM2\stop.ps1
```

只启动后端：

```powershell
.\Script\PM2\start.ps1 -OnlyBackend
```

只启动前端：

```powershell
.\Script\PM2\start.ps1 -OnlyFrontend
```

## Linux/macOS

```bash
bash Script/PM2/start.sh
bash Script/PM2/stop.sh
```

前端 PM2 进程直接运行 Vite 开发服务，不依赖 `dist`。修改
`Code/GptSov_Front` 下的前端源码后，Vite 会监听文件并向浏览器推送热更新。

PM2 的 `watch` 特意保持关闭：前端文件由 Vite 监听，PM2 只负责进程守护，
避免每次保存源码都重启整个前端服务。

安装或更新依赖后，需要重启前端进程：

```bash
npm install
pm2 restart MonGsvFrontend
```

