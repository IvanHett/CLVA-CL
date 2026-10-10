"""Text preprocessing: normalisation and tokenisation."""
import re

_APOSTROPHES = re.compile(r"['’`]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalise(text: str) -> str:
    """Lower-case, drop punctuation and collapse whitespace."""
    text = _APOSTROPHES.sub("", (text or "").lower())
    return _NON_ALNUM.sub(" ", text).strip()


def tokenise(text: str) -> list[str]:
    """Split raw text into normalised word tokens."""
    return normalise(text).split()


def stem(token: str) -> str:
    """Very light stemmer: strips a plural ending so 'deadlines' matches 'deadline'."""
    if token.endswith("sses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def stemmed(text: str) -> str:
    """Normalised text with every token stemmed, used for keyword matching."""
    return " ".join(stem(t) for t in tokenise(text))
