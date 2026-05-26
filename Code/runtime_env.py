#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行时环境辅助。

当前主要负责为 Windows 注入 FFmpeg shared 运行时，
避免 torchcodec / torchaudio 在另一台机器上因为找不到 DLL 而崩溃。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Iterable


_DLL_HANDLES = []


def repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()
    resolved = start.resolve()
    if resolved.is_dir() and (resolved / ".monconfig").exists():
        return resolved
    if resolved.is_file():
        resolved = resolved.parent
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".monconfig").exists():
            return candidate
    return Path(__file__).resolve().parent.parent


def _system_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _iter_ffmpeg_dirs(root: Path) -> Iterable[Path]:
    yield root / "Tool" / "bin"
    yield root / "Tool" / "ffmpeg" / "bin"


def _has_ffmpeg_runtime_files(directory: Path) -> bool:
    required_patterns = (
        "ffmpeg.exe",
        "ffprobe.exe",
        "avcodec-*.dll",
        "avformat-*.dll",
        "avutil-*.dll",
        "swresample-*.dll",
        "swscale-*.dll",
    )
    return all(any(directory.glob(pattern)) for pattern in required_patterns)


def find_ffmpeg_runtime_dir(root: Path | None = None) -> Path | None:
    if _system_ffmpeg_available():
        return Path(os.path.dirname(shutil.which("ffmpeg") or "/usr/bin"))
    root = repo_root(root)
    for candidate in _iter_ffmpeg_dirs(root):
        if candidate.is_dir() and _has_ffmpeg_runtime_files(candidate):
            return candidate
    return None


def configure_ffmpeg_runtime(root: Path | None = None, verbose: bool = False) -> Path | None:
    ffmpeg_dir = find_ffmpeg_runtime_dir(root)
    if ffmpeg_dir is None:
        return None

    if _system_ffmpeg_available():
        if verbose:
            print(f"[runtime] 使用系统 FFmpeg: {ffmpeg_dir}")
        return ffmpeg_dir

    root = repo_root(root)
    ffmpeg_dir_str = str(ffmpeg_dir)
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if ffmpeg_dir_str not in path_parts:
        os.environ["PATH"] = ffmpeg_dir_str + os.pathsep + os.environ.get("PATH", "")
        if verbose:
            print(f"[runtime] 已注入 FFmpeg PATH: {ffmpeg_dir}")
    elif verbose:
        print(f"[runtime] FFmpeg PATH 已存在: {ffmpeg_dir}")

    if sys.platform.startswith("win") and hasattr(os, "add_dll_directory"):
        try:
            handle = os.add_dll_directory(ffmpeg_dir_str)
            _DLL_HANDLES.append(handle)
            if verbose:
                print(f"[runtime] 已注册 FFmpeg DLL 目录: {ffmpeg_dir}")
        except FileNotFoundError:
            pass

    return ffmpeg_dir


def _missing_ffmpeg_message(root: Path) -> str:
    candidates = [str(path) for path in _iter_ffmpeg_dirs(root)]
    lines = [
        "未找到可用的 FFmpeg shared 运行时，音频功能无法启动。",
        "需要的是完整 shared 包，不是单独一个 ffmpeg.exe。",
        "请把以下文件放进任一目录：",
        f"  - {candidates[0]}",
        f"  - {candidates[1]}",
        "至少需要包含：ffmpeg.exe、ffprobe.exe、avcodec-*.dll、avformat-*.dll、avutil-*.dll、swresample-*.dll、swscale-*.dll。",
    ]
    return "\n".join(lines)


def ensure_audio_runtime(
    root: Path | None = None,
    *,
    verify_torchcodec: bool = False,
    strict: bool = False,
    verbose: bool = False,
) -> Path | None:
    root = repo_root(root)
    ffmpeg_dir = configure_ffmpeg_runtime(root=root, verbose=verbose)

    if ffmpeg_dir is None:
        message = _missing_ffmpeg_message(root)
        if strict:
            raise RuntimeError(message)
        if verbose:
            print(f"[runtime] {message}")
        return None

    if verify_torchcodec:
        try:
            import torchcodec  # noqa: F401
        except Exception as exc:  # pragma: no cover - depends on local runtime
            message = (
                f"FFmpeg shared 目录已找到: {ffmpeg_dir}\n"
                "但 torchcodec 仍然初始化失败。\n"
                "请检查该目录是否为 full-shared 版本，或检查当前 torch / torchcodec 版本兼容性。\n"
                f"原始错误: {exc}"
            )
            if strict:
                raise RuntimeError(message) from exc
            if verbose:
                print(f"[runtime] {message}")

    return ffmpeg_dir
