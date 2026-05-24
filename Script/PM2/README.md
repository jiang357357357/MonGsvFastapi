# PM2 Runtime

PM2 管理两个独立进程：

- `MonGsvBackend`: FastAPI 网关
- `MonGsvFrontend`: 已构建前端的 Vite preview 服务

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

前端 PM2 进程只运行已有 `Code/GptSov_Front/dist`，不会自动构建。
需要更新构建产物时，在 `Code/GptSov_Front` 下执行：

```bash
npm run build
```

