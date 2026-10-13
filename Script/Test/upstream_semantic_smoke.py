"""Extract semantic tokens from real local HuBERT features on CUDA."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Code.FastApi.Base.DatasetFormatting.semantic_encoding.service import (
    SemanticEncodingConfig, SemanticEncodingRequest, SemanticEncodingService,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v5turbo")
    args = parser.parse_args()
    assert torch.cuda.is_available(), "Real CUDA hardware is required"
    source = ROOT / "Resources/Train/Projects/明日方舟/霍尔海雅/v2ProPlus/dataset"
    output = ROOT / "Data/Output/UpgradeV5" / ("semantic-" + args.version)
    output.mkdir(parents=True, exist_ok=True)
    selected = [line.split("\t") for line in (source / "2-name2text.txt").read_text().splitlines()
                if len(line.split("\t")) == 4 and (source / "4-cnhubert" / (line.split("\t")[0] + ".pt")).is_file()][:2]
    assert len(selected) == 2
    annotations = output / "input.list"
    annotations.write_text("\n".join(f"{row[0]}|smoke|zh|{row[-1]}" for row in selected) + "\n")
    service = SemanticEncodingService(str(ROOT))
    response = service.encode_semantic_sync(SemanticEncodingRequest(
        input_text_file=str(annotations), cnhubert_dir=str(source / "4-cnhubert"),
        experiment_name="upgrade-smoke", output_dir=str(output),
        config=SemanticEncodingConfig(version=args.version, device="cuda"),
    ))
    assert response.success and response.processed_count == 2 and response.failed_count == 0, asdict(response)
    rows = Path(response.output_file).read_text().splitlines()[1:]
    assert len(rows) == 2
    counts = [len(row.split("\t")[1].split()) for row in rows]
    assert min(counts) > 10, counts
    report = {"version": args.version, "gpu": torch.cuda.get_device_name(0), "token_counts": counts, **asdict(response)}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("SEMANTIC_RESULT", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
