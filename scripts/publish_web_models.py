from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    from scripts.model_registry import MODEL_REGISTRY
except ModuleNotFoundError:
    from model_registry import MODEL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "models" / "out"
WEB_MODEL_DIR = ROOT / "site" / "public" / "generated" / "models"


def main() -> None:
    allow_missing = "--allow-missing" in sys.argv
    WEB_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []

    for entry in MODEL_REGISTRY:
        source = OUT_DIR / f"{entry.name}.stl"
        if not source.exists():
            missing.append(source.name)
            continue
        shutil.copy2(source, WEB_MODEL_DIR / source.name)

    if missing and not allow_missing:
        raise FileNotFoundError(
            "Missing STL exports for web publishing: " + ", ".join(sorted(missing))
        )


if __name__ == "__main__":
    main()
