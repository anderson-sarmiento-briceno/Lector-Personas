from src.pick_line import display_scale, format_line, to_original


def test_display_scale_fits_4k_and_never_upscales() -> None:
    assert display_scale(3840, 2160) == 1280 / 3840
    assert display_scale(640, 360) == 1.0


def test_points_back_to_original_pixels() -> None:
    scale = display_scale(3840, 2160)
    assert to_original([(400, 300), (400, 720)], scale) == [(1200, 900), (1200, 2160)]


def test_format_line() -> None:
    assert format_line([(1, 2), (3, 4)]) == "1,2,3,4"
