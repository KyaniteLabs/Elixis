"""Input validation and sanitization for SoulCraft.

Provides validators for brain dump inputs, API requests, and entity data.
"""

import re
import html
from typing import Dict, List, Tuple, Optional


# Maximum allowed input sizes
MAX_BRAIN_DUMP_LENGTH = 50000  # 50KB
MAX_ENTITY_NAME_LENGTH = 200
MAX_THEME_COUNT = 10
MAX_TRAIT_COUNT = 10

# Patterns for detecting problematic content
POTENTIAL_PROMPT_INJECTION = [
    r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|directives)",
    r"system\s*:\s*you\s+are\s+now",
    r"\{\{\s*SYSTEM\s*\}\}",
    r"<\s*system\s*>",
    r"user\s*:\s*ignore",
    r"disregard\s+(?:all|previous)",
]

SUSPICIOUS_PATTERNS = re.compile(
    "|".join(POTENTIAL_PROMPT_INJECTION),
    re.IGNORECASE | re.MULTILINE
)


def sanitize_text(text: str, max_length: int = MAX_BRAIN_DUMP_LENGTH) -> str:
    """Sanitize input text.

    Args:
        text: Raw input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Convert to string if needed
    text = str(text)

    # Remove null bytes
    text = text.replace("\x00", "")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip leading/trailing whitespace
    text = text.strip()

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "\n[truncated]"

    return text


def validate_brain_dump(text: str) -> Tuple[bool, Optional[str], Dict]:
    """Validate brain dump input.

    Args:
        text: Raw brain dump text

    Returns:
        Tuple of (is_valid, error_message, metadata)
    """
    metadata = {
        "original_length": len(text) if text else 0,
        "sanitized_length": 0,
        "warnings": [],
    }

    # Check for empty input
    if not text or not text.strip():
        return False, "Brain dump is empty", metadata

    # Check length
    if len(text) > MAX_BRAIN_DUMP_LENGTH:
        return (
            False,
            f"Input too long. Maximum {MAX_BRAIN_DUMP_LENGTH} characters allowed.",
            metadata
        )

    # Check for potential prompt injection
    if SUSPICIOUS_PATTERNS.search(text):
        metadata["warnings"].append("Potential prompt injection detected")
        # Sanitize but don't block - just flag
        text = SUSPICIOUS_PATTERNS.sub("[filtered]", text)

    # Sanitize
    sanitized = sanitize_text(text)
    metadata["sanitized_length"] = len(sanitized)

    # Check minimum meaningful content
    word_count = len(sanitized.split())
    if word_count < 2:
        return (
            False,
            "Input too short. Please provide at least a few words.",
            metadata
        )

    metadata["word_count"] = word_count

    return True, None, metadata


def validate_entity(entity: Dict) -> Tuple[bool, List[str]]:
    """Validate extracted entity structure.

    Args:
        entity: Entity dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if "canonical" not in entity:
        errors.append("Missing 'canonical' field")
        return False, errors

    name = entity.get("canonical", "")

    # Validate name
    if not name:
        errors.append("Entity name is empty")
    elif len(name) > MAX_ENTITY_NAME_LENGTH:
        errors.append(f"Entity name too long (max {MAX_ENTITY_NAME_LENGTH})")
    elif len(name) < 2:
        errors.append("Entity name too short")

    # Sanitize name
    if name:
        # Remove control characters
        name = "".join(c for c in name if ord(c) >= 32 or c == '\n')
        # Escape HTML
        name = html.escape(name)
        entity["canonical"] = name.strip()

    # Validate themes
    themes = entity.get("themes", [])
    if len(themes) > MAX_THEME_COUNT:
        entity["themes"] = themes[:MAX_THEME_COUNT]
        errors.append(f"Themes truncated to {MAX_THEME_COUNT}")

    # Validate traits
    traits = entity.get("traits", [])
    if len(traits) > MAX_TRAIT_COUNT:
        entity["traits"] = traits[:MAX_TRAIT_COUNT]
        errors.append(f"Traits truncated to {MAX_TRAIT_COUNT}")

    return len(errors) == 0, errors


def sanitize_entity(entity: Dict) -> Dict:
    """Sanitize all fields in an entity.

    Args:
        entity: Entity dictionary

    Returns:
        Sanitized entity
    """
    sanitized = {}

    for key, value in entity.items():
        if isinstance(value, str):
            # Sanitize strings
            sanitized[key] = sanitize_text(value, max_length=1000)
        elif isinstance(value, list):
            # Sanitize list items
            sanitized[key] = [
                sanitize_text(item, max_length=200) if isinstance(item, str) else item
                for item in value[:20]  # Limit list size
            ]
        else:
            sanitized[key] = value

    return sanitized


def validate_api_request(data: Dict, endpoint: str) -> Tuple[bool, Optional[str]]:
    """Validate API request payload.

    Args:
        data: Request body
        endpoint: API endpoint path

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Invalid request format"

    if endpoint == "/api/extract":
        # Validate extraction request
        brain_dump = data.get("brain_dump", "")
        is_valid, error, _ = validate_brain_dump(brain_dump)
        if not is_valid:
            return False, error

        # Validate options
        stream = data.get("stream", False)
        if not isinstance(stream, bool):
            return False, "Invalid 'stream' parameter"

    return True, None


def get_content_security_policy() -> str:
    """Get Content Security Policy header value."""
    return (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
