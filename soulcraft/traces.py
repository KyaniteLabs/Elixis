"""Trace and diagnostics system for Soulcraft.

Saves LLM traces, pipeline runs, and request logs to disk.
All data goes to the .soulcraft/ directory next to app.py.

Structure:
  .soulcraft/
    traces/       — One JSON per LLM call
    runs/         — One JSON per pipeline run (brain dump → SOUL.md)
    requests.log  — HTTP request log (JSONL)
"""

import json
import os
import time
from datetime import datetime, timezone

_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".soulcraft")
_TRACES_DIR = os.path.join(_BASE_DIR, "traces")
_RUNS_DIR = os.path.join(_BASE_DIR, "runs")
_REQUESTS_LOG = os.path.join(_BASE_DIR, "requests.log")


def _ensure_dirs():
    os.makedirs(_TRACES_DIR, exist_ok=True)
    os.makedirs(_RUNS_DIR, exist_ok=True)


def save_trace(prompt, response, latency_ms, model="", extra=None):
    """Save an LLM call trace."""
    _ensure_dirs()
    ts = datetime.now(timezone.utc)
    entry = {
        "timestamp": ts.isoformat(),
        "model": model,
        "latency_ms": latency_ms,
        "prompt_preview": prompt[:500] if prompt else "",
        "response_preview": response[:500] if response else "",
        "response_length": len(response) if response else 0,
    }
    if extra:
        entry.update(extra)

    filepath = os.path.join(_TRACES_DIR, f"{ts.strftime('%Y%m%d_%H%M%S_%f')}.json")
    try:
        with open(filepath, "w") as f:
            json.dump(entry, f, indent=2)
    except OSError:
        pass  # trace saving is best-effort


def save_run(brain_dump, entities, graph, soulmd, stage_timings=None):
    """Save a full pipeline run."""
    _ensure_dirs()
    ts = datetime.now(timezone.utc)
    entry = {
        "timestamp": ts.isoformat(),
        "brain_dump_length": len(brain_dump),
        "brain_dump_preview": brain_dump[:300],
        "entity_count": len(entities),
        "entity_types": _count_types(entities),
        "pattern_count": len(graph.get("patterns", [])),
        "emergent_topic": graph.get("emergent_topic"),
        "emergent_theme": graph.get("emergent_theme"),
        "consensus_score": graph.get("consensus_score"),
        "bridge_count": len(graph.get("bridges", [])),
        "soulmd_length": len(soulmd),
        "soulmd_preview": soulmd[:300],
        "top_patterns": [
            {"name": p["name"], "probability": p.get("probability", 0)}
            for p in graph.get("patterns", [])[:3]
        ],
    }
    if stage_timings:
        entry["stage_timings_ms"] = stage_timings
        entry["total_ms"] = sum(stage_timings.values())

    filepath = os.path.join(_RUNS_DIR, f"{ts.strftime('%Y%m%d_%H%M%S_%f')}.json")
    try:
        with open(filepath, "w") as f:
            json.dump(entry, f, indent=2)
    except OSError:
        pass


def log_request(method, path, status, duration_ms, extra=None):
    """Append an HTTP request log entry."""
    _ensure_dirs()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "path": path,
        "status": status,
        "duration_ms": round(duration_ms, 1),
    }
    if extra:
        entry.update(extra)
    try:
        with open(_REQUESTS_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def get_recent_traces(limit=20):
    """Load recent LLM traces, newest first."""
    _ensure_dirs()
    traces = []
    try:
        files = sorted(os.listdir(_TRACES_DIR), reverse=True)[:limit]
        for fname in files:
            if fname.endswith(".json"):
                with open(os.path.join(_TRACES_DIR, fname)) as f:
                    traces.append(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    return traces


def get_recent_runs(limit=20):
    """Load recent pipeline runs, newest first."""
    _ensure_dirs()
    runs = []
    try:
        files = sorted(os.listdir(_RUNS_DIR), reverse=True)[:limit]
        for fname in files:
            if fname.endswith(".json"):
                with open(os.path.join(_RUNS_DIR, fname)) as f:
                    runs.append(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    return runs


def get_recent_requests(limit=50):
    """Load recent request log entries."""
    if not os.path.isfile(_REQUESTS_LOG):
        return []
    entries = []
    try:
        with open(_REQUESTS_LOG) as f:
            lines = f.readlines()
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass
    return entries


def get_diagnostics():
    """Get full diagnostics summary."""
    runs = get_recent_runs(100)
    traces = get_recent_traces(100)

    avg_latency = 0
    if traces:
        avg_latency = round(sum(t.get("latency_ms", 0) for t in traces) / len(traces))

    avg_total = 0
    if runs:
        avg_total = round(sum(r.get("total_ms", 0) for r in runs) / len(runs))

    return {
        "status": "ok",
        "total_runs": len(runs),
        "total_traces": len(traces),
        "avg_llm_latency_ms": avg_latency,
        "avg_pipeline_ms": avg_total,
        "recent_runs": get_recent_runs(5),
        "recent_traces": get_recent_traces(5),
        "recent_requests": get_recent_requests(20),
    }


def _count_types(entities):
    """Count entity types."""
    counts = {}
    for e in entities:
        t = e.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts
