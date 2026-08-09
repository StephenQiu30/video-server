from __future__ import annotations

import unicodedata


def normalize_username(value: str) -> tuple[str, str]:
    display = unicodedata.normalize("NFKC", value).strip()
    if not 2 <= len(display) <= 32:
        raise ValueError("username must contain between 2 and 32 characters")
    if not all(character.isalnum() or character in "_-." for character in display):
        raise ValueError("username contains unsupported characters")
    return display, display.casefold()
