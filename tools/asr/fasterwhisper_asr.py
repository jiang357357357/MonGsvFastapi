import argparse
import os
import traceback
from typing import Callable, Dict, List, Optional, Tuple

import requests
import torch
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download as snapshot_download_hf
from modelscope import snapshot_download as snapshot_download_ms
from tqdm import tqdm

from tools.asr.config import get_models
from tools.asr.funasr_asr import only_asr, resolve_inputs, write_output_file
from tools.my_utils import load_cudnn

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}

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

    url = "https://huggingface.co/api/models/gpt2"
    try:
        requests.get(url, timeout=3)
        source = "HF"
    except Exception:
        source = "ModelScope"

    if source == "ModelScope":
        repo_id = "XXXXRT/faster-whisper"
        model_path = "tools/asr/models"
        files = [f"faster-whisper-{model_size}/{file}".replace("whisper-distil", "distil-whisper") for file in files]
    else:
        model_path = hf_model_path

    if source == "HF":
        print(f"Downloading model from HuggingFace: {repo_id} to {model_path}")
        snapshot_download_hf(
            repo_id,
            local_dir=model_path,
            local_dir_use_symlinks=False,
            allow_patterns=files,
        )
    else:
        print(f"Downloading model from ModelScope: {repo_id} to {model_path}")
        snapshot_download_ms(
            repo_id,
            local_dir=model_path,
            allow_patterns=files,
        )
        resolved_model_path = model_path + f"/faster-whisper-{model_size}".replace("whisper-distil", "distil-whisper")
        if not has_required_files(resolved_model_path, [os.path.basename(file) for file in files]):
            raise FileNotFoundError(f"Model download incomplete: {resolved_model_path}")
        return resolved_model_path

    if not has_required_files(model_path, files):
        raise FileNotFoundError(f"Model download incomplete: {model_path}")
    return model_path


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
