#!/usr/bin/env python3
"""
MonGSV 系统启动器 (生产模式)
用于启动 GSV (GPT-SoVITS-WebUI) 前后端服务 - 生产环境
"""

import os
import sys
import subprocess
import argparse
import time
import socket
from pathlib import Path


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


def print_banner():
    """打印启动横幅"""
    print("\n" + "=" * 60)
    print("       MonGSV - GPT-SoVITS-WebUI 系统启动器")
    print("       " + '"生产模式"')
    print("=" * 60 + "\n")


def check_environment():
    """检查生产环境"""
    # 检查虚拟环境
    venv_path = PROJECT_ROOT / ".venv"
    if not venv_path.exists():
        print("[!] 未找到虚拟环境 (.venv)")
        return False
    
    if '.venv' not in sys.executable:
        print("[!] 未在虚拟环境中运行")
        print(f"    当前 Python: {sys.executable}")
        return False
    
    print("[✓] 环境检查通过")
    return True


def start_backend(host="127.0.0.1", port=None):
    """启动后端服务"""
    backend_path = PROJECT_ROOT / "Code" / "GsvBack" / "main.py"
    
    if not backend_path.exists():
        print(f"[!] 后端启动文件不存在: {backend_path}")
        return None
    
    print(f"[→] 正在启动后端服务...")
    print(f"    访问地址: http://{host}:{port or '7020'}/Core/")
    
    # 构建命令
    cmd = [sys.executable, str(backend_path)]
    if host != "127.0.0.1":
        cmd.extend(["--host", host])
    if port:
        cmd.extend(["--port", str(port)])
    
    # 设置生产环境变量
    env = os.environ.copy()
    env["MON_GSV_ENV"] = "production"
    env["PYTHONOPTIMIZE"] = "1"
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8"
        )
        return process
    except Exception as e:
        print(f"[!] 后端启动失败: {e}")
        return None


def start_frontend():
    """启动前端服务"""
    frontend_path = PROJECT_ROOT / "Code" / "GptSov_Front"
    
    if not frontend_path.exists():
        print(f"[!] 前端目录不存在: {frontend_path}")
        return None
    
    # 检查 package.json
    package_json = frontend_path / "package.json"
    if not package_json.exists():
        print(f"[!] 前端 package.json 不存在")
        return None
    
    print(f"[→] 正在启动前端服务...")
    
    # 使用 npm run dev 启动前端
    cmd = ["npm", "run", "dev"]
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(frontend_path),
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            shell=True  # Windows 需要 shell=True 来运行 npm
        )
        return process
    except Exception as e:
        print(f"[!] 前端启动失败: {e}")
        return None


def monitor_processes(processes, verbose=False):
    """监控所有进程输出"""
    import re
    import select
    
    key_patterns = [
        r"系统已就绪",
        r"正在启动 Web",
        r"数据库迁移",
        r"错误",
        r"失败",
        r"端口.*被占用",
        r"Local:",
        r"Network:",
        r"ready in",
    ]
    
    print("\n" + "-" * 60)
    print("服务运行中...")
    if not verbose:
        print("(使用 --verbose 查看详细输出)")
    print("-" * 60 + "\n")
    
    try:
        while True:
            for name, process in processes.items():
                if process.poll() is not None:
                    print(f"[!] {name} 进程已退出 (code: {process.returncode})")
                    return
                
                # 读取输出
                if verbose:
                    try:
                        line = process.stdout.readline()
                        if line:
                            print(f"[{name}] {line.strip()}")
                    except:
                        pass
                else:
                    # 只显示关键信息
                    try:
                        line = process.stdout.readline()
                        if line:
                            line_str = line.strip()
                            for pattern in key_patterns:
                                if re.search(pattern, line_str, re.IGNORECASE):
                                    print(f"[{name}] {line_str}")
                                    break
                    except:
                        pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[!] 收到停止信号...")


def stop_processes(processes):
    """停止所有进程"""
    for name, process in processes.items():
        try:
            print(f"[→] 正在停止 {name}...")
            process.terminate()
            process.wait(timeout=5)
            print(f"[✓] {name} 已停止")
        except:
            try:
                process.kill()
                print(f"[✓] {name} 已强制停止")
            except:
                print(f"[!] 无法停止 {name}")


def main():
    parser = argparse.ArgumentParser(description="MonGSV 系统启动器 (生产模式)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="后端绑定地址")
    parser.add_argument("--port", type=int, default=None, help="后端端口号")
    parser.add_argument("--no-frontend", action="store_true", help="不启动前端")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    print_banner()
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    print()
    
    # 存储所有进程
    processes = {}
    
    # 启动后端
    backend_proc = start_backend(args.host, args.port)
    if not backend_proc:
        print("[!] 后端启动失败")
        sys.exit(1)
    processes["后端"] = backend_proc
    print(f"[✓] 后端已启动 (PID: {backend_proc.pid})\n")
    
    # 启动前端
    if not args.no_frontend:
        frontend_proc = start_frontend()
        if frontend_proc:
            processes["前端"] = frontend_proc
            print(f"[✓] 前端已启动 (PID: {frontend_proc.pid})\n")
        else:
            print("[!] 前端启动失败，继续运行后端\n")
    
    # 显示访问信息
    print("=" * 60)
    print("服务访问地址:")
    print(f"  后端 API: http://localhost:{args.port or '7020'}/Core/")
    if not args.no_frontend and "前端" in processes:
        print(f"  前端页面: http://localhost:7010/")
    print("=" * 60)
    print("\n按 Ctrl+C 停止所有服务\n")
    
    # 监控进程
    try:
        monitor_processes(processes, args.verbose)
    finally:
        stop_processes(processes)
        print("\n[✓] 所有服务已停止")


if __name__ == "__main__":
    main()
