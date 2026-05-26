"""Source Corpus ingestion for GitHub repositories and local folders.

The ingestion layer is intentionally read-only. It extracts quality-improving
signals for Elixis synthesis without executing project code.
"""

from __future__ import annotations

import ast
import base64
import json
import mimetypes
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MAX_SIGNALS = 80
MAX_TEXT_BYTES = 80_000
MAX_SIGNAL_TEXT = 4_000
MAX_LOCAL_FILES = 2_000
USER_AGENT = "Elixis/1.0 SourceCorpus"
RUNS_DIR = Path(".elixis") / "ingestion-runs"

TEXT_EXTENSIONS = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".html",
}

PRIMARY_DOC_NAMES = {
    "readme",
    "index",
    "overview",
    "introduction",
    "quickstart",
    "getting-started",
    "docs",
    "features",
    "architecture",
    "design",
    "brand",
    "marketing",
    "about",
    "llms",
}

METADATA_FILES = {
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "go.mod",
    "composer.json",
    "Gemfile",
    "Dockerfile",
    "docker-compose.yml",
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "archive",
    "coverage",
    ".next",
    ".nuxt",
    ".turbo",
}

GENERATED_OR_NOISY = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "Gemfile.lock",
}

SENSITIVE_NAME_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in (
        r"(^|/)\.env($|[./_-])",
        r"(^|/)\.npmrc$",
        r"(^|/)\.pypirc$",
        r"(^|/)id_rsa($|\.)",
        r"(^|/)id_ed25519($|\.)",
        r"private[_-]?key",
        r"secret",
        r"credential",
        r"token",
        r"password",
        r"\.pem$",
        r"\.key$",
    )
]

SENSITIVE_CONTENT_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"gh[pousr]_[A-Za-z0-9_]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"sk-[A-Za-z0-9_-]{20,}",
        r"tskey-[A-Za-z0-9_-]+",
        r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}",
    )
]


@dataclass
class CandidateSignal:
    kind: str
    title: str
    text: str
    path: str | None = None
    url: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    metadata: dict[str, Any] | None = None


def ingest_source(
    *,
    github: str | None = None,
    path: str | None = None,
    include_code: bool = False,
    include_issues: bool = False,
    include_prs: bool = False,
    include_commits: bool = False,
    include_hidden: bool = False,
    include_large_files: bool = False,
    include_visual_analysis: bool = False,
    artifacts: list[str] | None = None,
    max_signals: int = DEFAULT_MAX_SIGNALS,
) -> dict[str, Any]:
    """Build a quality-focused Ingestion Result from a GitHub URL or folder."""
    started = time.time()
    if bool(github) == bool(path):
        raise ValueError("Provide exactly one Source Target: github or path")
    if max_signals < 1 or max_signals > 500:
        raise ValueError("max_signals must be between 1 and 500")

    rejected: list[dict[str, Any]] = []
    if github:
        target = _github_target(github)
        candidates = _github_candidates(
            target,
            include_code=include_code,
            include_issues=include_issues,
            include_prs=include_prs,
            include_commits=include_commits,
            include_large_files=include_large_files,
            rejected=rejected,
        )
    else:
        target = _local_target(path or "")
        candidates = _local_candidates(
            Path(path or ""),
            include_code=include_code,
            include_hidden=include_hidden,
            include_large_files=include_large_files,
            include_visual_analysis=include_visual_analysis,
            rejected=rejected,
        )

    included, score_summary = _score_and_select(candidates, max_signals=max_signals, rejected=rejected)
    corpus_text = corpus_to_brain_dump(included)
    run_id = uuid.uuid4().hex[:12]
    duration_ms = int((time.time() - started) * 1000)
    artifact_tiers = _normalize_artifacts(artifacts or [])
    result = {
        "run_id": run_id,
        "source_target": target,
        "source_corpus": {
            "signals": included,
            "signal_count": len(included),
            "corpus_text": corpus_text,
        },
        "rejected_signals": _summarize_rejections(rejected),
        "signal_value_summary": score_summary,
        "artifact_tiers": artifact_tiers,
        "process_trace": {
            "visibility": (
                "Source Corpus trace. Values from Sensitive Candidates are never exposed; "
                "only rejection categories and paths are reported."
            ),
            "phases": [
                {"name": "discover", "candidate_count": len(candidates), "duration_ms": duration_ms},
                {"name": "score", "included_count": len(included), "rejected_count": len(rejected)},
            ],
            "include_options": {
                "include_code": include_code,
                "include_issues": include_issues,
                "include_prs": include_prs,
                "include_commits": include_commits,
                "include_hidden": include_hidden,
                "include_large_files": include_large_files,
                "include_visual_analysis": include_visual_analysis,
            },
            "max_signals": max_signals,
            "duration_ms": duration_ms,
        },
    }
    _persist_ingestion_result(result)
    return result


