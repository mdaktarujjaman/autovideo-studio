from .lexicon import apply_lexicon
from .numbers import speak_numbers


def prepare_speech(text, lexicon):
    return speak_numbers(apply_lexicon(text, lexicon))