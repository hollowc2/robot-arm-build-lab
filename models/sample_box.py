from pathlib import Path

from build123d import Box, export_step, export_stl


OUT_DIR = Path(__file__).parent / "out"


def build_model() -> Box:
    return Box(40, 30, 12)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    model = build_model()
    export_step(model, OUT_DIR / "sample_box.step")
    export_stl(model, OUT_DIR / "sample_box.stl")

    print(f"Wrote {OUT_DIR / 'sample_box.step'}")
    print(f"Wrote {OUT_DIR / 'sample_box.stl'}")


if __name__ == "__main__":
    main()
