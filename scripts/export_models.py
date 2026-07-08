from __future__ import annotations

import importlib
import sys
from pathlib import Path

try:
    from scripts.model_registry import MODEL_REGISTRY
except ModuleNotFoundError:
    from model_registry import MODEL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from models.common import export_model

    for entry in MODEL_REGISTRY:
        module = importlib.import_module(entry.module)
        model = module.build_model()
        export_model(model, entry.name)


if __name__ == "__main__":
    main()
