# -*- coding:utf-8 -*-

import argparse
import os
import traceback
from typing import Any, Dict, List, Tuple

from funasr import AutoModel
from modelscope import snapshot_download
from tqdm import tqdm

funasr_models: Dict[str, Any] = {}  # 存储模型避免重复加载
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
SUPPORTED_BACKENDS = ("classic", "fun-asr-nano", "sensevoice")


def has_required_files(local_dir, required_files):
    return os.path.isdir(local_dir) and all(os.path.exists(os.path.join(local_dir, name)) for name in required_files)


def ensure_snapshot(repo_id, local_dir, required_files):
    if has_required_files(local_dir, required_files):
        print(f"Using cached model: {local_dir}")
        return local_dir

    print(f"Downloading model from ModelScope: {repo_id} -> {local_dir}")
    snapshot_download(repo_id, local_dir=local_dir)

    if not has_required_files(local_dir, required_files):
        raise FileNotFoundError(f"Model download incomplete: {local_dir}")
    return local_dir


def normalize_backend(backend=None):
    backend = (backend or "classic").strip().lower()
    aliases = {
        "damo": "classic",
        "legacy": "classic",
        "paraformer": "classic",
        "funasr-nano": "fun-asr-nano",
        "nano": "fun-asr-nano",
        "sense-voice": "sensevoice",
    }
    backend = aliases.get(backend, backend)
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(f"{backend} is not supported. Supported backends: {', '.join(SUPPORTED_BACKENDS)}")
    return backend


def only_asr(input_file, language, backend="classic"):
    try:
        model = create_model(language, backend=backend)
        text = transcribe_with_model(model, input_file)
    except Exception:
        text = ""
        print(traceback.format_exc())
    return text


def create_model(language="zh", use_cache=True, backend="classic"):
    backend = normalize_backend(backend)
    if language == "yue" and backend in ("fun-asr-nano", "sensevoice"):
        backend = "classic"

    # Nano and SenseVoice are multilingual. Cantonese uses the classic yue model.
    if backend in ("fun-asr-nano", "sensevoice"):
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        cache_key = f"{language}_{backend}"
        if use_cache and cache_key in funasr_models:
            return funasr_models[cache_key]

        if backend == "fun-asr-nano":
            model = AutoModel(
                model="FunAudioLLM/Fun-ASR-Nano-2512",
                trust_remote_code=True,
                hub="hf",
                vad_model="fsmn-vad",
                device=device,
                disable_update=True,
            )
            print(f"FunASR Fun-ASR-Nano 模型加载完成: {language.upper()}")
        else:
            model = AutoModel(
                model="iic/SenseVoiceSmall",
                vad_model="fsmn-vad",
                device=device,
                disable_update=True,
            )
            print(f"FunASR SenseVoice 模型加载完成: {language.upper()}")

        if use_cache:
            funasr_models[cache_key] = model
        return model

    if language == "zh":
        path_vad = ensure_snapshot(
            "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            "tools/asr/models/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            ["configuration.json", "model.pt"],
        )
        path_punc = ensure_snapshot(
            "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
            "tools/asr/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
            ["configuration.json", "model.pt", "tokens.json"],
        )
        path_asr = ensure_snapshot(
            "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "tools/asr/models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            ["configuration.json", "model.pt", "tokens.json"],
        )
        model_revision = "v2.0.4"
        vad_model_revision = punc_model_revision = "v2.0.4"
    elif language == "yue":
        path_asr = ensure_snapshot(
            "iic/speech_UniASR_asr_2pass-cantonese-CHS-16k-common-vocab1468-tensorflow1-online",
            "tools/asr/models/speech_UniASR_asr_2pass-cantonese-CHS-16k-common-vocab1468-tensorflow1-online",
            ["configuration.json"],
        )
        path_vad = path_punc = None
        vad_model_revision = punc_model_revision = ""
        model_revision = "master"
    else:
        raise ValueError(f"{language} is not supported. Supported: zh, yue, ja, en, ko, auto")

    cache_key = f"{language}_{backend}"
    if use_cache and cache_key in funasr_models:
        return funasr_models[cache_key]
    model = AutoModel(
        model=path_asr,
        model_revision=model_revision,
        vad_model=path_vad,
        vad_model_revision=vad_model_revision,
        punc_model=path_punc,
        punc_model_revision=punc_model_revision,
    )
    print(f"FunASR 模型加载完成: {language.upper()}")

    if use_cache:
        funasr_models[cache_key] = model
    return model


