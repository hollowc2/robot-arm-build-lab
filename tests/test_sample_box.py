from models.sample_box import build_model


def test_sample_box_has_volume() -> None:
    assert build_model().volume > 0
