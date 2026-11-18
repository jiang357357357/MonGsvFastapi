Windows 交付目录构建与精简
========================

从项目根目录运行。构建主机需要 Python >=3.11、packaging、uv、npm、clang、lld-link、llvm-dlltool、7z。

完整构建：
  python3 Script/Build/Windows/assemble.py --stage all

分阶段：
  python3 Script/Build/Windows/assemble.py --stage payload
  python3 Script/Build/Windows/assemble.py --stage frontend
  python3 Script/Build/Windows/assemble.py --stage runtime
  python3 Script/Build/Windows/assemble.py --stage trim
  python3 Script/Build/Windows/assemble.py --stage manifest

单元测试：
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Script/Build/Windows/tests -v

验证：
  PYTHONDONTWRITEBYTECODE=1 python3 Script/Build/Windows/validate.py
  验证器使用 Temp/WinBuild 下的依赖包、浏览器检查和模型目录检查报告。
  浏览器脚本在 tests/browser_check.mjs，需要本机 Playwright 与 Chromium。

目录约定：
- win：只交付程序、底模和 ASR 模型、运行环境、配置、说明、许可及校验结果。
- Temp/WinBuild：下载档案、Windows wheels、构建日志和检查中间结果；不随 win 交付。
- --stage all 会复用上述缓存，不再把离线安装包或构建/测试脚本放进 win。
- 默认不打包服务器上的已训练角色模型、参考音频和角色元数据，Resources/Model 初始为空。
- 保留底模与 ASR 模型；移除交付副本中的开发资料、旧启动脚本、字节码缓存和 ffplay。
- 中文 ASR 默认使用 Fun-ASR-Nano-2512；打包 tools/asr/models/Fun-ASR-Nano-2512 的完整权重与词表，
  并保留本地 VAD。排除已不使用的 Paraformer-large 中文权重，验证器核对 Nano 的固定修订与 SHA-256。
- FFmpeg 的全部 shared DLL、ffmpeg.exe、ffprobe.exe 及许可仍然保留。
- Windows 实机启动、合成和训练验收须单独执行。

Windows 启动复验：
- 当前 Windows 11 原生测试结果在 win/startup-acceptance.json，原始日志与截图在 Temp/WinBuild/acceptance。
- 测试覆盖资源管理器双击入口、全部服务健康、自动打开页面、完整运行库检查、Stop.cmd 清理进程/端口，
  以及含中文/空格的路径和自定义端口重启。未安装系统 Python、uv 或 MSVC 运行库。
- 测试辅助脚本在 tests/windows-*.ps1；acceptance_server.py 仅供隔离的 libvirt 测试网传入包并收集报告。
  这些脚本不进入交付目录，也不安装常驻服务。
- 构建验证器比对完整程序文件的 SHA-256 指纹；程序文件发生变化后，旧的启动验收不会继续标为通过。
- Windows 10、GPU 实际推理和训练需要另外验收。

功能实测：
- functional_probe.py 使用真实 HTTP 接口和真实音频，不模拟模型。--mode windows-cpu 验证两种底模、
  中英文合成、已训练权重加载、ASR 回读及无 CUDA 时拒绝训练；--mode linux-gpu 验证完整预处理、
  SoVITS/GPT 训练、检查点续训、权重重载与合成。具体参数见 --help。
- windows_browser_probe.py 在 Windows 中使用原生 Edge，通过 CDP 操作实际页面，验证合成、
  HTML 音频播放进度、小窗口控件可见性和下载 WAV 的时长/采样率。
- 本次功能证据在 Temp/WinBuild/functional-acceptance 与 Temp/WinBuild/gpu-functional-acceptance；
  win/functional-acceptance.json 是绑定交付文件指纹的精简报告。测试音频、训练权重、虚拟机及脚本均不进入 win。
- Linux GPU 测试与 Windows CPU 测试分别记录；只有带 NVIDIA 显卡的 Windows 实测才能完成 Windows CUDA 验收。

官方训练预设复验：
- 默认值集中在 Code/FastApi/Base/Training/defaults.py，通过 /training/workbench/defaults 提供给页面。
- v1/v2/v2Pro/v2ProPlus：SoVITS 默认 8 轮；v3/v4/v5dev/v5turbo：默认 2 轮；GPT 均为 15 轮。
  Batch 根据官方显存/内存算法动态计算。保存策略按用户要求：每个阶段只在最后一轮保存一次，
  保存间隔自动等于该阶段的总轮数；新训练、续训、旧请求及直接调用服务均遵循此规则。
  历史记录原样保留，恢复旧任务时采用新的最终保存策略。
- 测试：PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest Code.FastApi.tests.test_training_defaults -v
- 参数、实际生成配置与页面序列化的证据在 Temp/OfficialDefaultsReference。
- 最终轮次保存策略、修改总轮数和旧任务续训的复验证据在 Temp/FinalOnlySaving。
- 轮次与 Loss 对应关系的测试在 Code/FastApi/tests/test_training_telemetry.py；
  Temp/EpochLossFix 保存历史数据核对、网页检查和 v2ProPlus/v5dev 三轮真实 GPU 训练证据。
  新 SoVITS 训练逐轮记录平均 Loss；旧任务的缺失轮次保持缺失，保存权重仍只发生在最后一轮。
- 修改交付文件后，旧 Windows 原生验收仅作历史证据；验证器不会将旧指纹的成功结果用于新包。
