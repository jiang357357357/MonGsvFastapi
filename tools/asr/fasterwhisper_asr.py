import argparse
import os
import shutil
import tempfile
import threading
import time
import traceback
import zipfile
from typing import Callable, Dict, List, Optional, Tuple

import requests
import torch
from faster_whisper import WhisperModel
from modelscope import snapshot_download as snapshot_download_ms
from tqdm import tqdm

from tools.asr.config import get_models
from tools.asr.funasr_asr import only_asr, resolve_inputs, write_output_file
from tools.my_utils import load_cudnn

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
MODELSCOPE_PRETRAINED_REPO = "XXXXRT/GPT-SoVITS-Pretrained"
MODELSCOPE_FASTER_WHISPER_ZIP = "faster-whisper.zip"
MODELSCOPE_FASTER_WHISPER_REPO = "XXXXRT/faster-whisper"

# fmt: off
language_code_list = [
    "af", "am", "ar", "as", "az", 
    "ba", "be", "bg", "bn", "bo", 
    "br", "bs", "ca", "cs", "cy", 
    "da", "de", "el", "en", "es", 
    "et", "eu", "fa", "fi", "fo", 
    "fr", "gl", "gu", "ha", "haw", 
    "he", "hi", "hr", "ht", "hu", 
    "hy", "id", "is", "it", "ja", 
    "jw", "ka", "kk", "km", "kn", 
    "ko", "la", "lb", "ln", "lo", 
    "lt", "lv", "mg", "mi", "mk", 
    "ml", "mn", "mr", "ms", "mt", 
    "my", "ne", "nl", "nn", "no", 
    "oc", "pa", "pl", "ps", "pt", 
    "ro", "ru", "sa", "sd", "si", 
    "sk", "sl", "sn", "so", "sq", 
    "sr", "su", "sv", "sw", "ta", 
    "te", "tg", "th", "tk", "tl", 
    "tr", "tt", "uk", "ur", "uz", 
    "vi", "yi", "yo", "zh", "yue",
    "auto"] 
# fmt: on


def has_required_files(local_dir: str, required_files: list[str]) -> bool:
    return os.path.isdir(local_dir) and all(os.path.exists(os.path.join(local_dir, name)) for name in required_files)


def format_bytes(size: int) -> str:
    if size >= 1024 ** 3:
        return f"{size / (1024 ** 3):.2f} GB"
    if size >= 1024 ** 2:
        return f"{size / (1024 ** 2):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def directory_file_size(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return total
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            try:
                total += os.path.getsize(file_path)
            except OSError:
                pass
    return total


def get_existing_required_files(model_path: str, required_files: list[str]) -> list[str]:
    existing_required = []
    for filename in required_files:
        if os.path.exists(os.path.join(model_path, filename)):
            existing_required.append(filename)
    return existing_required


def get_incomplete_files(model_path: str) -> list[tuple[str, int]]:
    incomplete_files = []
    if os.path.isdir(model_path):
        for root, _, filenames in os.walk(model_path):
            for filename in filenames:
                if filename.endswith(".incomplete"):
                    file_path = os.path.join(root, filename)
                    try:
                        incomplete_files.append((file_path, os.path.getsize(file_path)))
                    except OSError:
                        pass
    return incomplete_files


def observed_download_size(model_path: str, required_files: list[str]) -> int:
    total = 0
    for filename in required_files:
        file_path = os.path.join(model_path, filename)
        if os.path.exists(file_path):
            try:
                total += os.path.getsize(file_path)
            except OSError:
                pass
    return total + sum(size for _, size in get_incomplete_files(model_path))


