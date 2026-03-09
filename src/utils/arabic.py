"""Arabic text normalization for search."""

import re


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text by removing diacritics and normalizing letter forms.

    1. Remove diacritics (harakat): fathah, dammah, kasrah, shadda, sukun, etc.
    2. Remove Quranic orthographic marks (small waw, small meem, rounded zero, etc.)
    3. Remove tatweel (kashida)
    4. Normalize alef forms: أ إ آ ٱ → ا
    5. Normalize yaa forms: ى → ي
    6. Remove hamza combining marks (above/below)
    """
    # Core diacritics: harakat, tanwin, shadda, sukun, superscript alef
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Maddah above, hamza above/below
    text = re.sub(r'[\u0653-\u0655]', '', text)
    # Tatweel
    text = text.replace('\u0640', '')
    # Quranic annotation marks (U+06D6-U+06ED)
    text = re.sub(r'[\u06D6-\u06ED]', '', text)
    # Normalize alef forms
    text = re.sub(r'[أإآٱ]', 'ا', text)
    # Normalize yaa
    text = text.replace('ى', 'ي')
    return text.strip()
