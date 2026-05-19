from __future__ import annotations

from pathlib import Path

TEXT_DIR = Path(__file__).resolve().parent
G2PW_SOURCE_DIR = TEXT_DIR / "g2pw"
G2PW_MODEL_DIR = TEXT_DIR / "G2PWModel"
G2PW_SOURCE_FILES = (
    "__init__.py",
    "g2pw.py",
    "onnx_api.py",
    "utils.py",
    "polyphonic.rep",
    "polyphonic-fix.rep",
)
G2PW_MODEL_FILES = (
    "g2pW.onnx",
    "config.py",
    "char_bopomofo_dict.json",
    "MONOPHONIC_CHARS.txt",
    "POLYPHONIC_CHARS.txt",
)


def _format_missing(base_dir: Path, names: tuple[str, ...]) -> str:
    missing = [str((base_dir / name).relative_to(TEXT_DIR.parent.parent)).replace("\\", "/") for name in names if not (base_dir / name).exists()]
    return ", ".join(missing)


def ensure_g2pw_source_available() -> None:
    missing = _format_missing(G2PW_SOURCE_DIR, G2PW_SOURCE_FILES)
    if missing:
        raise ModuleNotFoundError(
            "缺少 GPT_SoVITS/text/g2pw 源码包或源码文件: "
            f"{missing}. "
            "G2PWModel 只包含模型数据，不包含 text.g2pw 的 Python 源码。"
        )


def ensure_g2pw_model_available() -> None:
    missing = _format_missing(G2PW_MODEL_DIR, G2PW_MODEL_FILES)
    if missing:
        raise FileNotFoundError(
            "缺少 G2PWModel 模型文件: "
            f"{missing}. "
            "中文链路需要同时具备 GPT_SoVITS/text/g2pw/ 源码和 GPT_SoVITS/text/G2PWModel/ 数据。"
        )


def load_g2pw(model_source: str | None, *, v_to_u: bool, neutral_tone_with_five: bool):
    ensure_g2pw_source_available()
    ensure_g2pw_model_available()

    try:
        from text.g2pw import G2PWPinyin, correct_pronunciation
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("text.g2pw"):
            raise ModuleNotFoundError(
                "无法导入 text.g2pw。请确认 GPT_SoVITS/text/g2pw/ 已随仓库提交，"
                "而不是只在本地存在。"
            ) from exc
        raise

    g2pw = G2PWPinyin(
        model_dir=str(G2PW_MODEL_DIR).replace("\\", "/"),
        model_source=model_source,
        v_to_u=v_to_u,
        neutral_tone_with_five=neutral_tone_with_five,
    )
    return g2pw, correct_pronunciation
