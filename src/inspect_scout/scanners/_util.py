import re

from inspect_scout._scanner.result import Reference


def extract_references(explanation: str, message_id_map: list[str]) -> list[Reference]:
    """Extract message references from explanation text.

    Args:
        explanation: Explanation text containing [M{n}] style references
        message_id_map: List mapping 1-based indices to actual message IDs

    Returns:
        List of Reference objects with type="message"
    """
    # Find all [M{number}] patterns in the explanation
    pattern = r"\[M(\d+)\]"
    matches = re.finditer(pattern, explanation)

    references = []
    seen_ids = set()

    for match in matches:
        local_id = int(match.group(1))
        # Convert 1-based local ID to 0-based index
        idx = local_id - 1

        # Validate index is within bounds
        if 0 <= idx < len(message_id_map):
            actual_id = message_id_map[idx]
            # Avoid duplicate references
            if actual_id not in seen_ids:
                references.append(Reference(type="message", id=actual_id))
                seen_ids.add(actual_id)

    return references