def load_ingestion_result(run_id: str) -> dict[str, Any]:
    """Load a persisted Ingestion Result by run ID."""
    if not re.match(r"^[a-f0-9]{12}$", run_id):
        raise ValueError("Invalid ingestion run ID")
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        raise ValueError(f"Ingestion run not found: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _persist_ingestion_result(result: dict[str, Any]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = result.get("run_id")
    if not run_id:
        return
    path = RUNS_DIR / f"{run_id}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def corpus_to_brain_dump(signals: list[dict[str, Any]]) -> str:
    """Convert included Corpus Signals into compact text for existing synthesis."""
    parts: list[str] = []
    for signal in signals:
        title = signal.get("title") or signal.get("path") or signal.get("kind")
        text = (signal.get("text") or "").strip()
        if not text:
            continue
        parts.append(f"{title}\n{text[:MAX_SIGNAL_TEXT]}")
    return "\n\n---\n\n".join(parts)


def _normalize_artifacts(artifacts: list[str] | str) -> list[str]:
    allowed = {"json", "markdown", "html", "css", "market-page"}
    if isinstance(artifacts, str):
        artifacts = [artifacts]
    normalized = []
    for artifact in artifacts:
        item = str(artifact).strip().lower()
        if item and item in allowed and item not in normalized:
            normalized.append(item)
    return normalized


def _github_target(url: str) -> dict[str, Any]:
    owner, repo = _parse_github_url(url)
    meta = _github_json(f"https://api.github.com/repos/{owner}/{repo}")
    topics = []
    languages = {}
    tags = []
    releases = []
    try:
        topics = _github_json(f"https://api.github.com/repos/{owner}/{repo}/topics").get("names", [])
    except Exception:
        topics = meta.get("topics", [])
    try:
        languages = _github_json(f"https://api.github.com/repos/{owner}/{repo}/languages")
    except Exception:
        languages = {}
    try:
        tags = _github_json(f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=10")
    except Exception:
        tags = []
    try:
        releases = _github_json(f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=5")
    except Exception:
        releases = []
    return {
        "type": "github",
        "url": url,
        "owner": owner,
        "repo": repo,
        "default_branch": meta.get("default_branch", "main"),
        "metadata": {
            "name": meta.get("name"),
            "full_name": meta.get("full_name"),
            "description": meta.get("description"),
            "homepage": meta.get("homepage"),
            "topics": topics,
            "languages": languages,
            "license": (meta.get("license") or {}).get("spdx_id"),
            "stars": meta.get("stargazers_count"),
            "forks": meta.get("forks_count"),
            "tags": [tag.get("name") for tag in tags[:10] if isinstance(tag, dict)],
            "releases": [rel.get("name") or rel.get("tag_name") for rel in releases[:5] if isinstance(rel, dict)],
        },
    }


def _github_candidates(
    target: dict[str, Any],
    *,
    include_code: bool,
    include_issues: bool,
    include_prs: bool,
    include_commits: bool,
    include_large_files: bool,
    rejected: list[dict[str, Any]],
) -> list[CandidateSignal]:
    owner = target["owner"]
    repo = target["repo"]
    branch = target.get("default_branch") or "main"
    base = f"https://api.github.com/repos/{owner}/{repo}"
    candidates = [
        CandidateSignal(
            kind="repository_metadata",
            title=f"{owner}/{repo} metadata",
            text=json.dumps(target.get("metadata", {}), indent=2, ensure_ascii=False),
            url=target.get("url"),
            metadata={"authority": "repository"},
        )
    ]

    try:
        readme = _github_json(f"{base}/readme")
        text = base64.b64decode(readme.get("content", "")).decode("utf-8", errors="replace")
        candidates.append(CandidateSignal(
            kind="documentation",
            title="README",
            text=text,
            path=readme.get("path", "README.md"),
            url=readme.get("html_url"),
            metadata={"authority": "readme"},
        ))
    except Exception as exc:
        rejected.append(_reject("README", "unavailable", str(exc)))

    try:
        tree = _github_json(f"{base}/git/trees/{branch}?recursive=1").get("tree", [])
    except Exception as exc:
        rejected.append(_reject("git tree", "unavailable", str(exc)))
        tree = []

    tree_lines = []
    selected_files = []
    for item in tree:
        item_path = item.get("path", "")
        if not item_path:
            continue
        if _is_sensitive_path(item_path):
            rejected.append(_reject(item_path, "sensitive_path", "path resembles secret material"))
            continue
        if item.get("type") == "tree":
            continue
        tree_lines.append(item_path)
        if _select_path_for_content(item_path, include_code=include_code):
            selected_files.append(item)

    if tree_lines:
        candidates.append(CandidateSignal(
            kind="code_evidence",
            title="Repository structure",
            text="\n".join(tree_lines[:500]),
            path="/",
            url=target.get("url"),
            metadata={"authority": "tree"},
        ))

    for item in selected_files[:80]:
        item_path = item.get("path", "")
        size = int(item.get("size") or 0)
        if size > MAX_TEXT_BYTES and not include_large_files:
            rejected.append(_reject(item_path, "large_file", f"{size} bytes"))
            continue
        try:
            blob = _github_json(item.get("url", ""))
            raw = base64.b64decode(blob.get("content", ""))
            text = raw[:MAX_TEXT_BYTES].decode("utf-8", errors="replace")
        except Exception as exc:
            rejected.append(_reject(item_path, "unavailable", str(exc)))
            continue
        if _contains_secret(text):
            rejected.append(_reject(item_path, "sensitive_content", "secret-like content detected"))
            continue
        candidates.append(_signal_from_text_path(item_path, text, url=f"https://github.com/{owner}/{repo}/blob/{branch}/{item_path}"))

    if include_issues:
        candidates.extend(_github_issue_candidates(base, "issues", rejected))
    if include_prs:
        candidates.extend(_github_issue_candidates(base, "pulls", rejected))
    if include_commits:
        candidates.extend(_github_commit_candidates(base, rejected))
    return candidates


def _local_target(path: str) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Local Source Target is not a directory: {path}")
    return {"type": "local", "path": str(root), "name": root.name}


def _local_candidates(
    root: Path,
    *,
    include_code: bool,
    include_hidden: bool,
    include_large_files: bool,
    include_visual_analysis: bool,
    rejected: list[dict[str, Any]],
) -> list[CandidateSignal]:
    root = root.expanduser().resolve()
    candidates: list[CandidateSignal] = []
    tree_lines: list[str] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and (include_hidden or not d.startswith("."))
        ]
        for filename in filenames:
            scanned += 1
            if scanned > MAX_LOCAL_FILES:
                rejected.append(_reject(str(rel_dir), "budget_exhausted", f"stopped after {MAX_LOCAL_FILES} files"))
                break
            if not include_hidden and filename.startswith("."):
                rejected.append(_reject(str(rel_dir / filename), "hidden_file", "hidden files are opt-in"))
                continue
            rel_path = str((rel_dir / filename).as_posix()) if str(rel_dir) != "." else filename
            if _is_sensitive_path(rel_path):
                rejected.append(_reject(rel_path, "sensitive_path", "path resembles secret material"))
                continue
            full = root / rel_path
            if not full.is_file():
                continue
            tree_lines.append(rel_path)
            if _is_media_path(rel_path):
                candidates.append(_media_signal(full, rel_path, include_visual_analysis=include_visual_analysis))
                continue
            if not _select_path_for_content(rel_path, include_code=include_code):
                continue
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size > MAX_TEXT_BYTES and not include_large_files:
                rejected.append(_reject(rel_path, "large_file", f"{size} bytes"))
                continue
            try:
                text = full.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT_BYTES]
            except OSError as exc:
                rejected.append(_reject(rel_path, "unavailable", str(exc)))
                continue
            if _contains_secret(text):
                rejected.append(_reject(rel_path, "sensitive_content", "secret-like content detected"))
                continue
            candidates.append(_signal_from_text_path(rel_path, text))

    if tree_lines:
        candidates.append(CandidateSignal(
            kind="code_evidence",
            title="Local project structure",
            text="\n".join(tree_lines[:500]),
            path="/",
            metadata={"authority": "tree"},
        ))
    return candidates


def _signal_from_text_path(path: str, text: str, url: str | None = None) -> CandidateSignal:
    lower = path.lower()
    basename = os.path.basename(lower)
    stem = os.path.splitext(basename)[0]
    if basename in METADATA_FILES:
        kind = "metadata"
    elif "/docs/" in f"/{lower}" or stem in PRIMARY_DOC_NAMES or lower.endswith((".md", ".mdx", ".rst")):
        kind = "documentation"
    elif lower.startswith("test") or "/test" in lower:
        kind = "operator_journey"
        text = _extract_test_names(path, text) or text
    elif lower.endswith(".py"):
        kind = "code_evidence"
        text = _extract_python_code_evidence(path, text) or text
    elif lower.endswith((".js", ".jsx", ".ts", ".tsx")):
        kind = "code_evidence"
        text = _extract_js_code_evidence(path, text) or text
    elif lower.endswith((".css", ".html")):
        kind = "visual_system"
    else:
        kind = "documentation"
    return CandidateSignal(kind=kind, title=path, text=text[:MAX_SIGNAL_TEXT], path=path, url=url)


def _score_and_select(
    candidates: list[CandidateSignal],
    *,
    max_signals: int,
    rejected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scored = []
    by_kind: dict[str, int] = {}
    for candidate in candidates:
        score, reasons = _signal_value(candidate)
        if score < 0.35:
            rejected.append(_reject(candidate.path or candidate.title, "low_signal_value", ", ".join(reasons)))
            continue
        payload = {
            "kind": candidate.kind,
            "title": candidate.title,
            "text": candidate.text[:MAX_SIGNAL_TEXT],
            "provenance": {
                "path": candidate.path,
                "url": candidate.url,
                "line_start": candidate.line_start,
                "line_end": candidate.line_end,
            },
            "signal_value_score": round(score, 3),
            "inclusion_reasons": reasons,
            "metadata": candidate.metadata or {},
        }
        scored.append(payload)
        by_kind[candidate.kind] = by_kind.get(candidate.kind, 0) + 1

    scored.sort(key=lambda item: item["signal_value_score"], reverse=True)
    included = scored[:max_signals]
    for item in scored[max_signals:]:
        rejected.append(_reject(item["provenance"].get("path") or item["title"], "budget_excluded", "lower Signal Value Score"))

    included_by_kind: dict[str, int] = {}
    for item in included:
        kind = item["kind"]
        included_by_kind[kind] = included_by_kind.get(kind, 0) + 1

    return included, {
        "method": "Signal Value Score: relevance + distinctiveness + authority + lens utility + provenance + freshness - noise risk",
        "candidate_count": len(candidates),
        "included_count": len(included),
        "eligible_by_kind": by_kind,
        "included_by_kind": included_by_kind,
        "threshold": 0.35,
        "max_signals": max_signals,
        "top_scores": [
            {
                "title": item["title"],
                "kind": item["kind"],
                "score": item["signal_value_score"],
                "reasons": item["inclusion_reasons"][:3],
            }
            for item in included[:10]
        ],
    }


def _signal_value(candidate: CandidateSignal) -> tuple[float, list[str]]:
    text = candidate.text or ""
    lower = f"{candidate.title}\n{text}".lower()
    score = 0.0
    reasons: list[str] = []
    kind_weight = {
        "repository_metadata": 0.78,
        "documentation": 0.72,
        "metadata": 0.68,
        "visual_system": 0.64,
        "operator_journey": 0.62,
        "media": 0.56,
        "code_evidence": 0.48,
    }.get(candidate.kind, 0.4)
    score += kind_weight
    reasons.append(f"{candidate.kind} evidence")

    relevance_terms = [
        "brand", "design", "market", "user", "customer", "audience", "position",
        "feature", "workflow", "cli", "api", "mcp", "landing", "homepage",
        "naming", "voice", "identity", "product", "operator", "problem",
        "value", "promise", "visual", "color", "typography",
    ]
    hits = [term for term in relevance_terms if term in lower]
    if hits:
        score += min(0.18, len(hits) * 0.025)
        reasons.append("lens utility: " + ", ".join(hits[:5]))
    if candidate.path or candidate.url:
        score += 0.05
        reasons.append("traceable provenance")
    if candidate.metadata and candidate.metadata.get("authority"):
        score += 0.04
        reasons.append(f"authority: {candidate.metadata['authority']}")
    if len(text.strip()) < 20:
        score -= 0.25
        reasons.append("short/noisy")
    if _is_noisy_path(candidate.path or candidate.title):
        score -= 0.3
        reasons.append("noise risk")
    return max(0.0, min(1.0, score)), reasons


def _summarize_rejections(rejected: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    examples: list[dict[str, Any]] = []
    for item in rejected:
        reason = item.get("reason", "unknown")
        counts[reason] = counts.get(reason, 0) + 1
        if len(examples) < 20:
            examples.append(item)
    return {"count": len(rejected), "by_reason": counts, "examples": examples}


def _reject(path: str | None, reason: str, detail: str) -> dict[str, Any]:
    return {"path": path, "reason": reason, "detail": detail}


def _parse_github_url(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise ValueError("GitHub Source Target must be a github.com URL")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub Source Target must include owner and repository")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or _gh_auth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _gh_auth_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    token = result.stdout.strip()
    return token or None


def _github_json(url: str) -> Any:
    if not url:
        raise ValueError("missing GitHub URL")
    req = urllib.request.Request(url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GitHub API error {exc.code}") from exc


def _github_issue_candidates(base: str, endpoint: str, rejected: list[dict[str, Any]]) -> list[CandidateSignal]:
    try:
        items = _github_json(f"{base}/{endpoint}?state=all&per_page=20")
    except Exception as exc:
        rejected.append(_reject(endpoint, "unavailable", str(exc)))
        return []
    candidates = []
    for item in items[:20]:
        title = item.get("title", "")
        labels = [label.get("name") for label in item.get("labels", []) if isinstance(label, dict)]
        body = (item.get("body") or "")[:800]
        candidates.append(CandidateSignal(
            kind="operator_journey",
            title=f"{endpoint}: {title}",
            text=f"{title}\nLabels: {', '.join(labels)}\n{body}",
            url=item.get("html_url"),
            metadata={"authority": endpoint},
        ))
    return candidates


def _github_commit_candidates(base: str, rejected: list[dict[str, Any]]) -> list[CandidateSignal]:
    try:
        items = _github_json(f"{base}/commits?per_page=20")
    except Exception as exc:
        rejected.append(_reject("commits", "unavailable", str(exc)))
        return []
    lines = []
    for item in items[:20]:
        message = ((item.get("commit") or {}).get("message") or "").splitlines()[0]
        if message:
            lines.append(message)
    if not lines:
        return []
    return [CandidateSignal(kind="operator_journey", title="Recent commit trajectory", text="\n".join(lines), metadata={"authority": "commits"})]


def _select_path_for_content(path: str, *, include_code: bool) -> bool:
    lower = path.lower()
    basename = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    if _is_noisy_path(path):
        return False
    if basename in METADATA_FILES:
        return True
    if lower.endswith((".md", ".mdx", ".rst", ".txt")):
        return True
    if any(part in lower for part in ("/docs/", "/examples/", "/example/", "/public/", "/static/", "/assets/")):
        return ext in TEXT_EXTENSIONS or _is_media_path(path)
    if include_code and ext in {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html"}:
        return True
    return False


def _is_noisy_path(path: str) -> bool:
    parts = set(Path(path).parts)
    return bool(parts & SKIP_DIRS) or os.path.basename(path) in GENERATED_OR_NOISY


def _is_sensitive_path(path: str) -> bool:
    return any(pattern.search(path) for pattern in SENSITIVE_NAME_PATTERNS)


def _contains_secret(text: str) -> bool:
    sample = text[:MAX_TEXT_BYTES]
    return any(pattern.search(sample) for pattern in SENSITIVE_CONTENT_PATTERNS)


def _is_media_path(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"}


def _media_signal(path: Path, rel_path: str, *, include_visual_analysis: bool) -> CandidateSignal:
    try:
        size = path.stat().st_size
    except OSError:
        size = None
    mime = mimetypes.guess_type(rel_path)[0]
    text = f"Visual asset: {rel_path}\nMIME: {mime or 'unknown'}\nBytes: {size or 'unknown'}"
    if include_visual_analysis:
        text += "\nVisual analysis requested; downstream renderer may inspect this asset."
    return CandidateSignal(kind="media", title=rel_path, text=text, path=rel_path, metadata={"mime": mime, "bytes": size})


def _extract_python_code_evidence(path: str, text: str) -> str:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    lines = [f"Python module: {path}"]
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            lines.append(f"{node.__class__.__name__}: {node.name}")
            doc = ast.get_docstring(node)
            if doc:
                lines.append(f"Doc: {doc.splitlines()[0][:240]}")
    return "\n".join(lines)


def _extract_js_code_evidence(path: str, text: str) -> str:
    names = []
    for pattern in (
        r"export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)",
        r"export\s+const\s+([A-Za-z0-9_]+)",
        r"function\s+([A-Za-z0-9_]+)",
        r"(?:app|router)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)",
    ):
        for match in re.finditer(pattern, text):
            names.append(" ".join(part for part in match.groups() if part))
    if not names:
        return ""
    return "JavaScript/TypeScript public evidence: " + path + "\n" + "\n".join(names[:60])


def _extract_test_names(path: str, text: str) -> str:
    names = []
    for pattern in (r"def\s+(test_[A-Za-z0-9_]+)", r"it\(['\"]([^'\"]+)", r"test\(['\"]([^'\"]+)"):
        names.extend(match.group(1) for match in re.finditer(pattern, text))
    if not names:
        return ""
    return "Operator journey/test evidence: " + path + "\n" + "\n".join(names[:80])
