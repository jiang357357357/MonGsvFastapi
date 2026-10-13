"""Train one small real CUDA epoch in an isolated workspace and export a model."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Code.FastApi.Base.Training.sovits_training.service import (
    SoVITSTrainingConfig, SoVITSTrainingRequest, SoVITSTrainingService,
)
from Code.FastApi.Base.Training.gpt_training.service import (
    GPTTrainingConfig, GPTTrainingRequest, GPTTrainingService,
)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v5turbo")
    parser.add_argument("--gpt", action="store_true", help="Test GPT training with the existing V2ProPlus semantic dataset")
    args = parser.parse_args()
    source = ROOT / "Resources/Train/Projects/明日方舟/霍尔海雅/v2ProPlus/dataset"
    assert not args.gpt or args.version == "v2ProPlus", "GPT regression uses the V2ProPlus semantic dataset"
    workspace = ROOT / "Data/Temp/UpgradeV5Training" / (args.version + ("-gpt" if args.gpt else ""))
    dataset = workspace / "dataset"
    export = workspace / "export"
    for folder in ("4-cnhubert", "5-wav32k", "7-sv_cn"):
        (dataset / folder).mkdir(parents=True, exist_ok=True)
    sources = [source]
    if args.gpt:
        sources += [p for p in (ROOT / "Resources/Train/Projects").glob("*/*/v2ProPlus/dataset")
                    if p != source and (p / "6-name2semantic.tsv").exists()]
    records = [(directory, line) for directory in sources
               for line in (directory / "2-name2text.txt").read_text().splitlines()]
    target_count = 100 if args.gpt else 4
    chosen = []
    for record_source, line in records:
        fields = line.split("\t")
        if len(fields) != 4:
            continue
        name = fields[0]
        if name in {row.split("\t")[0] for _, row in chosen}:
            continue
        if args.gpt and not (record_source / "3-bert" / (name + ".pt")).exists():
            continue
        audio = record_source / "5-wav32k" / name
        hubert = record_source / "4-cnhubert" / (name + ".pt")
        if audio.exists() and hubert.exists() and 2 <= sf.info(audio).duration <= (8 if args.gpt else 4):
            chosen.append((record_source, line))
            shutil.copy2(audio, dataset / "5-wav32k" / name)
            shutil.copy2(hubert, dataset / "4-cnhubert" / hubert.name)
            if args.version in {"v2Pro", "v2ProPlus"}:
                shutil.copy2(record_source / "7-sv_cn" / (name + ".pt"), dataset / "7-sv_cn" / (name + ".pt"))
        if len(chosen) == target_count:
            break
    assert len(chosen) == target_count, f"Need {target_count} real short training examples"
    (dataset / "2-name2text.txt").write_text("\n".join(row for _, row in chosen) + "\n")
    if args.gpt:
        (dataset / "3-bert").mkdir(exist_ok=True)
        names = {line.split("\t")[0] for _, line in chosen}
        selected = []
        for record_source in {directory for directory, _ in chosen}:
            semantic = (record_source / "6-name2semantic.tsv").read_text().splitlines()
            source_names = {row.split("\t")[0] for directory, row in chosen if directory == record_source}
            selected += [row for row in semantic[1:] if row.split("\t")[0] in source_names]
        assert len(selected) == len(names)
        (dataset / "6-name2semantic.tsv").write_text("\n".join([semantic[0], *selected]) + "\n")
        for record_source, row in chosen:
            name = row.split("\t")[0]
            shutil.copy2(record_source / "3-bert" / (name + ".pt"), dataset / "3-bert" / (name + ".pt"))
        request = GPTTrainingRequest(exp_name="upgrade-smoke", exp_root=str(workspace.parent),
                                     workspace_dir=str(workspace), model_output_dir=str(export),
                                     config=GPTTrainingConfig(version=args.version, batch_size=4, total_epoch=1,
                                                              save_every_epoch=1))
        service = GPTTrainingService(str(ROOT))
    else:
        request = SoVITSTrainingRequest(exp_name="upgrade-smoke", exp_root=str(workspace.parent),
                                   workspace_dir=str(workspace), model_output_dir=str(export),
                                   config=SoVITSTrainingConfig(version=args.version, batch_size=4, total_epoch=1,
                                                               save_every_epoch=1, lora_rank=4, if_grad_ckpt=True))
        service = SoVITSTrainingService(str(ROOT))
    start = time.perf_counter()
    response = await service.start_training(request)
    assert response.success, response.message
    try:
        while True:
            status = service.get_training_status(response.job_id)
            if status.status != "running":
                break
            assert time.perf_counter() - start < 1200, "Smoke training timed out"
            await asyncio.sleep(1)
        assert status.status == "completed", status.error_message
        models = sorted(export.glob("*.ckpt" if args.gpt else "*.pth"))
        assert models, "Training did not export a checkpoint"
        report = {"version": args.version, "type": "gpt" if args.gpt else "sovits", "status": status.status, "elapsed": time.perf_counter() - start,
                  "source_examples": len(chosen), "epochs": 1, "model": str(models[-1]),
                  "log": status.log_file, "config": response.config_file}
        (workspace / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print("TRAIN_RESULT", json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        service.stop_training(response.job_id)


if __name__ == "__main__":
    asyncio.run(main())