def collect_download_snapshot(
    model_path: str,
    required_files: list[str],
    total_size: Optional[int] = None,
    previous_size: Optional[int] = None,
    elapsed_seconds: float = 0,
) -> tuple[str, int]:
    existing_required = get_existing_required_files(model_path, required_files)
    incomplete_files = get_incomplete_files(model_path)
    current_size = observed_download_size(model_path, required_files)
    parts = [
        f"已完成文件 {len(existing_required)}/{len(required_files)}",
    ]

    if total_size and total_size > 0:
        percent = min(current_size / total_size * 100, 100)
        remaining = max(total_size - current_size, 0)
        parts.insert(0, f"进度 {percent:.1f}% ({format_bytes(current_size)}/{format_bytes(total_size)})")
        if remaining == 0 and len(existing_required) < len(required_files):
            parts.append("等待校验/落盘")
        else:
            parts.append(f"剩余 {format_bytes(remaining)}")
    else:
        parts.insert(0, f"已下载 {format_bytes(current_size)}")

    if previous_size is not None and elapsed_seconds > 0:
        speed = max(current_size - previous_size, 0) / elapsed_seconds
        parts.append(f"速度 {format_bytes(int(speed))}/s")

    if incomplete_files:
        largest_path, largest_size = max(incomplete_files, key=lambda item: item[1])
        parts.append(f"临时文件 {format_bytes(largest_size)} ({os.path.basename(largest_path)[:18]}...)")
    return ", ".join(parts), current_size


def start_download_progress_logger(
    label: str,
    model_path: str,
    required_files: list[str],
    total_size: Optional[int] = None,
):
    stop_event = threading.Event()

    def worker():
        last_snapshot = ""
        last_size = None
        last_time = time.monotonic()
        while not stop_event.is_set():
            now = time.monotonic()
            snapshot, current_size = collect_download_snapshot(
                model_path,
                required_files,
                total_size=total_size,
                previous_size=last_size,
                elapsed_seconds=now - last_time,
            )
            if snapshot != last_snapshot:
                print(f"[ASR] {label} 下载中: {snapshot}", flush=True)
                last_snapshot = snapshot
            last_size = current_size
            last_time = now
            stop_event.wait(5)

    thread = threading.Thread(target=worker, name=f"asr-download-progress-{label}", daemon=True)
    thread.start()

    def stop():
        stop_event.set()
        thread.join(timeout=1)
        snapshot, _ = collect_download_snapshot(model_path, required_files, total_size=total_size)
        print(f"[ASR] {label} 下载结束: {snapshot}", flush=True)

    return stop


def get_model_locations(model_size: str) -> tuple[str, str, str]:
    if "distil" in model_size:
        if "3.5" in model_size:
            repo_id = "distil-whisper/distil-large-v3.5-ct2"
            hf_model_path = "tools/asr/models/faster-distil-whisper-large-v3.5"
        else:
            repo_id = "Systran/faster-{}-whisper-{}".format(*model_size.split("-", maxsplit=1))
            hf_model_path = f"tools/asr/models/{repo_id.replace('Systran/', '').replace('distil-whisper/', '', 1)}"
    elif model_size == "large-v3-turbo":
        repo_id = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
        hf_model_path = "tools/asr/models/faster-whisper-large-v3-turbo"
    else:
        repo_id = f"Systran/faster-whisper-{model_size}"
        hf_model_path = f"tools/asr/models/{repo_id.replace('Systran/', '')}"

    ms_model_path = os.path.join(
        "tools/asr/models",
        f"faster-whisper-{model_size}".replace("whisper-distil", "distil-whisper"),
    )
    return repo_id, hf_model_path, ms_model_path


def remove_path(path: str):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def modelscope_resolve_url(repo_id: str, filename: str, revision: str = "master") -> str:
    return f"https://www.modelscope.cn/models/{repo_id}/resolve/{revision}/{filename}"


def download_file_with_progress(url: str, output_path: str, label: str) -> str:
    temp_path = output_path + ".part"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(temp_path):
        os.remove(temp_path)

    print(f"[ASR] {label} 下载地址: {url}", flush=True)
    with requests.get(url, stream=True, timeout=(10, 60)) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        last_downloaded = 0
        last_time = time.monotonic()
        last_log_time = 0.0

        if total_size > 0:
            print(f"[ASR] {label} 远端大小: {format_bytes(total_size)}", flush=True)
        else:
            print(f"[ASR] {label} 远端大小未知，将显示已下载大小", flush=True)

        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                file.write(chunk)
                downloaded += len(chunk)

                now = time.monotonic()
                if now - last_log_time < 5 and (not total_size or downloaded < total_size):
                    continue

                elapsed = max(now - last_time, 0.001)
                speed = max(downloaded - last_downloaded, 0) / elapsed
                if total_size > 0:
                    percent = min(downloaded / total_size * 100, 100)
                    remaining = max(total_size - downloaded, 0)
                    print(
                        f"[ASR] {label} 下载中: {percent:.1f}% "
                        f"({format_bytes(downloaded)}/{format_bytes(total_size)}), "
                        f"速度 {format_bytes(int(speed))}/s, 剩余 {format_bytes(remaining)}",
                        flush=True,
                    )
                else:
                    print(
                        f"[ASR] {label} 下载中: 已下载 {format_bytes(downloaded)}, "
                        f"速度 {format_bytes(int(speed))}/s",
                        flush=True,
                    )
                last_downloaded = downloaded
                last_time = now
                last_log_time = now

    os.replace(temp_path, output_path)
    print(f"[ASR] {label} 下载完成: {format_bytes(os.path.getsize(output_path))}", flush=True)
    return output_path


