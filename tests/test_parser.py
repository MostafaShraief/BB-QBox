"""Unit tests for core/parser.py"""
import json
import os
import tempfile
import pytest
from core.parser import QuestionParser


@pytest.fixture
def parser():
    return QuestionParser()


@pytest.fixture
def arabic_txt(tmp_path):
    content = """\
1. ما هو لون السماء؟
أ) أحمر
ب) أزرق
ج) أخضر
الجواب: ب
2. ما عاصمة مصر؟
أ) الإسكندرية
ب) الأقصر
ج) القاهرة
الجواب: ج ملاحظة: مدينة تاريخية
"""
    p = tmp_path / "arabic.txt"
    p.write_text(content, encoding="utf-8")
    return str(p)


@pytest.fixture
def english_txt(tmp_path):
    content = """\
1. What color is the sky?
a) red
b) blue
c) green
answer: b
2. What is 2+2?
a) 3
b) 4
c) 5
answer: b hint: basic math
"""
    p = tmp_path / "english.txt"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_parse_arabic(parser, arabic_txt):
    banks = parser.parse_text(arabic_txt)
    assert len(banks) == 1
    suffix, questions = banks[0]
    assert len(questions) == 2
    q1 = questions[0]
    assert "أ)" in q1["options"] or len(q1["options"]) > 0


def test_parse_english(parser, english_txt):
    banks = parser.parse_text(english_txt)
    assert len(banks) == 1
    _, questions = banks[0]
    assert len(questions) == 2
    # Second question has explanation (hint)
    assert questions[1]["explanation"] != ""


def test_file_not_found(parser):
    with pytest.raises(FileNotFoundError):
        parser.parse_text("/nonexistent/path/file.txt")


def test_split_lectures(tmp_path, parser):
    content = """\
1. Q1?
a) A
b) B
answer: a
2. Q2?
a) A
b) B
answer: b
1. Q3 (lecture 2)?
a) A
b) B
answer: a
"""
    p = tmp_path / "multi.txt"
    p.write_text(content, encoding="utf-8")
    banks = parser.parse_text(str(p), split_lectures=True)
    # Should be split into 2 banks
    assert len(banks) == 2


def test_map_char_to_index_english(parser):
    assert parser._map_char_to_index('a') == 0
    assert parser._map_char_to_index('b') == 1
    assert parser._map_char_to_index('A') == 0


def test_save_banks(tmp_path, parser, english_txt):
    banks = parser.parse_text(english_txt)
    # Patch the "banks" base path by using tmp_path
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        results = parser.save_banks(banks, "test_bank")
        assert len(results) == 1
        bank_path = results[0]
        assert os.path.exists(os.path.join(bank_path, "bank.json"))
        with open(os.path.join(bank_path, "bank.json"), 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) == 2
    finally:
        os.chdir(original_cwd)
