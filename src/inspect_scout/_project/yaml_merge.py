"""Comment-preserving YAML merge utilities for project configuration."""

import logging
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

logger = logging.getLogger(__name__)

# Maps list field names to the key used for matching items.
# None means match by value (for string lists like filter/tags).
LIST_MATCH_KEYS: dict[str, str | None] = {
    "filter": None,  # Match by string value
    "tags": None,  # Match by string value
    "worklist": "scanner",  # Match by scanner field
    "scanners": "name",  # Match by name field (when scanners is a list)
}


def apply_config_update(
    original: CommentedMap,
    updates: dict[str, Any],
    path: str = "",
) -> None:
    """Recursively update original CommentedMap with new values.

    Preserves comments on unchanged structure by updating in place rather
    than replacing objects.

    Args:
        original: The ruamel.yaml CommentedMap to update in place.
        updates: Plain dict with new values.
        path: Current path for determining list matching strategy.
    """
    # Handle keys in updates
    for key, new_value in updates.items():
        current_path = f"{path}.{key}" if path else key
        field_name = key  # The immediate field name for list matching

        if new_value is None or new_value == [] or new_value == {}:
            # None/empty means "unset" - remove the key if it exists
            if key in original:
                del original[key]
        elif key not in original:
            # New key - just add it
            original[key] = new_value
        elif isinstance(original[key], CommentedMap) and isinstance(new_value, dict):
            # Recursively update nested dict
            apply_config_update(original[key], new_value, current_path)
        elif isinstance(original[key], CommentedSeq) and isinstance(new_value, list):
            # Update list with comment preservation
            _update_list(original[key], new_value, field_name)
        elif isinstance(original[key], list) and isinstance(new_value, list):
            # Plain list (no comments) - just replace
            original[key] = new_value
        elif isinstance(original[key], dict) and isinstance(new_value, dict):
            # Plain dict - convert to recursive update if possible
            if isinstance(original[key], CommentedMap):
                apply_config_update(original[key], new_value, current_path)
            else:
                original[key] = new_value
        else:
            # Scalar or type change - just replace
            original[key] = new_value

    # Remove keys not in updates
    keys_to_remove = [key for key in original if key not in updates]
    for key in keys_to_remove:
        del original[key]


def _update_list(
    original: CommentedSeq,
    updates: list[Any],
    field_name: str,
) -> None:
    """Update a CommentedSeq in place, preserving comments where possible.

    Args:
        original: The ruamel.yaml CommentedSeq to update in place.
        updates: Plain list with new values.
        field_name: Field name to determine matching strategy.
    """
    match_key = LIST_MATCH_KEYS.get(field_name)

    if match_key is None:
        # Check if this is an object list without a configured match key
        if updates and isinstance(updates[0], dict):
            logger.warning(
                "List field '%s' contains objects but has no match key configured "
                "in LIST_MATCH_KEYS. Comments on list items may not be preserved. "
                "Consider adding an entry to LIST_MATCH_KEYS.",
                field_name,
            )
        # Match by value (for string lists)
        _update_list_by_value(original, updates)
    else:
        # Match by object key field
        _update_list_by_key(original, updates, match_key)


def _update_list_by_value(original: CommentedSeq, updates: list[Any]) -> None:
    """Update list matching items by their value.

    Used for string lists like filter and tags.
    """
    # Build index of original items by value
    original_by_value: dict[Any, int] = {}
    for i, item in enumerate(original):
        # Use the item itself as key (works for strings, numbers, etc.)
        if item not in original_by_value:
            original_by_value[item] = i

    # Track which original indices are still used
    used_indices: set[int] = set()
    result_items: list[tuple[Any, int | None]] = []  # (value, original_index)

    for new_item in updates:
        if new_item in original_by_value:
            orig_idx = original_by_value[new_item]
            if orig_idx not in used_indices:
                # Reuse original item (preserves any attached comments)
                result_items.append((original[orig_idx], orig_idx))
                used_indices.add(orig_idx)
            else:
                # Duplicate in new list - add as new
                result_items.append((new_item, None))
        else:
            # New item
            result_items.append((new_item, None))

    # Rebuild the list preserving comments
    _rebuild_list(original, result_items)


def _update_list_by_key(
    original: CommentedSeq, updates: list[Any], match_key: str
) -> None:
    """Update list matching items by a key field.

    Used for object lists like worklist and scanners.
    """
    # Build index of original items by key field value
    original_by_key: dict[Any, int] = {}
    for i, item in enumerate(original):
        if isinstance(item, dict) and match_key in item:
            key_value = item[match_key]
            if key_value not in original_by_key:
                original_by_key[key_value] = i

    # Track which original indices are still used
    used_indices: set[int] = set()
    result_items: list[tuple[Any, int | None]] = []  # (value, original_index)

    for new_item in updates:
        if isinstance(new_item, dict) and match_key in new_item:
            key_value = new_item[match_key]
            if key_value in original_by_key:
                orig_idx = original_by_key[key_value]
                if orig_idx not in used_indices:
                    # Update existing item in place
                    orig_item = original[orig_idx]
                    if isinstance(orig_item, CommentedMap):
                        apply_config_update(orig_item, new_item)
                        result_items.append((orig_item, orig_idx))
                    else:
                        result_items.append((new_item, None))
                    used_indices.add(orig_idx)
                else:
                    # Duplicate key in new list - add as new
                    result_items.append((new_item, None))
            else:
                # New item
                result_items.append((new_item, None))
        else:
            # Item without key field - add as new
            result_items.append((new_item, None))

    # Rebuild the list preserving comments
    _rebuild_list(original, result_items)


def _rebuild_list(
    original: CommentedSeq, result_items: list[tuple[Any, int | None]]
) -> None:
    """Rebuild a CommentedSeq from result items, preserving comments.

    Args:
        original: The CommentedSeq to rebuild.
        result_items: List of (value, original_index) tuples.
    """
    # Save comments from original positions
    # ruamel.yaml stores comments in a special ca (Comment Attribute) object
    original_comments = {}
    if hasattr(original, "ca") and original.ca.items:
        for idx, comment in original.ca.items.items():
            original_comments[idx] = comment

    # Clear and rebuild
    original.clear()

    for new_idx, (value, orig_idx) in enumerate(result_items):
        original.append(value)
        # Restore comment if this item came from an original position
        if orig_idx is not None and orig_idx in original_comments:
            if not hasattr(original, "ca"):
                continue
            original.ca.items[new_idx] = original_comments[orig_idx]
