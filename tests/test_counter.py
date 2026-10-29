import pytest

from src.counter import DIRECTION_IN, DIRECTION_OUT, LineCounter, PeopleCounter, parse_line

# Línea vertical x=100 de y=0 a y=200. Con p1 arriba y p2 abajo:
# derecha de la línea = lado negativo, izquierda = lado positivo.
P1, P2 = (100.0, 0.0), (100.0, 200.0)


def walk(counter: LineCounter, tid: int, xs: list[float], y: float = 100.0, start: int = 0) -> None:
    """Mueve un track horizontalmente por las posiciones x dadas."""
    for i, x in enumerate(xs):
        counter.update([tid], [(x, y)], frame_idx=start + i)


def test_in_frame_and_max_simultaneous() -> None:
    c = PeopleCounter(min_track_frames=1)
    c.update(3, [1, 2, 3])
    c.update(1, [1])
    assert c.in_frame == 1
    assert c.max_simultaneous == 3


def test_unique_requires_min_track_frames() -> None:
    c = PeopleCounter(min_track_frames=3)
    for _ in range(2):
        c.update(2, [1, 2])
    assert c.unique_count == 0
    c.update(1, [1])
    assert c.unique_count == 1  # solo el ID 1 llegó a 3 frames


def test_none_ids_are_ignored() -> None:
    c = PeopleCounter(min_track_frames=1)
    c.update(2, [None, None])
    assert c.in_frame == 2
    assert c.unique_count == 0


def test_same_id_counted_once() -> None:
    c = PeopleCounter(min_track_frames=1)
    for _ in range(10):
        c.update(1, [7])
    assert c.unique_count == 1


# ---------- LineCounter ----------

def test_side_sign() -> None:
    c = LineCounter(P1, P2)
    assert c.side((150, 100)) == -1
    assert c.side((50, 100)) == 1
    assert c.side((100, 100)) == 0


def test_right_to_left_is_in() -> None:
    c = LineCounter(P1, P2, min_track_frames=1)
    walk(c, 1, [160, 140, 120, 80, 60])
    assert (c.in_count, c.out_count) == (1, 0)
    assert c.events[0].direction == DIRECTION_IN
    assert c.events[0].frame_idx == 3


def test_left_to_right_is_out() -> None:
    c = LineCounter(P1, P2, min_track_frames=1)
    walk(c, 1, [40, 60, 80, 120, 140])
    assert (c.in_count, c.out_count) == (0, 1)


def test_invert_swaps_direction() -> None:
    c = LineCounter(P1, P2, min_track_frames=1, invert=True)
    walk(c, 1, [160, 120, 80])
    assert (c.in_count, c.out_count) == (0, 1)


def test_crossing_outside_segment_is_ignored() -> None:
    c = LineCounter(P1, P2, min_track_frames=1)
    walk(c, 1, [160, 120, 80, 60], y=300)  # pasa por la prolongación (y > 200)
    assert (c.in_count, c.out_count) == (0, 0)


def test_id_counted_once_per_direction() -> None:
    c = LineCounter(P1, P2, min_track_frames=1)
    walk(c, 1, [120, 80, 120, 80, 120, 80])  # va y viene sobre la puerta
    assert (c.in_count, c.out_count) == (1, 1)


def test_young_tracks_are_ignored() -> None:
    c = LineCounter(P1, P2, min_track_frames=3)
    walk(c, 1, [120, 80, 60])  # cruza en su 2º frame de vida
    assert c.in_count == 0
    walk(c, 2, [160, 140, 120, 80])  # cruza en su 4º frame
    assert c.in_count == 1


def test_point_on_line_waits_for_full_crossing() -> None:
    c = LineCounter(P1, P2, min_track_frames=1)
    walk(c, 1, [120, 100, 100, 80])
    assert c.in_count == 1
    assert c.events[0].frame_idx == 3


def test_none_ids_and_multiple_tracks() -> None:
    c = LineCounter(P1, P2, min_track_frames=1)
    c.update([1, 2, None], [(120, 50), (80, 150), (120, 100)], frame_idx=0)
    c.update([1, 2, None], [(80, 50), (120, 150), (80, 100)], frame_idx=1)
    assert (c.in_count, c.out_count) == (1, 1)
    assert {e.direction for e in c.events} == {DIRECTION_IN, DIRECTION_OUT}


def test_band_ignores_jitter_on_the_line() -> None:
    # Sin banda: alguien parado sobre la línea que oscila ±5 px cuenta IN y OUT
    jitter = [130, 105, 95, 105, 95, 105]
    no_band = LineCounter(P1, P2, min_track_frames=1)
    walk(no_band, 1, jitter)
    assert (no_band.in_count, no_band.out_count) == (1, 1)
    # Con banda de 20 px no cuenta nada
    with_band = LineCounter(P1, P2, min_track_frames=1, band=20)
    walk(with_band, 1, jitter)
    assert (with_band.in_count, with_band.out_count) == (0, 0)


def test_band_counts_full_crossing() -> None:
    c = LineCounter(P1, P2, min_track_frames=1, band=20)
    walk(c, 1, [150, 115, 100, 90, 85, 70])  # sale de la banda por la izquierda en x=70
    assert c.in_count == 1
    assert c.events[0].frame_idx == 5


def test_band_exit_and_return_same_side_is_not_a_crossing() -> None:
    c = LineCounter(P1, P2, min_track_frames=1, band=20)
    walk(c, 1, [150, 110, 90, 110, 150])  # entra a la banda y vuelve por donde vino
    assert (c.in_count, c.out_count) == (0, 0)


def test_signed_distance_in_pixels() -> None:
    c = LineCounter(P1, P2)
    assert c.signed_distance((130, 50)) == -30
    assert c.signed_distance((60, 50)) == 40


def test_once_per_id_keeps_only_first_crossing() -> None:
    # Sale (izq→der) y luego rebota sobre la línea: solo cuenta la salida
    c = LineCounter(P1, P2, min_track_frames=1, once_per_id=True)
    walk(c, 1, [40, 80, 120, 90, 130, 180])
    assert (c.in_count, c.out_count) == (0, 1)
    assert [e.direction for e in c.events] == [DIRECTION_OUT]


def test_once_per_id_still_counts_different_ids() -> None:
    c = LineCounter(P1, P2, min_track_frames=1, once_per_id=True)
    walk(c, 1, [120, 80])
    walk(c, 2, [80, 120])
    assert (c.in_count, c.out_count) == (1, 1)


def test_negative_band_raises() -> None:
    with pytest.raises(ValueError):
        LineCounter(P1, P2, band=-1)


def test_degenerate_line_raises() -> None:
    with pytest.raises(ValueError):
        LineCounter((5, 5), (5, 5))


def test_parse_line() -> None:
    assert parse_line("120, 400,1100,400") == ((120.0, 400.0), (1100.0, 400.0))
    with pytest.raises(ValueError):
        parse_line("1,2,3")
