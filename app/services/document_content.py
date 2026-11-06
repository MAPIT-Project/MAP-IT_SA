"""Reject PDF extraction debris before it becomes retrieval evidence."""

import re


def clean_document_text(content: str) -> str:
    """Remove control characters and long form separators, preserving numbers and tables."""
    content = "".join(char if char.isprintable() or char in "\n\t" else " " for char in content)
    return re.sub(r"[_=~]{6,}", " ", content).strip()


def is_usable_document_text(content: str) -> bool:
    """Page numbers, punctuation and separator lines cannot support a funding answer."""
    text = clean_document_text(content)
    letters = sum(char.isalpha() for char in text)
    words = re.findall(r"[^\W\d_]{2,}", text, re.UNICODE)
    return letters >= 24 and len(words) >= 4


def select_document_excerpt(content: str, query: str, max_chars: int = 1500) -> str:
    """Keep the part of a long chunk that covers the query, as a contiguous source quote."""
    if len(content) <= max_chars:
        return content
    stop_words = {"the", "and", "for", "from", "with", "what", "does", "about", "this", "that"}
    terms = {word for word in re.findall(r"\w+", query.casefold()) if len(word) > 2} - stop_words
    hits = [
        (match.start(), match.group().casefold())
        for match in re.finditer(r"\w+", content)
        if match.group().casefold() in terms
    ]
    starts = {0, *(max(0, position - max_chars // 4) for position, _ in hits)}

    def score(start):
        words = [word for position, word in hits if start <= position < start + max_chars]
        return len(set(words)), len(words), -start

    start = max(starts, key=score)
    if start:
        start = content.rfind(" ", 0, start) + 1
    end = min(len(content), start + max_chars)
    if end < len(content):
        boundary = content.rfind(" ", start, end)
        if boundary > start:
            end = boundary
    return content[start:end].strip()
