#!/usr/bin/env python3
"""
MonGSV 系统启动器 (开发模式)
用于启动 GSV (GPT-SoVITS-WebUI) 前后端服务 - 开发环境
特性：详细日志、调试模式、自动重载、同时启动前后端
"""

import os
import sys
import subprocess
import argparse
import time
import threading
import socket
from pathlib import Path


def configure_stdio():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def get_local_ip():
    """获取本机 IP 地址"""
    try:
        # 创建一个 UDP 连接来获取本机 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)

# 添加项目路径
sys.path.insert(0, str(PROJECT_ROOT))

FRONTEND_DIR = PROJECT_ROOT / "Code" / "GptSov_Front"
GATEWAY_ENTRY = PROJECT_ROOT / "Code" / "FastApi" / "Main" / "run_gateway.py"
MONCONFIG_PATH = PROJECT_ROOT / ".monconfig"


def load_monconfig():
    config = {}
    if not MONCONFIG_PATH.exists():
        return config

    current_section = "default"
    for raw_line in MONCONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            config.setdefault(current_section, {})
            continue
        if "=" not in line:
            continue
        line = line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        config.setdefault(current_section, {})[key.strip()] = value.strip()
    return config


def config_value(config, section, key, default):
    return config.get(section, {}).get(key, default)


def default_backend_port():
    config = load_monconfig()
    return int(config_value(config, "server", "PORT", "40302"))


def default_frontend_port():
    config = load_monconfig()
    return int(config_value(config, "frontend", "PORT", "40031"))


def print_banner():
    """打印开发模式横幅"""
    print("\n" + "=" * 60)
    print("       MonGSV - GPT-SoVITS-WebUI 系统启动器")
    print("       " + '"开发模式 - Debug & Hot Reload"')
    print("=" * 60 + "\n")


def print_debug_info():
    """打印调试信息"""
    print("[调试信息]")
    print(f"  项目根目录: {PROJECT_ROOT}")
    print(f"  Python路径: {sys.executable}")
    print(f"  工作目录: {os.getcwd()}")
    print()


def check_dev_environment():
    """检查开发环境"""
    print("[环境检查]")
    
    # 检查虚拟环境
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        print(f"  [✓] 虚拟环境: {venv_path}")
    else:
        print(f"  [!] 虚拟环境不存在")
    
    # 检查是否在虚拟环境中
    if '.venv' in sys.executable:
        print(f"  [✓] 已在虚拟环境中")
    else:
        print(f"  [!] 未在虚拟环境中")
        print(f"      建议: .venv\\Scripts\\activate")
    
    # 检查后端文件
    backend_path = GATEWAY_ENTRY
    if backend_path.exists():
        print(f"  [✓] 后端文件: {backend_path}")
    else:
        print(f"  [✗] 后端文件不存在")
        return False
    
    # 检查前端目录
    frontend_path = FRONTEND_DIR
    if frontend_path.exists():
        print(f"  [✓] 前端目录: {frontend_path}")
    else:
        print(f"  [!] 前端目录不存在")
    
    # 检查.env文件
    env_path = PROJECT_ROOT / "Env" / ".env"
    if env_path.exists():
        print(f"  [✓] 配置文件: {env_path}")
    else:
        print(f"  [!] 配置文件不存在")
    
    print()
    return True


