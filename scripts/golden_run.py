"""Real-seat golden run: one full Glass Bead Game with the LLM core alive.

Usage: python3 scripts/golden_run.py [path/to/corpus.md]

Ingests the attention x activity ledger via the receipts feed, runs the
canonical pipeline (declare -> elaborate -> connect -> resolve) plus Phase 5
naming with the machine-encoded discipline, and writes a full receipt:
  .elixis/runs/golden-<ts>.json   machine-readable run record
  .elixis/runs/golden-<ts>.md     human receipt with verbatim LLM output
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import elixis  # loads .env seat
from elixis import llm
from elixis.engine import GameEngine
from elixis.receipts import corpus_to_seed, ingest_file

CORPUS_DEFAULT = "/Users/simongonzalezdecruz/workspaces/takeout-staging-elixis-salvage/elixis_run/corpus.md"


def main():
    corpus_path = sys.argv[1] if len(sys.argv) > 1 else CORPUS_DEFAULT
    corpus_data = ingest_file(corpus_path)
    seed = corpus_to_seed(open(corpus_path).read())

    print(f"corpus: {corpus_data['months_count']} months, "
          f"{corpus_data['watched_total']} watched, "
          f"{corpus_data['built_total']} built events, "
          f"{corpus_data['unique_titles']} unique titles")
    print(f"seed: {len(seed)} chars")
    print(f"seat: {llm.cfg.provider} @ {llm.cfg.base_url} model={llm.cfg.default_model} "
          f"available={llm.is_available()}")
    if not llm.is_available():
        print("FATAL: LLM seat not available")
        sys.exit(1)

    t_start = time.time()
    engine = GameEngine()
    engine.declare_themes(seed)
    state = engine.state
    tele = state.metadata["extraction_telemetry"]
    print(f"[declare] beads={len(state.beads)} extraction_source={tele.get('source')} "
          f"tokens={tele.get('tokens_in')}->{tele.get('tokens_out')} "
          f"tps={tele.get('tokens_per_sec')}", flush=True)
    if tele.get("source") != "llm":
        print("FATAL: extraction did not use the LLM core")
        sys.exit(1)

    engine.elaborate()
    en_tele = state.metadata.get("enrichment_telemetry", {})
    print(f"[elaborate] enriched={en_tele.get('success_count')} failed={en_tele.get('fail_count')}", flush=True)

    engine.connect_domains()
    graph = state.metadata["pattern_graph"]
    iso = [t for t in state.threads if t.isomorphic]
    print(f"[connect] patterns={len(graph.get('patterns', []))} bridges={len(graph.get('bridges', []))} "
          f"threads={len(state.threads)} isomorphic={len(iso)} tensions={len(state.tensions)}", flush=True)

    report = engine.name(source="taxonomy")
    disc = report.get("discipline", {})
    print(f"[name] kept={disc.get('kept')} rejected={disc.get('rejected')} "
          f"llm_variants={len(report.get('variants', [])) + len(report.get('rejected_variants', []))}", flush=True)

    output = engine.resolve("identity")
    print(f"[resolve] soulmd {len(output)} chars", flush=True)

    total = round(time.time() - t_start, 1)

    # ── Receipts ────────────────────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".elixis", "runs")
    os.makedirs(run_dir, exist_ok=True)

    plate = report.get("plate")
    record = {
        "timestamp": ts,
        "seat": {"provider": llm.cfg.provider, "base_url": llm.cfg.base_url,
                 "model": llm.cfg.default_model},
        "total_seconds": total,
        "corpus": {"months": corpus_data["months_count"],
                   "watched_total": corpus_data["watched_total"],
                   "built_total": corpus_data["built_total"],
                   "unique_titles": corpus_data["unique_titles"],
                   "built_projects": corpus_data["built_projects"]},
        "seed_length": len(seed),
        "extraction_telemetry": tele,
        "bead_count": len(state.beads),
        "bead_names": [b.canonical for b in state.beads],
        "thread_count": len(state.threads),
        "isomorphic_thread_count": len(iso),
        "tensions": state.tensions,
        "pattern_names": [p.get("name") for p in graph.get("patterns", [])[:5]],
        "emergent_topic": graph.get("emergent_topic"),
        "emergent_theme": graph.get("emergent_theme"),
        "naming": {
            "kept": len(report.get("variants", [])),
            "rejected": len(report.get("rejected_variants", [])),
            "top_kept": [{"name": v["name"], "prosody": v.get("prosody"),
                          "deniability": v.get("deniability", {}).get("verdict"),
                          "identity_fit": v.get("identity_fit"),
                          "discipline_pass": v.get("discipline_pass")}
                         for v in report.get("variants", [])[:6]],
            "rejected_names": [{"name": v["name"], "violations": v.get("kill_list_violations")}
                               for v in report.get("rejected_variants", [])],
        },
        "plate": plate,
        "soulmd_length": len(output),
        "soulmd_preview": output[:500],
    }
    json_path = os.path.join(run_dir, f"golden-{ts}.json")
    with open(json_path, "w") as f:
        json.dump(record, f, indent=2)

    # Human receipt with a verbatim LLM sample pulled from the trace store
    from elixis.traces import get_recent_traces
    traces = get_recent_traces(50)
    naming_trace = next((t for t in traces if "product names" in t.get("prompt_preview", "")), traces[0] if traces else None)

    lines = [
        "# Golden run receipt",
        "",
        f"- seat: `{llm.cfg.provider}` @ `{llm.cfg.base_url}` model `{llm.cfg.default_model}`",
        f"- corpus: {corpus_data['months_count']} months, {corpus_data['unique_titles']} unique titles, "
        f"{corpus_data['built_total']} build events",
        f"- extraction: source={tele.get('source')} tokens {tele.get('tokens_in')}->{tele.get('tokens_out')} "
        f"@ {tele.get('tokens_per_sec')} tok/s",
        f"- beads: {len(state.beads)} | threads: {len(state.threads)} (isomorphic: {len(iso)}) | tensions: {len(state.tensions)}",
        f"- naming: kept {disc.get('kept')}, rejected {disc.get('rejected')}",
        f"- total: {total}s",
        "",
        "## Verbatim LLM sample (naming call)",
        "",
        "```json",
        (naming_trace or {}).get("response_preview", "(no trace)"),
        "```",
        "",
    ]
    if plate:
        from elixis.discipline import format_plate
        lines += ["## Plate (silk + name + subtitle, one unit)", "", "```", format_plate(plate), "```", "",
                  f"validation: {json.dumps(plate.get('validation'))}", "",
                  f"prosody: {json.dumps(plate.get('prosody'))} | deniability: {json.dumps(plate.get('deniability'))}", ""]
    lines += ["## SOUL.md preview", "", "```", output[:800], "```", ""]
    md_path = os.path.join(run_dir, f"golden-{ts}.md")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    print(f"GOLDEN RUN DONE in {total}s")
    print(f"receipts: {json_path} | {md_path}")
    if plate:
        from elixis.discipline import format_plate
        print("\n=== PLATE ===")
        print(format_plate(plate))
        print(f"validation: {plate['validation']}")


if __name__ == "__main__":
    main()
