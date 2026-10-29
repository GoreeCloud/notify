"""Local-only search semantics over ntfy notifications."""
import pytest

from goreecloud_notify.core import Notification
from goreecloud_notify.filters import filter_notifications


@pytest.fixture
def messages():
    return [
        Notification("a", "infra", "Backup complete", "Storage", 3, 10, ("zfs", "success")),
        Notification("b", "infra", "Pool DEGRADED", "Storage alert", 5, 20, ("zfs", "urgent")),
        Notification("c", "office", "Network offline", "Router", 4, 30, ("network",)),
    ]


def test_search_is_case_insensitive_and_matches_tags(messages):
    assert [n.id for n in filter_notifications(messages, query="ZFS")] == ["a", "b"]


def test_all_words_required_across_fields(messages):
    assert [n.id for n in filter_notifications(messages, query="storage degraded")] == ["b"]
    assert filter_notifications(messages, query="storage impossible") == []


def test_priority_filters(messages):
    assert [n.id for n in filter_notifications(messages, min_priority=4)] == ["b", "c"]
    assert [n.id for n in filter_notifications(messages, min_priority=5)] == ["b"]
    assert [n.id for n in filter_notifications(messages, min_priority=1)] == ["a", "b", "c"]


def test_combined_filter_preserves_original_order(messages):
    result = filter_notifications(messages, query="storage", min_priority=4)
    assert [n.id for n in result] == ["b"]
    assert [n.id for n in messages] == ["a", "b", "c"]


def test_empty_query_matches_all(messages):
    assert filter_notifications(messages) == messages


def test_invalid_priority_fails_closed(messages):
    with pytest.raises(ValueError):
        filter_notifications(messages, min_priority=2)