def start_backend_dev(host="127.0.0.1", port=None):
    """启动开发模式后端（在新终端窗口中）"""
    backend_path = GATEWAY_ENTRY
    backend_port = port or default_backend_port()
    
    print(f"[→] 正在启动后端服务 (开发模式)...")
    print(f"    访问地址: http://localhost:{backend_port}/docs")
    
    # 构建命令参数
    cmd_args = [
        str(backend_path),
        "start",
        "--reload",
        "--log-level",
        "debug",
    ]
    if host:
        cmd_args.extend(["--host", host])
    cmd_args.extend(["--port", str(backend_port)])
    
    # 设置环境变量
    env = os.environ.copy()
    env["MON_GSV_ENV"] = "development"
    env["DEBUG"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    
    try:
        # 使用 PowerShell 在新终端窗口中启动
        # 构建要执行的命令
        python_exe = sys.executable
        # 构建参数列表，每个参数用引号包裹
        quoted_args = ' '.join(['"' + arg + '"' for arg in cmd_args])
        script_cmd = '& "' + python_exe + '" ' + quoted_args
        full_cmd = 'cd "' + str(PROJECT_ROOT) + '"; ' + script_cmd
        
        ps_command = "Start-Process powershell -ArgumentList '-NoExit', '-Command', '" + full_cmd + "'"
        
        process = subprocess.Popen(
            ["powershell", "-Command", ps_command],
            cwd=str(PROJECT_ROOT),
            env=env,
            shell=True
        )
        return process
    except Exception as e:
        print(f"[!] 后端启动失败: {e}")
        return None


def start_frontend_dev():
    """启动开发模式前端（在新终端窗口中）"""
    frontend_path = FRONTEND_DIR
    
    if not frontend_path.exists():
        print(f"[!] 前端目录不存在: {frontend_path}")
        return None
    
    print(f"[→] 正在启动前端服务 (开发模式)...")
    
    try:
        # 使用 PowerShell 在新终端窗口中启动
        frontend_cmd = 'cd "' + str(frontend_path) + '"; npm run dev'
        ps_command = "Start-Process powershell -ArgumentList '-NoExit', '-Command', '" + frontend_cmd + "'"
        
        process = subprocess.Popen(
            ["powershell", "-Command", ps_command],
            cwd=str(frontend_path),
            env=os.environ.copy(),
            shell=True
        )
        return process
    except Exception as e:
        print(f"[!] 前端启动失败: {e}")
        return None


def output_reader(process, name, verbose=False):
    """读取进程输出"""
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            if verbose:
                print(f"[{name}] {line.strip()}")
            else:
                # 只显示关键信息
                line_str = line.strip()
                key_patterns = [
                    "系统已就绪", "数据库迁移", "错误", "失败",
                    "Local:", "Network:", "ready in", "端口",
                    "正在启动", "已启动"
                ]
                for pattern in key_patterns:
                    if pattern in line_str:
                        print(f"[{name}] {line_str}")
                        break
    except:
        pass


def watch_files():
    """监视文件变化"""
    print("[👁] 文件监视已启动")
    last_mtime = {}
    watch_paths = [
        PROJECT_ROOT / "Code" / "FastApi",
        PROJECT_ROOT / "Code" / "GptSov_Front" / "src",
    ]
    
    while True:
        time.sleep(3)
        for watch_path in watch_paths:
            if not watch_path.exists():
                continue
            for py_file in watch_path.rglob("*.py"):
                try:
                    mtime = py_file.stat().st_mtime
                    if py_file in last_mtime and mtime > last_mtime[py_file]:
                        print(f"\n[🔄] 文件变化: {py_file.name}")
                    last_mtime[py_file] = mtime
                except:
                    pass


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description="MonGSV 系统启动器 (开发模式)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="后端绑定地址")
    parser.add_argument("--port", type=int, default=None, help="后端端口号，默认读取 .monconfig")
    parser.add_argument("--no-frontend", action="store_true", help="不启动前端")
    parser.add_argument("--no-backend", action="store_true", help="不启动后端")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    parser.add_argument("--watch", "-w", action="store_true", help="启用文件监视")
    parser.add_argument("--debug", "-d", action="store_true", help="显示调试信息")
    parser.add_argument("--skip-check", action="store_true", help="跳过环境检查")
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.debug:
        print_debug_info()
    
    if not args.skip_check:
        if not check_dev_environment():
            sys.exit(1)
    
    # 启动文件监视
    if args.watch:
        watcher_thread = threading.Thread(target=watch_files, daemon=True)
        watcher_thread.start()
    
    # 存储进程
    processes = {}
    threads = []
    
    # 启动后端
    if not args.no_backend:
        backend_proc = start_backend_dev(args.host, args.port)
        if backend_proc:
            processes["后端"] = backend_proc
            print(f"[✓] 后端已启动 (新终端窗口)\n")
        else:
            print("[!] 后端启动失败\n")
    
    # 启动前端
    if not args.no_frontend:
        frontend_proc = start_frontend_dev()
        if frontend_proc:
            processes["前端"] = frontend_proc
            print(f"[✓] 前端已启动 (新终端窗口)\n")
        else:
            print("[!] 前端启动失败\n")
    
    if not processes:
        print("[!] 没有启动任何服务")
        sys.exit(1)
    
    # 显示访问信息
    print("=" * 60)
    print("服务访问地址:")
    if "后端" in processes:
        print(f"  后端 API: http://localhost:{args.port or default_backend_port()}/docs")
    if "前端" in processes:
        print(f"  前端页面: http://localhost:{default_frontend_port()}/")
    print("=" * 60)
    print("\n按 Ctrl+C 停止所有服务")
    if args.watch:
        print("文件监视: 已启用")
    print()
    
    # 等待进程结束
    try:
        while True:
            for name, proc in list(processes.items()):
                if proc.poll() is not None:
                    print(f"[!] {name} 进程已退出 (code: {proc.returncode})")
                    del processes[name]
            if not processes:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] 正在关闭服务...")
    finally:
        for name, proc in processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=3)
                print(f"[✓] {name} 已停止")
            except:
                proc.kill()
                print(f"[✓] {name} 已强制停止")
        print("\n[✓] 所有服务已停止")


if __name__ == "__main__":
    main()
