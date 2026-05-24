#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MonGSV 生产模式启动器。

启动当前 FastAPI 网关后端，以及编译后的前端 preview 服务。
"""

from __future__ import annotations

import argparse
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "Code" / "GptSov_Front"
GATEWAY_ENTRY = PROJECT_ROOT / "Code" / "FastApi" / "Main" / "run_gateway.py"
MONCONFIG_PATH = PROJECT_ROOT / ".monconfig"


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def print_banner() -> None:
    print("\n" + "=" * 70)
    print("       MonGSV - GPT-SoVITS FastAPI 系统启动器")
    print("       生产模式: FastAPI Gateway + Vite Preview")
    print("=" * 70 + "\n")


def load_monconfig() -> dict[str, dict[str, str]]:
    config: dict[str, dict[str, str]] = {}
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


def config_value(
    config: dict[str, dict[str, str]],
    section: str,
    key: str,
    default: str,
) -> str:
    return config.get(section, {}).get(key, default)


def display_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def command_name(name: str) -> str:
    if os.name == "nt" and not name.endswith(".cmd"):
        return f"{name}.cmd"
    return name


def python_executable() -> str:
    if os.name == "nt":
        candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = PROJECT_ROOT / ".venv" / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return sys.executable


def check_environment() -> bool:
    missing: list[str] = []
    if not GATEWAY_ENTRY.exists():
        missing.append(str(GATEWAY_ENTRY))
    if not FRONTEND_DIR.exists():
        missing.append(str(FRONTEND_DIR))
    if not (FRONTEND_DIR / "package.json").exists():
        missing.append(str(FRONTEND_DIR / "package.json"))

    npm = shutil.which(command_name("npm"))
    npx = shutil.which(command_name("npx"))
    if not npm:
        missing.append("npm")
    if not npx:
        missing.append("npx")

    if missing:
        print("[!] 环境检查失败，缺少:")
        for item in missing:
            print(f"    - {item}")
        return False

    print("[✓] 环境检查通过")
    print(f"    Python: {python_executable()}")
    print(f"    npm   : {npm}")
    return True


def ensure_frontend_dependencies() -> bool:
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        return True

    npm = command_name("npm")
    install_cmd = [npm, "ci"] if (FRONTEND_DIR / "package-lock.json").exists() else [npm, "install"]
    print("[→] 前端依赖不存在，正在安装...")
    result = subprocess.run(
        install_cmd,
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy(),
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        print("[!] 前端依赖安装失败")
        return False
    return True


def build_frontend() -> bool:
    print("[→] 正在编译前端...")
    result = subprocess.run(
        [command_name("npm"), "run", "build"],
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy(),
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        print("[!] 前端编译失败")
        return False
    return True


def start_backend(host: str, port: int, new_window: bool = False) -> Optional[subprocess.Popen]:
    print("[→] 正在启动 FastAPI 后端...")
    print(f"    访问地址: http://{display_host(host)}:{port}/docs")
    if new_window:
        print("    日志窗口: 单独控制台")

    env = os.environ.copy()
    env["MON_GSV_ENV"] = "production"
    env["PYTHONUTF8"] = "1"

    cmd = [
        python_executable(),
        str(GATEWAY_ENTRY),
        "start",
        "--host",
        host,
        "--port",
        str(port),
        "--no-reload",
    ]

    try:
        if new_window and os.name == "nt":
            return subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        return subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        print(f"[!] 后端启动失败: {exc}")
        return None


def start_frontend(port: int, build: bool = False) -> Optional[subprocess.Popen]:
    if not ensure_frontend_dependencies():
        return None
    if build and not build_frontend():
        return None
    if not (FRONTEND_DIR / "dist").exists():
        print("[!] 前端 dist 目录不存在，请先执行一次 npm run build，或使用 --build")
        return None

    print("[→] 正在启动前端 preview...")
    print(f"    访问地址: http://127.0.0.1:{port}/")

    env = os.environ.copy()
    env["NODE_ENV"] = "production"
    env["FRONTEND_PORT"] = str(port)

    cmd = [
        command_name("npx"),
        "vite",
        "preview",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]

    try:
        return subprocess.Popen(
            cmd,
            cwd=str(FRONTEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except Exception as exc:
        print(f"[!] 前端启动失败: {exc}")
        return None


def enqueue_output(process: subprocess.Popen, name: str, output_queue: queue.Queue) -> None:
    if process.stdout is None:
        output_queue.put((name, None))
        return
    for line in iter(process.stdout.readline, ""):
        output_queue.put((name, line.rstrip()))
    output_queue.put((name, None))


def monitor_processes(processes: dict[str, subprocess.Popen], verbose: bool = False) -> None:
    key_words = [
        "Uvicorn running",
        "Application startup complete",
        "MonHub",
        "Local:",
        "Network:",
        "ready",
        "error",
        "failed",
        "错误",
        "失败",
        "端口",
    ]
    output_queue: queue.Queue = queue.Queue()
    for name, process in processes.items():
        threading.Thread(
            target=enqueue_output,
            args=(process, name, output_queue),
            daemon=True,
        ).start()

    print("\n" + "-" * 70)
    print("服务运行中...")
    if not verbose:
        print("(使用 --verbose 查看详细输出)")
    print("-" * 70 + "\n")

    try:
        while processes:
            for name, process in list(processes.items()):
                if process.poll() is not None:
                    print(f"[!] {name} 进程已退出 (code: {process.returncode})")
                    processes.pop(name, None)

            try:
                name, line = output_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if line is None:
                continue
            if verbose or any(word.lower() in line.lower() for word in key_words):
                print(f"[{name}] {line}")
    except KeyboardInterrupt:
        print("\n[!] 收到停止信号...")


def stop_processes(processes: dict[str, subprocess.Popen]) -> None:
    for name, process in processes.items():
        if process.poll() is not None:
            continue
        try:
            print(f"[→] 正在停止 {name}...")
            process.terminate()
            process.wait(timeout=8)
            print(f"[✓] {name} 已停止")
        except Exception:
            try:
                process.kill()
                print(f"[✓] {name} 已强制停止")
            except Exception:
                print(f"[!] 无法停止 {name}")


def main() -> int:
    configure_stdio()
    config = load_monconfig()
    default_host = config_value(config, "server", "HOST", "0.0.0.0")
    default_backend_port = int(config_value(config, "server", "PORT", "40302"))
    default_frontend_port = int(config_value(config, "frontend", "PORT", "40031"))

    parser = argparse.ArgumentParser(description="MonGSV 系统启动器 (生产模式)")
    parser.add_argument("--host", type=str, default=default_host, help="后端绑定地址")
    parser.add_argument("--port", type=int, default=default_backend_port, help="后端端口号")
    parser.add_argument("--frontend-port", type=int, default=default_frontend_port, help="前端端口号")
    parser.add_argument("--no-frontend", action="store_true", help="不启动前端")
    parser.add_argument("--build", action="store_true", help="启动前先重新编译前端")
    parser.add_argument("--inline-backend", action="store_true", help="后端日志显示在当前窗口，不单独弹窗")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    args = parser.parse_args()

    print_banner()
    if not check_environment():
        return 1
    print()

    processes: dict[str, subprocess.Popen] = {}
    backend_proc = start_backend(args.host, args.port, new_window=(os.name == "nt" and not args.inline_backend))
    if not backend_proc:
        return 1
    processes["后端"] = backend_proc
    print(f"[✓] 后端已启动 (PID: {backend_proc.pid})\n")

    if not args.no_frontend:
        frontend_proc = start_frontend(args.frontend_port, build=args.build)
        if frontend_proc:
            processes["前端"] = frontend_proc
            print(f"[✓] 前端已启动 (PID: {frontend_proc.pid})\n")
        else:
            print("[!] 前端启动失败，继续运行后端\n")

    print("=" * 70)
    print("服务访问地址:")
    print(f"  后端 API : http://{display_host(args.host)}:{args.port}/docs")
    print(f"  后端健康: http://{display_host(args.host)}:{args.port}/health")
    if "前端" in processes:
        print(f"  前端页面: http://127.0.0.1:{args.frontend_port}/")
    print("=" * 70)
    print("\n按 Ctrl+C 停止所有服务\n")

    try:
        monitor_processes(processes, args.verbose)
    finally:
        stop_processes(processes)
        print("\n[✓] 所有服务已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
