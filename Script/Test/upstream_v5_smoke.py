"""Real CUDA synthesis checks for an upstream upgrade, using local model assets."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Code.FastApi.Base.Inference.service import InferenceConfig, InferenceRequest, InferenceService


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v5", action="store_true")
    parser.add_argument("--version", choices=["v2ProPlus", "v5dev", "v5turbo"])
    parser.add_argument("--graph", action="store_true")
    parser.add_argument("--lora", type=Path)
    parser.add_argument("--gpt", type=Path, help="Use an exported GPT checkpoint")
    parser.add_argument("--sovits", type=Path, help="Use an exported full SoVITS checkpoint")
    parser.add_argument("--output", default="Data/Output/UpgradeV5")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    role = ROOT / "Resources/Model/明日方舟/霍尔海雅/v2ProPlus"
    references = list((role / "emotion").glob("*.wav"))
    reference = next(p for p in references if 3 <= sf.info(p).duration <= 10)
    prompt = re.sub(r"^\[[^]]*\]\[[^]]*\]", "", reference.stem)
    models = [("v2ProPlus", next((role / "GPT").glob("*.ckpt")), next((role / "SoVITS").glob("*.pth")))]
    if args.v5:
        for version in ("v5dev", "v5turbo"):
            models.append((version, ROOT / "GPT_SoVITS/pretrained_models/s1v3.ckpt",
                           ROOT / f"GPT_SoVITS/pretrained_models/gsv-v5-pretrained/s2G{version}.pth"))
    if args.version:
        if args.version == "v2ProPlus":
            models = models[:1]
        else:
            models = [(args.version, ROOT / "GPT_SoVITS/pretrained_models/s1v3.ckpt",
                       ROOT / f"GPT_SoVITS/pretrained_models/gsv-v5-pretrained/s2G{args.version}.pth")]
    if args.lora:
        version = {b"07": "v5dev", b"08": "v5turbo"}[args.lora.open("rb").read(2)]
        models = [(version, ROOT / "GPT_SoVITS/pretrained_models/s1v3.ckpt", args.lora)]
    if args.gpt or args.sovits:
        assert len(models) == 1, "Choose one model version for checkpoint reload checks"
        version, gpt, sovits = models[0]
        models = [(version, args.gpt or gpt, args.sovits or sovits)]
    assert torch.cuda.is_available(), "A real CUDA device is required"
    report = {"gpu": torch.cuda.get_device_name(0), "torch": torch.__version__, "reference": str(reference), "cases": []}
    service = InferenceService(str(ROOT))

    def save_case(version, label, sr, audio, elapsed, config):
        assert sr == (48000 if version.startswith("v5") else 32000), (version, sr)
        assert len(audio) > sr * 0.2, "Audio is unexpectedly short"
        assert np.isfinite(audio).all(), "Audio contains nonfinite values"
        assert np.max(np.abs(audio.astype(np.float32))) > 10, "Audio is silent"
        path = output / f"{version}-{label}.wav"
        sf.write(path, audio, sr, subtype="PCM_16")
        item = {"model": version, "case": label, "path": str(path), "sample_rate": sr,
                "duration": len(audio) / sr, "elapsed": elapsed, "rms": float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))),
                "sample_steps": config.sample_steps, "cfg_rate": config.cfg_rate,
                "graph_requested": config.use_cuda_graph,
                "accel_created": service.tts_pipeline.t2s_accel is not None,
                "graph_enabled": bool(getattr(service.tts_pipeline.t2s_accel, "graph_enabled", False)),
                "gpu_memory_peak": torch.cuda.max_memory_allocated()}
        report["cases"].append(item)
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print("RESULT", json.dumps(item, ensure_ascii=False), flush=True)

    try:
        for version, gpt, sovits in models:
            assert service.load_models(str(gpt), str(sovits)), "Model loading failed: " + version
            assert service.model_version == version, service.model_version
            cases = [("zh", "这是升级后的真实语音合成测试。今天的天气很好。", "zh", 1.0),
                     ("en-speed", "This is a real test of the upgraded speech system.", "en", 1.15)]
            if args.graph:
                cases.append(("graph", "现在测试加速模式下的语音合成。", "zh", 1.0))
                cases.append(("graph-warm", "现在测试加速模式下的语音合成。", "zh", 1.0))
            if version.startswith("v5"):
                cases.append(("sampling", "测试自定义采样参数。", "zh", 1.0))
            for label, text, language, speed in cases:
                config = InferenceConfig(seed=1234, speed=speed, use_cuda_graph=label.startswith("graph"), use_flash_attention=False)
                if label == "sampling":
                    config.sample_steps = 8 if version == "v5dev" else 2
                    config.cfg_rate = 1.0 if version == "v5dev" else 0.0
                request = InferenceRequest(text=text, text_language=language, ref_audio_path=str(reference),
                                           prompt_text=prompt, prompt_language="zh", config=config)
                torch.cuda.reset_peak_memory_stats()
                start = time.perf_counter()
                response = await service.inference(request)
                assert response.success, response.error_details or response.message
                audio, sr = sf.read(response.audio_path, dtype="int16")
                save_case(version, label, sr, audio, time.perf_counter() - start, config)
            request = InferenceRequest(text="第一句测试分段返回。第二句检查音频采样率。", ref_audio_path=str(reference),
                                       prompt_text=prompt, config=InferenceConfig(seed=1234))
            start = time.perf_counter()
            chunks = list(service.stream_inference(request))
            assert chunks and len({sr for sr, _ in chunks}) == 1
            save_case(version, "stream", chunks[0][0], np.concatenate([audio for _, audio in chunks]),
                      time.perf_counter() - start, request.config)
            report["cases"][-1]["chunks"] = len(chunks)
            report["cases"][-1]["stream_mode"] = "segments" if version.startswith("v5") else "tokens"
            service.unload_models(reason="upgrade_smoke")
    finally:
        service.unload_models(reason="upgrade_smoke_cleanup")
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
