"""Exercise actual HTTP and WebSocket synthesis with a temporary test role."""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import re
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
import requests
import soundfile as sf
import websockets

ROOT = Path(__file__).resolve().parents[2]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:40322")
    parser.add_argument("--version", choices=["v2ProPlus", "v5dev", "v5turbo"], default="v5turbo")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    version = args.version
    expected_sr = 48000 if version.startswith("v5") else 32000
    output = ROOT / "Data/Output/UpgradeV5" / ("gateway-" + version)
    output.mkdir(parents=True, exist_ok=True)
    source_role = ROOT / "Resources/Model/明日方舟/霍尔海雅/v2ProPlus"
    reference = next(p for p in (source_role / "emotion").glob("*.wav") if 3 <= sf.info(p).duration <= 10)
    prompt = re.sub(r"^\[[^]]*\]\[[^]]*\]", "", reference.stem)
    if version.startswith("v5"):
        gpt = ROOT / "GPT_SoVITS/pretrained_models/s1v3.ckpt"
        sovits = ROOT / f"GPT_SoVITS/pretrained_models/gsv-v5-pretrained/s2G{version}.pth"
    else:
        gpt = next((source_role / "GPT").glob("*.ckpt"))
        sovits = next((source_role / "SoVITS").glob("*.pth"))
    assert gpt.is_file() and sovits.is_file(), "Real model weights are required"

    def post(path, **kwargs):
        response = requests.post(url + path, timeout=240, **kwargs)
        response.raise_for_status()
        data = response.json()
        assert data.get("success"), data.get("message")
        return data

    def validate(label, audio, sr, elapsed):
        assert sr == expected_sr, sr
        assert len(audio) > sr * .2 and np.isfinite(audio).all()
        assert np.max(np.abs(audio.astype(np.float32))) > 10, "Silent audio"
        path = output / (label + ".wav")
        sf.write(path, audio, sr, subtype="PCM_16")
        return {"path": str(path), "sample_rate": sr, "duration": len(audio) / sr, "elapsed": elapsed}

    report = {"version": version, "url": url, "cases": []}
    # The owned directory contains links; removing it does not delete model assets.
    world = Path(tempfile.mkdtemp(prefix="__upgrade_smoke_", dir=ROOT / "Resources/Model"))
    try:
        role_root = world / "GatewaySmoke" / version
        for directory, path in (("GPT", gpt), ("SoVITS", sovits), ("emotion", reference)):
            folder = role_root / directory
            folder.mkdir(parents=True)
            name = f"[测试][zh]{prompt}.wav" if directory == "emotion" else path.name
            (folder / name).symlink_to(path.resolve())
        roles = requests.get(url + "/api/role/list/", timeout=30).json()["roles"]
        role_id = next(role["id"] for role in roles if role["world_name"] == world.name and role["version"] == version)
        report["role_id"] = role_id
        post("/inference/models/load", data={"gpt_path": str(gpt), "sovits_path": str(sovits)})
        start = time.perf_counter()
        response = post("/inference/tts", data={"text": "测试 HTTP 自定义采样参数。", "ref_audio_path": str(reference),
                        "prompt_text": prompt, "sample_steps": 8 if version == "v5dev" else 2,
                        "cfg_rate": 1.0 if version == "v5dev" else 0.0})
        audio, sr = sf.read(io.BytesIO(base64.b64decode(response["audio_data"])), dtype="int16")
        report["cases"].append({"case": "http-parameters", **validate("http-parameters", audio, sr, time.perf_counter() - start)})
        for mode in ("normal", "accelerated"):
            start = time.perf_counter()
            response = post("/api/synthesis/role-emotion", json={"role_id": role_id, "emotion": "测试",
                            "text": "这是通过角色接口完成的真实语音测试。", "inference_mode": mode})
            audio, sr = sf.read(io.BytesIO(base64.b64decode(response["audio_data"])), dtype="int16")
            report["cases"].append({"case": "http-role-" + mode, **validate("http-role-" + mode, audio, sr, time.perf_counter() - start)})

        start = time.perf_counter()
        first_audio = None
        chunks, events = [], []
        async with websockets.connect(url.replace("http", "ws", 1) + "/ws/tts/stream", max_size=None) as connection:
            await connection.send(json.dumps({"type": "start", "request_id": "upgrade-ws", "role_id": role_id, "emotion": "测试"}))
            while True:
                event = json.loads(await asyncio.wait_for(connection.recv(), timeout=240))
                events.append(event)
                assert event["type"] != "error", event
                if event["type"] == "ready":
                    assert event["stream_mode"] == ("segments" if version.startswith("v5") else "tokens"), event
                    break
            await connection.send(json.dumps({"type": "text", "request_id": "upgrade-ws", "text": "第一句测试真实流式连接。第二句检查音频采样率。"}))
            await connection.send(json.dumps({"type": "finish", "request_id": "upgrade-ws"}))
            while True:
                event = await asyncio.wait_for(connection.recv(), timeout=240)
                if isinstance(event, bytes):
                    chunks.append(np.frombuffer(event, dtype="<i2"))
                    if first_audio is None:
                        first_audio = time.perf_counter() - start
                else:
                    event = json.loads(event)
                    events.append(event)
                    assert event["type"] != "error", event
                    if event["type"] == "audio_start":
                        assert event["sample_rate"] == expected_sr, event
                    if event["type"] == "end":
                        break
        assert chunks, "No PCM received"
        report["cases"].append({"case": "websocket", "first_audio_seconds": first_audio, "chunks": len(chunks), "events": events,
                                **validate("websocket", np.concatenate(chunks), expected_sr, time.perf_counter() - start)})
        report["status"] = "passed"
        print("GATEWAY_RESULT", json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        try:
            post("/inference/models/unload")
        finally:
            shutil.rmtree(world)
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
