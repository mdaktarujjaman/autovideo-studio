from autovideo.lexicon import apply_lexicon
from autovideo.numbers import BELOW_100, integer_words, speak_numbers
from autovideo.parser import DEFAULTS, SCENE_DEFAULTS
from autovideo.speech import prepare_speech
from autovideo.validator import validate


def base_config(tmp_path, **overrides):
    font = tmp_path / "font.ttf"
    font.write_bytes(b"x")
    return {**DEFAULTS, "font": str(font), "fps": 24, **overrides}


def scene(text):
    return {**SCENE_DEFAULTS, "text": text}


def test_table_has_100_entries():
    assert len(BELOW_100) == 100


def test_integer_words():
    assert integer_words(0) == "শূন্য"
    assert integer_words(24) == "চব্বিশ"
    assert integer_words(36) == "ছত্রিশ"
    assert integer_words(100) == "একশো"
    assert integer_words(2027) == "দুই হাজার সাতাশ"
    assert integer_words(150000) == "এক লাখ পঞ্চাশ হাজার"
    assert integer_words(10000000) == "এক কোটি"


def test_speak_numbers():
    assert speak_numbers("২৪ ঘণ্টা") == "চব্বিশ ঘণ্টা"
    assert speak_numbers("36 পয়েন্ট") == "ছত্রিশ পয়েন্ট"
    assert speak_numbers("৫০%") == "পঞ্চাশ শতাংশ"
    assert speak_numbers("৩.৫") == "তিন দশমিক পাঁচ"
    assert speak_numbers("১১:৪৫") == "এগারোটা পঁয়তাল্লিশ"
    assert speak_numbers("৳৫০০") == "পাঁচশো টাকা"
    assert speak_numbers("$50") == "পঞ্চাশ ডলার"
    assert speak_numbers("১,২৫০") == "এক হাজার দুইশো পঞ্চাশ"
    assert speak_numbers("৩–২") == "তিন-দুই"
    assert speak_numbers("০১৭১২") == "শূন্য এক সাত এক দুই"


def test_lexicon_matches_whole_words_only():
    lexicon = {"API": "এপিআই", "AI": "এআই"}
    assert apply_lexicon("API ও AI", lexicon) == "এপিআই ও এআই"
    assert apply_lexicon("RAPID", lexicon) == "RAPID"


def test_prepare_speech_combines_both():
    result = prepare_speech("ShopVerge-এ ২৪ ঘণ্টা", {"ShopVerge": "শপভার্জ"})
    assert result == "শপভার্জ-এ চব্বিশ ঘণ্টা"


def test_digits_in_voiceover_are_not_flagged(tmp_path):
    assert validate(base_config(tmp_path), [scene("২৪ ঘণ্টা সাপোর্ট।")]) == []


def test_unknown_english_word_warns(tmp_path):
    config = base_config(tmp_path, lexicon="")
    issues = validate(config, [scene("WordPress দিয়ে।")])
    assert [(issue.level, issue.scene) for issue in issues] == [("warning", 1)]