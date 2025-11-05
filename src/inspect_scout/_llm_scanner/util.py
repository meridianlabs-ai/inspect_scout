import re

from inspect_scout._scanner.result import Reference


def extract_references(
    explanation: str, message_id_map: dict[str, str]
) -> list[Reference]:
    """Extract message references from explanation text.

    Args:
        explanation: Explanation text containing [M{n}] style references
        message_id_map: Dict mapping ordinal IDs (e.g., "M1", "M2") to actual message IDs

    Returns:
        List of Reference objects with type="message"
    """
    # Find all [M{number}] patterns in the explanation
    pattern = r"\[M\d+\]"
    matches = re.finditer(pattern, explanation)

    references = []
    seen_ids = set()

    for match in matches:
        cite = match.group(0)
        # Extract ordinal key (e.g., "M1" from "[M1]")
        ordinal_key = cite[1:-1]

        # Look up actual message ID
        if ordinal_key in message_id_map:
            actual_id = message_id_map[ordinal_key]
            # Avoid duplicate references
            if actual_id not in seen_ids:
                references.append(Reference(type="message", cite=cite, id=actual_id))
                seen_ids.add(actual_id)

    return references
