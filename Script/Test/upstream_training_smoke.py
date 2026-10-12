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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v5turbo")
    args = parser.parse_args()
    source = ROOT / "Resources/Train/Projects/明日方舟/霍尔海雅/v2ProPlus/dataset"
    workspace = ROOT / "Data/Temp/UpgradeV5Training" / args.version
    dataset = workspace / "dataset"
    export = workspace / "export"
    for folder in ("4-cnhubert", "5-wav32k", "7-sv_cn"):
        (dataset / folder).mkdir(parents=True, exist_ok=True)
    lines = (source / "2-name2text.txt").read_text().splitlines()
    chosen = []
    for line in lines:
        fields = line.split("\t")
        if len(fields) != 4:
            continue
        name = fields[0]
        audio = source / "5-wav32k" / name
        hubert = source / "4-cnhubert" / (name + ".pt")
        if audio.exists() and hubert.exists() and 2 <= sf.info(audio).duration <= 4:
            chosen.append(line)
            shutil.copy2(audio, dataset / "5-wav32k" / name)
            shutil.copy2(hubert, dataset / "4-cnhubert" / hubert.name)
            if args.version in {"v2Pro", "v2ProPlus"}:
                shutil.copy2(source / "7-sv_cn" / (name + ".pt"), dataset / "7-sv_cn" / (name + ".pt"))
        if len(chosen) == 4:
            break
    assert len(chosen) == 4, "Need four real short training examples"
    (dataset / "2-name2text.txt").write_text("\n".join(chosen) + "\n")
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
        models = sorted(export.glob("*.pth"))
        assert models, "Training did not export a checkpoint"
        report = {"version": args.version, "status": status.status, "elapsed": time.perf_counter() - start,
                  "source_examples": len(chosen), "epochs": 1, "model": str(models[-1]),
                  "log": status.log_file, "config": response.config_file}
        (workspace / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print("TRAIN_RESULT", json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        service.stop_training(response.job_id)


if __name__ == "__main__":
    asyncio.run(main())
