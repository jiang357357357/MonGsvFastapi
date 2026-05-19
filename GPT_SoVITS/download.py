import os
import sys

now_dir = os.getcwd()
sys.path.insert(0, now_dir)
from text.g2pw_loader import load_g2pw

g2pw, _ = load_g2pw(
    model_source="GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large",
    v_to_u=False,
    neutral_tone_with_five=True,
)
