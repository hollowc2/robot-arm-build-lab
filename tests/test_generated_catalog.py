from scripts.generate_catalog import build_catalog, build_viewer_model
from scripts.model_registry import REQUIRED_EXPORT_NAMES


def test_catalog_contains_required_export_names() -> None:
    catalog = build_catalog()
    names = {part["name"] for part in catalog["parts"]}

    assert set(REQUIRED_EXPORT_NAMES).issubset(names)


def test_viewer_model_contains_labeled_parts() -> None:
    viewer_model = build_viewer_model()
    names = {part["name"] for part in viewer_model["parts"]}

    assert viewer_model["format"] == "bbox-assembly-v1"
    assert "geared_base_stator" in names
    assert "bicep_arm_link" in names
    assert "forearm_link" in names
    assert "electronics_enclosure" in names
    assert len(viewer_model["parts"]) >= 30


def test_catalog_includes_electronics_enclosure_metadata() -> None:
    catalog = build_catalog()
    enclosure = next(
        part for part in catalog["parts"] if part["name"] == "electronics_enclosure"
    )

    assert enclosure["material"] == "PETG"
    assert enclosure["validation"] == "fit-test-required"