def transcribe_with_model(model, input_file: str) -> str:
    return model.generate(input=input_file)[0]["text"]


def resolve_inputs(input_path):
    input_path = os.path.abspath(input_path)
    if os.path.isfile(input_path):
        return [(os.path.basename(input_path), input_path)], os.path.basename(input_path)
    if os.path.isdir(input_path):
        input_file_names = []
        for file_name in sorted(os.listdir(input_path)):
            file_path = os.path.join(input_path, file_name)
            if not os.path.isfile(file_path):
                continue
            if os.path.splitext(file_name)[1].lower() not in AUDIO_EXTENSIONS:
                continue
            input_file_names.append((file_name, file_path))
        return input_file_names, os.path.basename(input_path.rstrip("/\\"))
    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def recognize_with_model(model, input_path: str, language: str) -> Tuple[str, List[Dict[str, str]]]:
    input_files, output_file_name = resolve_inputs(input_path)
    recognition_results: List[Dict[str, str]] = []

    for file_name, file_path in tqdm(input_files):
        try:
            print("\n" + file_name)
            text = transcribe_with_model(model, file_path)
            recognition_results.append(
                {
                    "audio_path": file_path,
                    "speaker": output_file_name,
                    "language": language.upper(),
                    "text": text,
                }
            )
        except Exception:
            print(traceback.format_exc())

    return output_file_name, recognition_results


def write_output_file(output_folder: str, output_file_name: str, recognition_results: List[Dict[str, str]]) -> str:
    output_folder = output_folder or "output/asr_opt"
    os.makedirs(output_folder, exist_ok=True)
    output_file_path = os.path.abspath(f"{output_folder}/{output_file_name}.list")
    lines = [
        "{audio_path}|{speaker}|{language}|{text}".format(**result)
        for result in recognition_results
    ]

    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        print(f"ASR 任务完成->标注文件路径: {output_file_path}\n")
    return output_file_path


def execute_asr(input_folder, output_folder, model_size, language, backend="classic"):
    input_files, output_file_name = resolve_inputs(input_folder)
    model = create_model(language, backend=backend)
    recognition_results: List[Dict[str, str]] = []

    for file_name, file_path in tqdm(input_files):
        try:
            print("\n" + file_name)
            text = transcribe_with_model(model, file_path)
            recognition_results.append(
                {
                    "audio_path": file_path,
                    "speaker": output_file_name,
                    "language": language.upper(),
                    "text": text,
                }
            )
        except Exception:
            print(traceback.format_exc())

    return write_output_file(output_folder, output_file_name, recognition_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_folder", type=str, required=True, help="Path to the folder or audio file to transcribe."
    )
    parser.add_argument("-o", "--output_folder", type=str, required=True, help="Output folder to store transcriptions.")
    parser.add_argument("-s", "--model_size", type=str, default="large", help="Model Size of FunASR is Large")
    parser.add_argument(
        "-l", "--language", type=str, default="zh", choices=["zh", "yue", "ja", "en", "ko", "auto"], help="Language of the audio files."
    )
    parser.add_argument(
        "-p", "--precision", type=str, default="float16", choices=["float16", "float32"], help="fp16 or fp32"
    )
    parser.add_argument(
        "-n", "--name", type=str, default=None, help="Output name for the transcription file."
    )
    parser.add_argument(
        "-b",
        "--backend",
        type=str,
        default="classic",
        choices=SUPPORTED_BACKENDS,
        help="FunASR backend: classic Paraformer, Fun-ASR-Nano, or SenseVoice.",
    )
    cmd = parser.parse_args()
    execute_asr(
        input_folder=cmd.input_folder,
        output_folder=cmd.output_folder,
        model_size=cmd.model_size,
        language=cmd.language,
        backend=cmd.backend,
    )
