# -*- coding:utf-8 -*-

import argparse
import os
import traceback
from typing import Any, Dict, List, Tuple

from funasr import AutoModel
from modelscope import snapshot_download
from tqdm import tqdm

funasr_models = {}  # 存储模型避免重复加载
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}


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


def only_asr(input_file, language):
    try:
        model = create_model(language)
        text = transcribe_with_model(model, input_file)
    except Exception:
        text = ""
        print(traceback.format_exc())
    return text


def create_model(language="zh", use_cache=True):
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
        raise ValueError(f"{language} is not supported")

    vad_model_revision = punc_model_revision = "v2.0.4"

    if use_cache and language in funasr_models:
        return funasr_models[language]
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
        funasr_models[language] = model
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


def execute_asr(input_folder, output_folder, model_size, language):
    input_files, output_file_name = resolve_inputs(input_folder)

    output = []

    model = create_model(language)

    for file_name, file_path in tqdm(input_files):
        try:
            print("\n" + file_name)
            text = model.generate(input=file_path)[0]["text"]
            output.append(f"{file_path}|{output_file_name}|{language.upper()}|{text}")
        except Exception:
            print(traceback.format_exc())

    recognition_results = []
    for line in output:
        audio_path, speaker, recognized_language, text = line.split("|", maxsplit=3)
        recognition_results.append(
            {
                "audio_path": audio_path,
                "speaker": speaker,
                "language": recognized_language,
                "text": text,
            }
        )
    return write_output_file(output_folder, output_file_name, recognition_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_folder", type=str, required=True, help="Path to the folder or audio file to transcribe."
    )
    parser.add_argument("-o", "--output_folder", type=str, required=True, help="Output folder to store transcriptions.")
    parser.add_argument("-s", "--model_size", type=str, default="large", help="Model Size of FunASR is Large")
    parser.add_argument(
        "-l", "--language", type=str, default="zh", choices=["zh", "yue", "auto"], help="Language of the audio files."
    )
    parser.add_argument(
        "-p", "--precision", type=str, default="float16", choices=["float16", "float32"], help="fp16 or fp32"
    )
    parser.add_argument(
        "-n", "--name", type=str, default=None, help="Output name for the transcription file."
    )
    cmd = parser.parse_args()
    execute_asr(
        input_folder=cmd.input_folder,
        output_folder=cmd.output_folder,
        model_size=cmd.model_size,
        language=cmd.language,
    )
