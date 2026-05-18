"""Output validation for the pattern synthesis.

Checks generated output for completeness, quality, and safety.
"""

import re

_REQUIRED_SECTIONS = {
    "identity": [
        "Who I Am",
        "Worldview",
        "Voice",
        "Operating Principles",
        "Response Patterns",
        "Boundaries",
        "Pet Peeves",
    ],
    "brand": [
        "Core Identity",
        "Voice Attributes",
        "Tone Spectrum",
        "Vocabulary",
    ],
    "design": [
        "Color Palette",
        "Typography",
        "Spacing",
        "Design Principles",
    ],
}

_PROMPT_LEAK_PATTERNS = [
    r"as an AI",
    r"I'm sorry",
    r"I cannot",
    r"Here is (?:the |a )?(?:SOUL|brand|design)",
    r"Generate a",
    r"You are a precise",
    r"```(?:markdown|json|)",
    r"Output (?:JSON|markdown)",
    r"Respond with ONLY",
]

_PII_PATTERNS = [
    r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b\d{16}\b",
]


def validate_output(output, lens="identity"):
    """Validate generated output for a given lens.

    Returns a dict with:
      - pass: bool — overall pass/fail
      - score: float — 0.0 to 1.0 quality score
      - issues: list[str] — blocking issues
      - warnings: list[str] — non-blocking warnings
    """
    if not output or not isinstance(output, str):
        return {"pass": False, "score": 0.0, "issues": ["Empty or invalid output"], "warnings": []}

    issues = []
    warnings = []
    score_parts = []

    # Length check
    if len(output) < 200:
        issues.append(f"Output too short ({len(output)} chars, minimum 200)")
        score_parts.append(0.0)
    elif len(output) < 500:
        warnings.append(f"Output short ({len(output)} chars)")
        score_parts.append(0.5)
    else:
        score_parts.append(1.0)

    # Section completeness
    required = _REQUIRED_SECTIONS.get(lens, [])
    found = sum(1 for s in required if s.lower() in output.lower())
    section_ratio = found / len(required) if required else 1.0
    score_parts.append(section_ratio)
    if found < len(required):
        missing = [s for s in required if s.lower() not in output.lower()]
        issues.append(f"Missing sections: {', '.join(missing)}")

    # Prompt leakage
    for pattern in _PROMPT_LEAK_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            issues.append(f"Prompt leakage detected: pattern '{pattern}'")
            score_parts.append(0.0)
            break
    else:
        score_parts.append(1.0)

    # PII check
    for pattern in _PII_PATTERNS:
        match = re.search(pattern, output)
        if match:
            warnings.append("Potential PII detected")
            score_parts.append(0.5)
            break
    else:
        score_parts.append(1.0)

    # Structural quality
    headers = re.findall(r'^#{1,3}\s+', output, re.MULTILINE)
    if len(headers) < 3:
        warnings.append(f"Few section headers ({len(headers)})")
        score_parts.append(0.5)
    else:
        score_parts.append(1.0)

    score = sum(score_parts) / len(score_parts) if score_parts else 0.0
    passed = len(issues) == 0 and score >= 0.5

    return {
        "pass": passed,
        "score": round(score, 3),
        "issues": issues,
        "warnings": warnings,
    }


def sanitize_output(output):
    """Remove prompt leakage artifacts from output."""
    sanitized = output
    for pattern in _PROMPT_LEAK_PATTERNS:
        lines = sanitized.split('\n')
        sanitized = '\n'.join(
            line for line in lines
            if not re.search(pattern, line, re.IGNORECASE)
        )
    sanitized = re.sub(r'```[\s\S]*?```', '', sanitized)
    return sanitized.strip()
