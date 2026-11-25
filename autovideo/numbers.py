import re

D = "0-9০-৯"
DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

DIGIT_WORDS = ["শূন্য", "এক", "দুই", "তিন", "চার", "পাঁচ", "ছয়", "সাত", "আট", "নয়"]

BELOW_100 = [
    "শূন্য", "এক", "দুই", "তিন", "চার", "পাঁচ", "ছয়", "সাত", "আট", "নয়",
    "দশ", "এগারো", "বারো", "তেরো", "চৌদ্দ", "পনেরো", "ষোলো", "সতেরো", "আঠারো", "উনিশ",
    "বিশ", "একুশ", "বাইশ", "তেইশ", "চব্বিশ", "পঁচিশ", "ছাব্বিশ", "সাতাশ", "আটাশ", "উনত্রিশ",
    "ত্রিশ", "একত্রিশ", "বত্রিশ", "তেত্রিশ", "চৌত্রিশ", "পঁয়ত্রিশ", "ছত্রিশ", "সাঁইত্রিশ", "আটত্রিশ", "উনচল্লিশ",
    "চল্লিশ", "একচল্লিশ", "বিয়াল্লিশ", "তেতাল্লিশ", "চুয়াল্লিশ", "পঁয়তাল্লিশ", "ছেচল্লিশ", "সাতচল্লিশ", "আটচল্লিশ", "উনপঞ্চাশ",
    "পঞ্চাশ", "একান্ন", "বাহান্ন", "তিপ্পান্ন", "চুয়ান্ন", "পঞ্চান্ন", "ছাপ্পান্ন", "সাতান্ন", "আটান্ন", "উনষাট",
    "ষাট", "একষট্টি", "বাষট্টি", "তেষট্টি", "চৌষট্টি", "পঁয়ষট্টি", "ছেষট্টি", "সাতষট্টি", "আটষট্টি", "উনসত্তর",
    "সত্তর", "একাত্তর", "বাহাত্তর", "তিয়াত্তর", "চুয়াত্তর", "পঁচাত্তর", "ছিয়াত্তর", "সাতাত্তর", "আটাত্তর", "উনআশি",
    "আশি", "একাশি", "বিরাশি", "তিরাশি", "চুরাশি", "পঁচাশি", "ছিয়াশি", "সাতাশি", "অষ্টাশি", "উননব্বই",
    "নব্বই", "একানব্বই", "বিরানব্বই", "তিরানব্বই", "চুরানব্বই", "পঁচানব্বই", "ছিয়ানব্বই", "সাতানব্বই", "আটানব্বই", "নিরানব্বই",
]

HUNDREDS = ["", "একশো", "দুইশো", "তিনশো", "চারশো", "পাঁচশো", "ছয়শো", "সাতশো", "আটশো", "নয়শো"]

TIME = re.compile(rf"(?<![{D}])([{D}]{{1,2}}):([{D}]{{2}})(?![{D}])")
RANGE = re.compile(rf"(?<=[{D}])\s*[–—]\s*(?=[{D}])")
NUMBER = re.compile(
    rf"([$৳])?([{D}]+(?:,[{D}]{{2,3}}(?![{D}]))*)(?:\.([{D}]+))?(%)?"
)


def integer_words(n):
    if n < 100:
        return BELOW_100[n]

    parts = []
    for size, name in ((10**7, "কোটি"), (10**5, "লাখ"), (1000, "হাজার")):
        if n >= size:
            parts.append(f"{integer_words(n // size)} {name}")
            n %= size
    if n >= 100:
        parts.append(HUNDREDS[n // 100])
        n %= 100
    if n:
        parts.append(BELOW_100[n])
    return " ".join(parts)


def digit_words(digits):
    return " ".join(DIGIT_WORDS[int(d)] for d in digits)


def _time(match):
    hour = int(match.group(1).translate(DIGIT_MAP))
    minute = int(match.group(2).translate(DIGIT_MAP))
    if hour > 24 or minute > 59:
        return match.group(0)
    words = f"{integer_words(hour)}টা"
    if minute:
        words += f" {integer_words(minute)}"
    return words


def _number(match):
    symbol, whole, fraction, percent = match.groups()
    digits = whole.replace(",", "").translate(DIGIT_MAP)

    if len(digits) > 12 or (len(digits) > 1 and digits.startswith("0")):
        words = digit_words(digits)
    else:
        words = integer_words(int(digits))

    if fraction:
        words += " দশমিক " + digit_words(fraction.translate(DIGIT_MAP))
    if percent:
        words += " শতাংশ"
    if symbol == "৳":
        words += " টাকা"
    elif symbol == "$":
        words += " ডলার"
    return words


def speak_numbers(text):
    text = RANGE.sub("-", text)
    text = TIME.sub(_time, text)
    return NUMBER.sub(_number, text)