"""File locations for the two hand-labelled evaluation sets.

dev  : used to FIND and FIX extractor mistakes (we look at it freely).
test : held out. Labelled before any tuning, used only to MEASURE the final
       result. Tuning on the test set would make the score look better than
       it really is (like studying the exact exam questions).
"""

from __future__ import annotations

from pathlib import Path

from skillpulse.config import PROJECT_ROOT

EVAL_DIR = PROJECT_ROOT / "data" / "eval"
SPLITS = ("dev", "test")


def sample_path(split: str) -> Path:
    return EVAL_DIR / ("sample_jobs.csv" if split == "dev" else f"{split}_jobs.csv")


def labels_path(split: str) -> Path:
    return EVAL_DIR / ("labels.csv" if split == "dev" else f"{split}_labels.csv")
