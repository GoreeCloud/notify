"""Bounded, offline notification filtering; never transmits search terms."""
from __future__ import annotations

from collections.abc import Iterable

from .core import Notification


def filter_notifications(
    messages: Iterable[Notification],
    *,
    query: str = "",
    min_priority: int = 1,
) -> list[Notification]:
    """Return matching messages in original order.

    Query matching is case-insensitive, with all whitespace-separated words
    required somewhere in the title, message, topic, or tags.
    """
    if min_priority not in (1, 4, 5):
        raise ValueError("Unsupported minimum priority")
    terms = query.casefold().split()
    matches = []
    for note in messages:
        if note.priority < min_priority:
            continue
        haystack = " ".join((note.topic, note.title, note.message, *note.tags)).casefold()
        if all(term in haystack for term in terms):
            matches.append(note)
    return matches