def install_modelscope_zip(zip_path: str, target_root: str, required_model_dir: str, required_files: list[str]) -> str:
    temp_dir = tempfile.mkdtemp(prefix="faster_whisper_ms_install_")
    try:
        print(f"[ASR] 解压魔塔模型包: {zip_path}", flush=True)
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(temp_dir)

        source_model_dir = os.path.join(temp_dir, required_model_dir)
        if not os.path.isdir(source_model_dir):
            entries = os.listdir(temp_dir)
            if len(entries) == 1:
                candidate = os.path.join(temp_dir, entries[0], required_model_dir)
                if os.path.isdir(candidate):
                    source_model_dir = candidate

        if not os.path.isdir(source_model_dir):
            raise FileNotFoundError(f"模型包内缺少目录: {required_model_dir}")

        os.makedirs(target_root, exist_ok=True)
        destination = os.path.join(target_root, required_model_dir)
        if os.path.exists(destination):
            remove_path(destination)
        shutil.move(source_model_dir, destination)

        if not has_required_files(destination, required_files):
            raise FileNotFoundError(f"模型安装不完整: {destination}")

        print(f"[ASR] 魔塔模型安装完成: {destination}", flush=True)
        return destination
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def download_large_v3_from_modelscope(required_files: list[str]) -> str:
    target_root = "tools/asr/models"
    target_model_dir = "faster-whisper-large-v3"
    target_model_path = os.path.join(target_root, target_model_dir)
    temp_dir = tempfile.mkdtemp(prefix="faster_whisper_ms_download_")
    try:
        print(
            f"Downloading model from ModelScope: {MODELSCOPE_PRETRAINED_REPO}/{MODELSCOPE_FASTER_WHISPER_ZIP} "
            f"to {target_model_path}",
            flush=True,
        )
        zip_path = os.path.join(temp_dir, MODELSCOPE_FASTER_WHISPER_ZIP)
        download_file_with_progress(
            modelscope_resolve_url(MODELSCOPE_PRETRAINED_REPO, MODELSCOPE_FASTER_WHISPER_ZIP),
            zip_path,
            "faster-whisper-large-v3",
        )
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"魔塔模型包下载失败: {MODELSCOPE_FASTER_WHISPER_ZIP}")

        return install_modelscope_zip(zip_path, target_root, target_model_dir, required_files)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def download_modelscope_snapshot(model_size: str, required_files: list[str]) -> str:
    model_path = "tools/asr/models"
    resolved_model_path = os.path.join(
        model_path,
        f"faster-whisper-{model_size}".replace("whisper-distil", "distil-whisper"),
    )
    scoped_files = [
        f"faster-whisper-{model_size}/{file}".replace("whisper-distil", "distil-whisper")
        for file in required_files
    ]

    print(f"Downloading model from ModelScope: {MODELSCOPE_FASTER_WHISPER_REPO} to {resolved_model_path}", flush=True)
    stop_progress = start_download_progress_logger(
        f"faster-whisper-{model_size}",
        resolved_model_path,
        required_files,
    )
    try:
        snapshot_download_ms(
            MODELSCOPE_FASTER_WHISPER_REPO,
            local_dir=model_path,
            allow_patterns=scoped_files,
        )
    finally:
        stop_progress()

    if not has_required_files(resolved_model_path, required_files):
        raise FileNotFoundError(f"Model download incomplete: {resolved_model_path}")
    return resolved_model_path


