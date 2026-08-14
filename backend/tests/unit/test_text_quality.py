"""Text-quality helpers — garbage text-layer detection signals."""

import pytest

from src.utils.text_quality import JUNK_RATIO_BAD, junk_ratio


def test_clean_prose_is_below_threshold():
    text = "Hello, world! This is a normal page of English prose."
    assert junk_ratio(text) < JUNK_RATIO_BAD


def test_garbage_ocr_is_above_threshold():
    # The actual CHOUKAI failure signature: kanji misread as symbol-heavy
    # Latin gibberish.
    text = "tf=fv7r- E6=EfrWt=ilfiffi +filr)*D' t'J' iEEffifE' EfiA'H7"
    assert junk_ratio(text) >= JUNK_RATIO_BAD


def test_cjk_prose_with_fullwidth_punctuation_is_clean():
    # Full-width CJK punctuation (。、「」) must never count as noise.
    text = "「天気がいいから、散歩しましょう。」 これは普通の日本語です。"
    assert junk_ratio(text) == 0.0


def test_empty_and_whitespace_only_text_is_zero():
    assert junk_ratio("") == 0.0
    assert junk_ratio("   \n\t  ") == 0.0


def test_apostrophes_in_english_prose_are_not_noise():
    # Contractions are normal prose; a page of them must stay below the gate.
    text = " ".join(["don't can't won't it's we're they'll"] * 10)
    assert junk_ratio(text) < JUNK_RATIO_BAD


@pytest.mark.parametrize(
    "text",
    [
        "a=b",  # = is a strong noise symbol
        "x|y|z",  # pipes
        "foo_bar_2",  # underscores
        "1*2*3",  # asterisks
    ],
)
def test_noise_symbols_pushed_ratio_up(text):
    assert junk_ratio(text) > 0.1
