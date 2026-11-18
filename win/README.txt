MonGSV Windows 本地版
===================

启动
1. 把整个 win 文件夹复制到 Windows 10/11 x64 的可写目录，再双击 MonGSV.exe。
   也可使用 Start.cmd。无需另装 Node.js 或 Python，程序不会调用服务器上的 Python。
2. 等待控制台出现 Ready，浏览器会打开 http://127.0.0.1:40031/。
   全新 Windows 首次加载音频库可能需要几分钟；默认最多等待 10 分钟，期间无需安装依赖。
3. 首次使用建议先运行 Check.cmd，检查 Torch、CUDA、FFmpeg、词典及底模。
4. 关闭时按启动窗口中的 Ctrl+C，或双击 Stop.cmd。启动器会结束本次启动的服务和子进程。

这是一份包含 Windows 可执行入口、CPython、依赖及底模的便携目录。
请保留整个目录结构，不能只拿走 MonGSV.exe。运行时需要目录写入权限。
建议使用较短的解压路径（例如 D:\MonGSV），以兼容第三方模型工具的 Windows 路径限制。

硬件与功能
- 内置 Python 3.10.20、PyTorch 2.11.0 + CUDA 12.8。
- NVIDIA GPU 训练需要兼容 CUDA 12.8 的显卡驱动和足够显存；不需要另装 CUDA Toolkit。
- 没有可用 CUDA 时可用 CPU 合成，已实测 v5turbo 中文/英文、v5dev 中文及新训练权重；CPU 合成较慢。
  训练需要 NVIDIA CUDA 显卡；无显卡时训练工作台会明确拒绝启动。
- 包含底模、ASR 模型和英文 NLTK 词典。
- 中文训练标注和参考音频转录默认使用 Fun-ASR-Nano-2512；Nano 权重、Qwen 词表和 VAD 已随包提供。
- 中文转录直接加载本地模型；Windows 分发包不再包含未使用的 Paraformer-large 中文权重。
- 不包含服务器上已训练好的角色模型和参考音频。首次使用请在资源管理中创建世界，再导入角色模型或准备音频训练新角色。
- 网页脚本和样式均在本地，沿用当前暖灰琥珀界面。
- 未复制训练历史、原始训练数据、输出音频、登录信息和个人声纹库。
- 当前源目录没有 UVR5 分离权重，因此包中也没有；需要该功能时另外安装相应模型。
- 可选模型、额外语种词典或依赖外部服务的功能仍可能需要联网获取资源。

配置与数据
- config.json：本机前后端端口、启动等待时间、是否自动打开浏览器。
  修改 backend_port / frontend_port 后重启即可；前端会自动跟随。
- 如果端口已占用，启动器会提示并退出，不会自动结束其他程序。
- app\Resources\Model：初始为空，保存新训练或导入的角色权重及参考音频。
- app\Resources\Train\Projects：新训练任务的数据。
- app\Data：输出、缓存、数据库和应用日志。
- data\launcher\console.log：启动及服务控制台日志。
- data\diagnostics.json：最近一次 Windows 检查报告。
- Check.cmd：完整检查；Check.cmd --quick：只检查基本文件和依赖是否存在。
- 若文件已损坏，请先关闭程序，再从完整交付目录重新复制 runtime。

训练默认参数
- v1/v2/v2Pro/v2ProPlus 的 SoVITS 默认 8 轮；v3/v4/v5dev/v5turbo 默认 2 轮。
- 所有版本的 GPT 默认 15 轮。训练轮数、Batch、学习率等沿用官方预设。
- 保存策略：每个阶段只在设定的最后一轮保存一次；修改总轮数后自动跟随，不再导出中间轮次权重。
- Batch 根据本机显卡向 PyTorch 报告的总显存，按官方算法自动计算。
- 默认关闭梯度检查点，LoRA rank 为 32，SoVITS/GPT 学习率分别为 0.0001/0.01。
- “恢复默认参数”会同时重置高级参数。历史训练记录保留原参数；新训练和续训都只在最后一轮保存。
- 训练曲线默认按轮次展示，并列出每轮 Loss 数值；可切换按 Step 查看原始记录。
- SoVITS 每轮记录平均 Loss，与 Step 日志频率和权重保存频率分别处理。
- 历史任务未记录的轮次显示“未记录”，已有采样值会单独标识，不补算或插值。

校验与验收状态
- manifest.json 记录交付文件的大小和 SHA-256；Python 包版本及许可保留在 runtime 中。
- validation.json 记录静态检查及验收状态；startup-acceptance.json 保存启动结果，
  functional-acceptance.json 保存功能实测结果及平台范围。
- 2026-10-19 已在全新 Windows 11 专业版 x64 虚拟机中以普通权限实测通过：
  资源管理器双击 MonGSV.exe、8/8 服务健康、自动打开页面、完整依赖检查、Stop.cmd 退出，
  以及中文/空格路径下修改端口后重新启动。未额外安装 Python、uv 或系统 MSVC 运行库。
- Windows 11 CPU 功能复验通过：两种底模合成、中英文合成、新训练权重加载、中文 ASR、
  生成音频的 ASR 回读、网页播放和下载。修复了小窗口中播放器控件被遮挡的问题。
- 同一份应用代码另在 Linux NVIDIA 显卡上完成 103 条音频的预处理、SoVITS/GPT 训练，
  从检查点续训至第 2 轮，并加载导出的新权重合成及 ASR 回读通过。
  Linux GPU 结果不能代表 Windows CUDA 已通过；测试 Windows 虚拟机没有 NVIDIA 显卡，
  Windows CUDA 推理/训练及 Windows 10 仍待实测。验收记录只适用于记录中 SHA-256 对应的程序文件。
- 若 Torch 提示缺少 MSVCP140/VCRUNTIME DLL，请安装微软官方 Visual C++ x64 运行库：
  https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist

后续更新的验收范围
- 本次同步了官方训练预设、最终轮次保存策略、每轮 Loss 记录与展示、v2 GPT 底模选择，
  以及情感配置的训练切分列表、切片转录修复、官方高级合成参数和 Fun-ASR-Nano 中文转录。
- 参数生成、网页操作与静态检查已验证；以上 Windows 原生启动/合成报告对应更新前的文件指纹，
  本次同步后尚未重跑 Windows 原生验收。validation.json 与 manifest.json 会据此将当前原生验收标为待测。

交付目录
- win 只包含程序、运行环境、底模和 ASR 模型、配置、许可和使用/校验说明。
- 离线安装包、构建缓存和开发测试不需要随本目录复制。
- 重建脚本在工程的 Script/Build/Windows；构建缓存与离线安装包在工程的 Temp/WinBuild。
- 原项目许可证：app\LICENSE；Python 与 Python 包许可随 runtime 保留，FFmpeg 许可及构建说明在 Tool\ffmpeg-info。

