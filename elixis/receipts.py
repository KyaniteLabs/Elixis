"""Receipts feed: ingest the attention x activity ledger into a game seed.

The corpus format (one block per month):

    ## 2026-05 - watched 438 AI videos; built: claude-code(2144), hermes-agent(29)
    - Some Watched Video Title
    - Another Watched Video Title

ingest_corpus() parses this ledger and corpus_to_seed() shapes it into a
raw_input the GameEngine can consume without manual pasting: build ledgers
(the strongest identity signal) first, then deduplicated watched titles.
"""

import re
from typing import Dict, List, Optional

_MONTH_RE = re.compile(
    r"^##\s*(\d{4}-\d{2})\s*[—–-]\s*watched\s+(\d+)\s+\w+.*?built:\s*(.*)$"
)
_BUILT_ITEM_RE = re.compile(r"([A-Za-z0-9_.\-]+)\((\d+)\)")


def ingest_corpus(text: str) -> Dict:
    """Parse a corpus.md ledger into months, watched titles, and build ledgers.

    Returns {"months": [...], "watched_total": int, "built_total": int,
    "built_projects": {...}, "title_counts": {...}}. Each month carries
    {"month": "YYYY-MM", "watched": int, "built": {project: count}, "titles": [...]}.
    """
    months: List[Dict] = []
    current = None
    for line in text.splitlines():
        m = _MONTH_RE.match(line.strip())
        if m:
            current = {
                "month": m.group(1),
                "watched": int(m.group(2)),
                "built": {name: int(count) for name, count in _BUILT_ITEM_RE.findall(m.group(3))},
                "titles": [],
            }
            months.append(current)
            continue
        if current is not None and line.strip().startswith("- "):
            title = line.strip()[2:].strip()
            if title and title != "—":
                current["titles"].append(title)

    title_counts: Dict[str, int] = {}
    for month in months:
        for title in month["titles"]:
            title_counts[title] = title_counts.get(title, 0) + 1
    built_projects: Dict[str, int] = {}
    for month in months:
        for project, count in month["built"].items():
            built_projects[project] = built_projects.get(project, 0) + count

    return {
        "months": months,
        "months_count": len(months),
        "watched_total": sum(m["watched"] for m in months),
        "built_total": sum(built_projects.values()),
        "built_projects": built_projects,
        "title_counts": title_counts,
        "unique_titles": len(title_counts),
    }


def ingest_file(path: str) -> Dict:
    """Ingest a corpus file from disk."""
    with open(path) as f:
        return ingest_corpus(f.read())


def corpus_to_seed(text: str, max_chars: int = 4000, profile: Optional[str] = None) -> str:
    """Shape an ingested ledger into a game-ready raw_input seed.

    Order of signal: build ledgers (what was actually shipped), then watched
    titles deduplicated most-repeated-first. Kill-list discipline applies to
    nothing here (the corpus is evidence, not naming output), but em dashes
    in the source are neutralized so downstream discipline sees clean text.
    """
    data = ingest_corpus(text)
    lines: List[str] = []
    for month in data["months"]:
        if month["built"]:
            built = ", ".join(f"{p}({c})" for p, c in sorted(month["built"].items(), key=lambda x: -x[1]))
            lines.append(f"{month['month']} built: {built}")
    ranked = sorted(data["title_counts"].items(), key=lambda x: -x[1])
    for title, _count in ranked:
        cleaned = title.replace("—", "-").replace("–", "-").strip()
        if cleaned:
            lines.append(f"- {cleaned}")
    seed = "\n".join(lines)
    return seed[:max_chars]
