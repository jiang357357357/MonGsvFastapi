# MonGSV Scripts

统一前后端启动脚本。

## Windows

启动后端：

```powershell
.\Code\Script\Back\Cmd\Win\start.ps1
```

启动前端：

```powershell
.\Code\Script\Front\Cmd\Win\start.ps1
```

同时启动前后端：

```powershell
.\Code\Script\start_all.ps1
```

停止全部：

```powershell
.\Code\Script\stop_all.ps1
```

## Linux/macOS

启动后端：

```bash
bash Code/Script/Back/Cmd/Linux/start.sh
```

启动前端：

```bash
bash Code/Script/Front/Cmd/Linux/start.sh
```

脚本会从仓库根目录的 `.monconfig` 读取端口配置。

