from src.counter import PeopleCounter


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
