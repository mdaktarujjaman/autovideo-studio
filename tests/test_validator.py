from autovideo.parser import DEFAULTS, SCENE_DEFAULTS
from autovideo.validator import validate


def make_config(tmp_path):
    font = tmp_path / "font.ttf"
    font.write_bytes(b"x")
    return {**DEFAULTS, "font": str(font), "fps": 24}


def make_scene(**overrides):
    return {**SCENE_DEFAULTS, "text": "ছোট একটি বাক্য।", **overrides}


def levels(issues):
    return [(issue.level, issue.scene) for issue in issues]


def test_valid_script_has_no_issues(tmp_path):
    assert validate(make_config(tmp_path), [make_scene()]) == []


def test_empty_script_is_error(tmp_path):
    assert ("error", 0) in levels(validate(make_config(tmp_path), []))


def test_unknown_type_is_error(tmp_path):
    issues = validate(make_config(tmp_path), [make_scene(type="slider")])
    assert ("error", 1) in levels(issues)


def test_counter_rejects_bengali_digits(tmp_path):
    scene = make_scene(type="counter", value="১৩", label="জন")
    assert ("error", 1) in levels(validate(make_config(tmp_path), [scene]))


def test_counter_accepts_english_digits(tmp_path):
    scene = make_scene(type="counter", value="13", label="জন")
    assert validate(make_config(tmp_path), [scene]) == []


def test_bullets_over_limit_warns(tmp_path):
    scene = make_scene(type="bullets", items="এক|দুই|তিন|চার")
    assert ("warning", 1) in levels(validate(make_config(tmp_path), [scene]))


def test_long_voiceover_warns(tmp_path):
    scene = make_scene(text=" ".join(["শব্দ"] * 30))
    assert ("warning", 1) in levels(validate(make_config(tmp_path), [scene]))


def test_missing_image_is_error(tmp_path):
    scene = make_scene(image=str(tmp_path / "missing.jpg"))
    assert ("error", 1) in levels(validate(make_config(tmp_path), [scene]))