def download_model(model_size: str):
    model_size = normalize_model_size(model_size)
    repo_id, hf_model_path, ms_model_path = get_model_locations(model_size)

    files: list[str] = [
        "config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.txt",
    ]
    if "large-v3" in model_size or "distil" in model_size:
        files.append("preprocessor_config.json")
        files.append("vocabulary.json")

        files.remove("vocabulary.txt")

    if has_required_files(hf_model_path, files):
        print(f"Using cached model: {hf_model_path}")
        return hf_model_path
    if has_required_files(ms_model_path, files):
        print(f"Using cached model: {ms_model_path}")
        return ms_model_path

    if model_size == "large-v3":
        return download_large_v3_from_modelscope(files)
    return download_modelscope_snapshot(model_size, files)


def normalize_model_size(model_size: str) -> str:
    return "large-v3" if model_size == "large" else model_size


def load_model_from_path(model_path: str, precision: str):
    print("loading faster whisper model:", model_path, model_path)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return WhisperModel(model_path, device=device, compute_type=precision)


def create_model(model_size: str, precision: str):
    return load_model_from_path(download_model(model_size), precision)


def transcribe_with_model(
    model,
    file_path: str,
    language: str,
    beam_size: int = 5,
    vad_filter: bool = True,
    vad_parameters: Optional[Dict[str, int]] = None,
    funasr_fallback: Optional[Callable[[str, str], str]] = None,
) -> Tuple[str, str]:
    resolved_language = None if language == "auto" else language
    segments, info = model.transcribe(
        audio=file_path,
        beam_size=beam_size,
        vad_filter=vad_filter,
        vad_parameters=vad_parameters or dict(min_silence_duration_ms=700),
        language=resolved_language,
    )
    detected_language = (info.language or language or "auto").lower()
    text = ""

    if detected_language in ["zh", "yue"] and funasr_fallback is not None:
        print("检测为中文文本, 转 FunASR 处理")
        text = funasr_fallback(file_path, detected_language)

    if text == "":
        for segment in segments:
            text += segment.text

    return detected_language, text


def recognize_with_model(
    model,
    input_path: str,
    language: str,
    beam_size: int = 5,
    vad_filter: bool = True,
    vad_parameters: Optional[Dict[str, int]] = None,
    funasr_fallback: Optional[Callable[[str, str], str]] = None,
) -> Tuple[str, List[Dict[str, str]]]:
    input_files, output_file_name = resolve_inputs(input_path)
    recognition_results: List[Dict[str, str]] = []

    for file_name, file_path in tqdm(input_files):
        try:
            detected_language, text = transcribe_with_model(
                model,
                file_path,
                language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters=vad_parameters,
                funasr_fallback=funasr_fallback,
            )
            recognition_results.append(
                {
                    "audio_path": file_path,
                    "speaker": output_file_name,
                    "language": detected_language.upper(),
                    "text": text,
                }
            )
        except Exception as e:
            print(e)
            traceback.print_exc()

    return output_file_name, recognition_results


def execute_asr(input_folder, output_folder, model_path, language, precision):
    model = load_model_from_path(model_path, precision)
    output_file_name, recognition_results = recognize_with_model(
        model,
        input_folder,
        language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=700),
        funasr_fallback=only_asr,
    )
    return write_output_file(output_folder, output_file_name, recognition_results)


load_cudnn()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_folder", type=str, required=True, help="Path to the folder or audio file to transcribe."
    )
    parser.add_argument("-o", "--output_folder", type=str, required=True, help="Output folder to store transcriptions.")
    parser.add_argument(
        "-s",
        "--model_size",
        type=str,
        default="large-v3",
        choices=get_models(),
        help="Model Size of Faster Whisper",
    )
    parser.add_argument(
        "-l", "--language", type=str, default="ja", choices=language_code_list, help="Language of the audio files."
    )
    parser.add_argument(
        "-p",
        "--precision",
        type=str,
        default="float16",
        choices=["float16", "float32", "int8"],
        help="fp16, int8 or fp32",
    )

    cmd = parser.parse_args()
    model_path = download_model(cmd.model_size)
    output_file_path = execute_asr(
        input_folder=cmd.input_folder,
        output_folder=cmd.output_folder,
        model_path=model_path,
        language=cmd.language,
        precision=cmd.precision,
    )
