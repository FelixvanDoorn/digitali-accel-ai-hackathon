"""Cleans free-text instructions from the user before they go to the model.

This limits size and strips characters that can hide text or break our prompt structure. It does not make
prompt injection impossible; the real guardrails are that user text never enters the system prompt and
that the output must match the template's JSON schema.
"""

import re
import unicodedata

MAX_CHARS = 1000
TAG = "user_instructions"


class InvalidInstructions(ValueError):
    pass


def clean_instructions(text: str | None) -> str | None:
    """Returns cleaned instructions, or None if there is nothing left."""
    if text is None:
        return None

    # NFKC folds look-alike characters (full-width letters etc.) into plain ones.
    text = unicodedata.normalize("NFKC", text)
    # Drop control and invisible format characters (zero-width spaces, bidi overrides), keep newlines and tabs.
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch) not in {"Cc", "Cf", "Co", "Cs"})
    # The user must not be able to close or open our delimiter tag.
    text = re.sub(rf"</?\s*{TAG}\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text:
        return None
    if len(text) > MAX_CHARS:
        raise InvalidInstructions(f"Instructions are too long ({len(text)} characters, max {MAX_CHARS})")
    return text


def wrap(text: str) -> str:
    return f"<{TAG}>\n{text}\n</{TAG}>"
