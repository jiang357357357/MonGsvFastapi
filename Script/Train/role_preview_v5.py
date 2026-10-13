"""Train V5 from an existing role dataset and generate matching V2PP previews."""
from __future__ import annotations

import argparse
import asyncio
import gc
import json
import re
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Code.FastApi.Base.DatasetFormatting.semantic_encoding.service import (
    SemanticEncodingConfig, SemanticEncodingRequest, SemanticEncodingService,
)
from Code.FastApi.Base.Training.gpt_training.service import GPTTrainingConfig, GPTTrainingRequest, GPTTrainingService
from Code.FastApi.Base.Training.sovits_training.service import SoVITSTrainingConfig, SoVITSTrainingRequest, SoVITSTrainingService


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", default="蔚蓝档案")
    parser.add_argument("--role", default="阿罗娜v21")
    parser.add_argument("--version", choices=["v5dev", "v5turbo"], default="v5turbo")
    parser.add_argument("--gpt-epochs", type=int, default=20)
    parser.add_argument("--sovits-epochs", type=int, default=2)
    parser.add_argument("--lora-rank", type=int, default=32)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--output", default="Data/Output/AronaV5Preview")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fresh-sovits", action="store_true", help="Train SoVITS from its pretrained base in a new workspace")
    args = parser.parse_args()
    assert torch.cuda.is_available(), "Real CUDA hardware is required"
    source = ROOT / "Resources/Train/Projects" / args.world / args.role / "v2ProPlus/dataset"
    source_role = ROOT / "Resources/Model" / args.world / args.role / "v2ProPlus"
    workspace = source.parent.parent / args.version
    dataset = workspace / "dataset"
    model_root = source_role.parent / args.version
    output = (ROOT / args.output).resolve()
    report_path = output / "report.json"
    if workspace.exists() and not args.resume:
        raise FileExistsError(f"Training workspace already exists: {workspace}; use --resume for this run")
    output.mkdir(parents=True, exist_ok=True)
    if args.resume:
        report = json.loads(report_path.read_text())
        assert report["workspace"] == str(workspace) and report["version"] == args.version
    else:
        assert not model_root.exists(), "A role model directory already exists"
        report = {"role": args.role, "world": args.world, "version": args.version,
                  "started": datetime.now().isoformat(), "workspace": str(workspace), "source": str(source),
                  "gpu": torch.cuda.get_device_name(0), "training": {}, "audio": []}

    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    async def train(label, service, request):
        previous = report["training"].get(label)
        previous_config = type(request.config).model_validate(previous["config"]).model_dump() if previous else None
        if previous and previous["status"] == "completed" and previous_config == request.config.model_dump() and Path(previous["model"]).is_file():
            return Path(previous["model"])
        started = time.perf_counter()
        response = await service.start_training(request)
        assert response.success, response.message
        report["phase"] = "training-" + label
        save()
        print("TRAIN_STARTED", label, response.job_id, flush=True)
        try:
            while True:
                status = service.get_training_status(response.job_id)
                if status.status != "running":
                    break
                assert time.perf_counter() - started < 7200, "Training timed out"
                await asyncio.sleep(1)
            assert status.status == "completed", status.error_message
            models = list(Path(request.model_output_dir).glob("*.ckpt" if label == "gpt" else "*.pth"))
            assert models, "No exported model found"
            model = max(models, key=lambda p: p.stat().st_mtime_ns)
            report["training"][label] = {"status": status.status, "job_id": response.job_id, "model": str(model),
                                         "elapsed": time.perf_counter() - started, "config": request.config.model_dump(),
                                         "config_file": response.config_file, "log": status.log_file}
            save()
            print("TRAIN_COMPLETED", label, str(model), flush=True)
            return model
        finally:
            service.stop_training(response.job_id)

    try:
        dataset.mkdir(parents=True, exist_ok=True)
        for folder in ("3-bert", "4-cnhubert", "5-wav32k"):
            if not (dataset / folder).exists():
                shutil.copytree(source / folder, dataset / folder)
        shutil.copy2(source / "2-name2text.txt", dataset / "2-name2text.txt")
        rows = [line.split("\t") for line in (dataset / "2-name2text.txt").read_text().splitlines()]
        assert all(len(row) == 4 for row in rows)
        assert len(rows) >= 100, "GPT training requires at least 100 real examples"
        names = [row[0] for row in rows]
        assert len(set(names)) == len(names)
        for folder in ("3-bert", "4-cnhubert", "5-wav32k"):
            assert all((dataset / folder / (name if folder == "5-wav32k" else name + ".pt")).is_file() for name in names)
        report.update(examples=len(rows), dataset_minutes=sum(sf.info(dataset / "5-wav32k" / name).duration for name in names) / 60)
        annotations = dataset / "input.list"
        annotations.write_text("\n".join(f"{dataset / '5-wav32k' / row[0]}|{args.role}|zh|{row[3]}" for row in rows) + "\n")
        if not report.get("semantic", {}).get("success"):
            report["phase"] = "semantic-encoding"
            save()
            encoder = SemanticEncodingService(str(ROOT))
            response = encoder.encode_semantic_sync(SemanticEncodingRequest(
                input_text_file=str(annotations), cnhubert_dir=str(dataset / "4-cnhubert"),
                experiment_name=args.role, output_dir=str(dataset),
                config=SemanticEncodingConfig(version=args.version, device="cuda"),
            ))
            assert response.success and response.processed_count == len(rows) and response.failed_count == 0, asdict(response)
            report["semantic"] = asdict(response)
            encoder.vq_model.cpu()
            del encoder
            gc.collect()
            torch.cuda.empty_cache()
            save()
            print("SEMANTIC_COMPLETED", len(rows), flush=True)

        experiment = args.role + "-" + args.version
        gpt = await train("gpt", GPTTrainingService(str(ROOT)), GPTTrainingRequest(
            exp_name=experiment, exp_root=str(workspace.parent), workspace_dir=str(workspace),
            model_output_dir=str(workspace / "export/GPT"),
            config=GPTTrainingConfig(version=args.version, total_epoch=args.gpt_epochs,
                                     batch_size=8, num_workers=0, save_every_epoch=5),
        ))
        sovits_workspace = workspace
        if args.fresh_sovits:
            sovits_workspace = workspace / "runs" / ("sovits-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
            run_dataset = sovits_workspace / "dataset"
            run_dataset.mkdir(parents=True)
            # Link only feature data; checkpoint directories stay isolated so
            # the official automatic resume cannot load the previous run.
            for name in ("2-name2text.txt", "3-bert", "4-cnhubert", "5-wav32k", "6-name2semantic.tsv"):
                (run_dataset / name).symlink_to((dataset / name).resolve(), target_is_directory=(dataset / name).is_dir())
            report["previous_sovits"] = report["training"].pop("sovits", None)
            report["fresh_sovits_workspace"] = str(sovits_workspace)
            report["sovits_retrained_at"] = datetime.now().isoformat()
            save()
        sovits = await train("sovits", SoVITSTrainingService(str(ROOT)), SoVITSTrainingRequest(
            exp_name=experiment, exp_root=str(workspace.parent), workspace_dir=str(sovits_workspace),
            model_output_dir=str(sovits_workspace / "export/SoVITS"),
            config=SoVITSTrainingConfig(version=args.version, total_epoch=args.sovits_epochs,
                                        batch_size=4, save_every_epoch=1, lora_rank=args.lora_rank, if_grad_ckpt=True),
        ))
        for folder, model in (("GPT", gpt), ("SoVITS", sovits)):
            (model_root / folder).mkdir(parents=True, exist_ok=True)
            shutil.copy2(model, model_root / folder / model.name)
        (model_root / "emotion").mkdir(exist_ok=True)
        for path in (source_role / "emotion").glob("*.wav"):
            shutil.copy2(path, model_root / "emotion" / path.name)
        (model_root / "meta").mkdir(exist_ok=True)
        metadata = {"role_name": args.role, "display_name": "阿罗娜 V5 Turbo" if args.version == "v5turbo" else "阿罗娜 V5 Dev",
                    "world_name": args.world, "language": "zh", "base_version": args.version,
                    "description": f"{len(rows)} 段中文语料；GPT {args.gpt_epochs} 轮，SoVITS LoRA {args.sovits_epochs} 轮，rank {args.lora_rank}"}
        (model_root / "meta/role.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        report["model_root"] = str(model_root)
        report["phase"] = "synthesis"
        report["seed"] = args.seed
        report.pop("asr_quality", None)
        save()

        from Code.FastApi.Base.Inference.service import InferenceConfig, InferenceRequest, InferenceService
        previews = [
            ("日常", "老师，早上好！今天的日程已经整理好了。工作再忙，也要记得好好吃饭哦。"),
            ("开心", "老师，您终于回来啦！阿罗娜一直在等您呢。今天也一起加油吧！"),
            ("认真", "老师，请放心。无论遇到什么困难，我都会陪在您身边。我们一定可以做到的。"),
        ]
        models = [("v2ProPlus", next((source_role / "GPT").glob("*.ckpt")), next((source_role / "SoVITS").glob("*.pth"))),
                  (args.version, model_root / "GPT" / gpt.name, model_root / "SoVITS" / sovits.name)]
        report["audio"] = []
        service = InferenceService(str(ROOT))
        combined = {}
        try:
            for version, gpt_path, sovits_path in models:
                assert service.load_models(str(gpt_path), str(sovits_path)), version
                assert service.model_version == version
                combined[version] = []
                for emotion, text in previews:
                    reference = next(p for p in (source_role / "emotion").glob("*.wav") if p.name.startswith(f"[{emotion}]"))
                    prompt = re.sub(r"^\[[^]]*\]\[[^]]*\]", "", reference.stem)
                    started = time.perf_counter()
                    result = await service.inference(InferenceRequest(
                        text=text, ref_audio_path=str(reference), prompt_text=prompt, prompt_language="zh", text_language="zh",
                        config=InferenceConfig(seed=args.seed, use_cuda_graph=False),
                    ))
                    assert result.success, result.error_details or result.message
                    audio, sr = sf.read(result.audio_path, dtype="float32")
                    assert sr == (48000 if version.startswith("v5") else 32000)
                    assert np.isfinite(audio).all() and len(audio) > sr and np.max(np.abs(audio)) > .001
                    path = output / f"{version}-{emotion}.wav"
                    sf.write(path, audio, sr, subtype="PCM_16")
                    report["audio"].append({"model": version, "emotion": emotion, "text": text, "reference": str(reference),
                                            "path": str(path), "seed": args.seed, "sample_rate": sr, "duration": len(audio) / sr,
                                            "elapsed": time.perf_counter() - started})
                    if sr != 48000:
                        audio = resample_poly(audio, 3, 2)
                    combined[version].append(audio)
                    save()
                    print("PREVIEW", version, emotion, str(path), flush=True)
                service.unload_models(reason="role_preview_switch")
        finally:
            service.unload_models(reason="role_preview_cleanup")

        silence = np.zeros(48000, dtype=np.float32)
        report["combined"] = {}
        for version, clips in combined.items():
            path = output / f"{version}-三种情绪试听.wav"
            sf.write(path, np.concatenate([part for clip in clips for part in (clip, silence)]), 48000, subtype="PCM_16")
            report["combined"][version] = str(path)
        # Match RMS loudness for listening comparisons; keep original previews above.
        pairs = []
        for i, (emotion, _) in enumerate(previews):
            for version in ("v2ProPlus", args.version):
                audio = combined[version][i]
                rms = max(float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))), 1e-8)
                gain = min(10 ** (-22 / 20) / rms, .98 / max(float(np.max(np.abs(audio))), 1e-8))
                pairs.extend((audio * gain, silence))
        pair_path = output / "V2PP与V5-同文本同参考对照.wav"
        sf.write(pair_path, np.concatenate(pairs), 48000, subtype="PCM_16")
        report.update(comparison=str(pair_path), comparison_order="日常 V2PP/V5；开心 V2PP/V5；认真 V2PP/V5；RMS loudness matched", phase="completed")
        save()
        print("ROLE_PREVIEW_COMPLETED", str(report_path), flush=True)
    except Exception as exc:
        report.update(phase="failed", error=str(exc))
        save()
        raise


if __name__ == "__main__":
    asyncio.run(main())
