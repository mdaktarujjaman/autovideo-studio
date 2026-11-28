from autovideo.compose import collapse_runs, write_concat


def test_collapse_runs_merges_repeats():
    runs = collapse_runs([["a", "a", "b"], ["b", "c"]])
    assert runs == [["a", 2], ["b", 2], ["c", 1]]


def test_write_concat_lists_durations(tmp_path):
    target = tmp_path / "list.txt"
    write_concat([["x.jpg", 2]], 10, target)
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "duration 0.200000"
    assert lines[0] == lines[2]