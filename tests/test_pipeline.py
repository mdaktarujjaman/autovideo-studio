import pytest

from autovideo.pipeline import parse_selection
from autovideo.render import split_jobs


def test_selection_defaults_to_all():
    assert parse_selection("", 3) == [1, 2, 3]


def test_selection_ranges_and_lists():
    assert parse_selection("5-8", 10) == [5, 6, 7, 8]
    assert parse_selection("1,3-4", 10) == [1, 3, 4]
    assert parse_selection("2,2", 5) == [2]


@pytest.mark.parametrize("bad", ["0", "11", "4-2", "a", "1-"])
def test_selection_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_selection(bad, 10)


def test_split_jobs_balances_by_duration():
    jobs = [{"index": i, "duration": d} for i, d in enumerate([8, 1, 1, 1, 1, 4])]
    groups = split_jobs(jobs, 2)
    loads = sorted(sum(job["duration"] for job in group) for group in groups)
    assert loads == [8, 8]
    assert sum(len(group) for group in groups) == 6