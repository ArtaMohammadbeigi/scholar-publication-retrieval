"""
Text preprocessing utilities for TF-IDF input.

Applies lowercasing, punctuation removal, stopword removal, and whitespace
normalization. Kept intentionally simple (no stemming/lemmatization) to
match project scope.
"""

import re
import string
import logging

import nltk
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)

# Ensure stopwords are available (downloads once, silent if already present).
try:
    STOPWORDS = set(stopwords.words("english"))
except LookupError:
    logger.info("NLTK stopwords not found locally. Downloading...")
    nltk.download("stopwords")
    STOPWORDS = set(stopwords.words("english"))


def to_lowercase(text: str) -> str:
    return text.lower()


def remove_punctuation(text: str) -> str:
    return text.translate(str.maketrans("", "", string.punctuation))


def remove_stopwords(text: str) -> str:
    words = text.split()
    filtered = [w for w in words if w not in STOPWORDS]
    return " ".join(filtered)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def preprocess_text(text: str) -> str:
    """
    Full preprocessing pipeline applied to any text before TF-IDF:
    lowercase -> remove punctuation -> remove stopwords -> normalize whitespace.
    """
    if not text:
        return ""
    text = to_lowercase(text)
    text = remove_punctuation(text)
    text = remove_stopwords(text)
    text = normalize_whitespace(text)
    return text
