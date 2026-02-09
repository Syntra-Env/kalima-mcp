"""Arabic text normalization for search."""

import re


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text by removing diacritics and normalizing letter forms.

    1. Remove diacritics (harakat): fathah, dammah, kasrah, shadda, sukun, etc.
    2. Normalize alef forms: أ إ آ ٱ → ا
    3. Normalize yaa forms: ى → ي
    """
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = text.replace('ى', 'ي')
    return text.strip()
