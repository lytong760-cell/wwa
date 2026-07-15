"""English-Vietnamese vocabulary module for the chatbot.

This module stores bilingual word pairs and provides helper functions for
translation and random vocabulary examples.
"""

import random

VOCABULARY = {
    "hello": "xin chào",
    "goodbye": "tạm biệt",
    "thank you": "cảm ơn",
    "please": "làm ơn",
    "yes": "vâng",
    "no": "không",
    "sorry": "xin lỗi",
    "love": "yêu",
    "friend": "bạn bè",
    "food": "thức ăn",
    "water": "nước",
    "happy": "vui vẻ",
    "sad": "buồn",
    "computer": "máy tính",
    "school": "trường học",
    "book": "quyển sách",
    "family": "gia đình",
    "work": "công việc",
    "city": "thành phố",
    "home": "nhà",
}

REVERSE_VOCABULARY = {viet: eng for eng, viet in VOCABULARY.items()}


def translate(term):
    """Translate a word or phrase in either direction."""
    normalized = term.strip().lower()
    if normalized in VOCABULARY:
        return f"{normalized} = {VOCABULARY[normalized]}"
    if normalized in REVERSE_VOCABULARY:
        return f"{normalized} = {REVERSE_VOCABULARY[normalized]}"
    return None


def random_word_pair():
    """Return a random English-Vietnamese word pair."""
    eng, viet = random.choice(list(VOCABULARY.items()))
    return eng, viet


def all_pairs():
    """Return all vocab pairs as a list of tuples."""
    return list(VOCABULARY.items())
