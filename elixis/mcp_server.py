"""Elixis MCP Server — stdio transport, zero external dependencies.

Exposes Elixis's pipeline as tools for any MCP-compatible AI assistant.

Usage in an MCP client config:
  {
    "mcpServers": {
      "elixis": {
        "command": "python",
        "args": ["-m", "elixis.mcp_server"]
      }
    }
  }
"""

import json
import sys
import traceback

from .entities import extract_entities
from .naming import research_name
from .patterns import build_pattern_graph
from .process_trace import process_trace_from_state
from .thread import serialize_threads
from .translate import translate_text
from .validation import validate_brain_dump

_SERVER_NAME = "elixis"
_SERVER_VERSION = "1.0.0"
_PROTOCOL_VERSION = "2024-11-05"

_TOOLS = [
    {
        "name": "create_soul",
        "description": (
            "Transform brain dump text into a structured SOUL.md identity document. "
            "Use when: creating AI persona documents, synthesizing identity from notes, "
            "generating OpenClaw-compatible agent personas."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "brain_dump": {
                    "type": "string",
                    "description": "Raw text containing references, influences, values, people, works, or concepts that define an identity.",
                },
            },
            "required": ["brain_dump"],
        },
    },
    {
        "name": "run_game",
        "description": (
            "Run Elixis pattern synthesis through an output lens. "
            "Use when: generating identity, brand, or design documents from scattered references, "
            "or when SOUL.md is too narrow for the requested output."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "brain_dump": {
                    "type": "string",
                    "description": "Raw text containing references, influences, values, people, works, or concepts.",
                },
                "lens": {
                    "type": "string",
                    "description": "Output lens to resolve through. Default: identity.",
                    "enum": ["identity", "brand", "design"],
                },
            },
            "required": ["brain_dump"],
        },
    },
    {
        "name": "extract_entities",
        "description": (
            "Extract structured entities (people, works, concepts, values) from text. "
            "Use when: analyzing what references someone chose, finding named entities in creative notes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to extract entities from.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "analyze_patterns",
        "description": (
            "Analyze text for archetypal patterns (transformation, power, shadow, trickster, etc.) "
            "and return a pattern probability graph. Use when: understanding the symbolic DNA of a set of references."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to analyze for patterns.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "translate_text",
        "description": (
            "Translate text to a target language. Use when: checking cross-language risks, "
            "translating SOUL.md output, multilingual naming review."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to translate."},
                "target_lang": {"type": "string", "description": "Target language code (e.g. 'es', 'fr', 'de')."},
                "source_lang": {"type": "string", "description": "Source language code (default: 'en')."},
            },
            "required": ["text", "target_lang"],
        },
    },
    {
        "name": "research_name",
        "description": (
            "Research a name with semantic analysis, pronounceability scoring, and variant generation. "
            "Use when: evaluating brand names, checking name quality, generating naming alternatives."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to research."},
                "context": {"type": "string", "description": "Context for the name (e.g. 'AI startup', 'creative agency')."},
                "generate_variants": {"type": "boolean", "description": "Whether to generate name variants (default: true)."},
                "source": {"type": "string", "description": "Variant source: 'general' (LLM freeform) or 'taxonomy' (scientific names). Default: 'general'.", "enum": ["general", "taxonomy"]},
            },
            "required": ["name"],
        },
    },
    {
        "name": "name_from_identity",
        "description": (
            "Generate product/brand name suggestions grounded in the identity synthesized from a brain dump. "
            "Runs the full pipeline (entity extraction, pattern analysis) and produces names aligned with "
            "the emergent identity themes. Use when: naming a persona, brand, or project from scattered influences."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "brain_dump": {"type": "string", "description": "Raw text containing references, influences, and values to synthesize and name."},
                "source": {"type": "string", "description": "Variant source: 'taxonomy' (scientific names) or 'general' (LLM freeform). Default: 'taxonomy'.", "enum": ["general", "taxonomy"]},
            },
            "required": ["brain_dump"],
        },
    },
    {
        "name": "ingest_source",
        "description": (
            "Build a Source Corpus from a GitHub repository URL or local folder path. "
            "Use when: gathering product evidence before naming, brand, design, identity, or marketing synthesis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "github": {"type": "string", "description": "GitHub repository URL to ingest."},
                "path": {"type": "string", "description": "Local folder path to ingest."},
                "include_code": {"type": "boolean", "description": "Include supporting code evidence. Default: false."},
                "include_issues": {"type": "boolean", "description": "Include GitHub issue evidence. Default: false."},
                "include_prs": {"type": "boolean", "description": "Include GitHub pull request evidence. Default: false."},
                "include_commits": {"type": "boolean", "description": "Include GitHub commit trajectory evidence. Default: false."},
                "artifacts": {"type": "array", "items": {"type": "string"}, "description": "Artifact tiers to render."},
            },
        },
    },
    {
        "name": "create_market_kit",
        "description": (
            "Create a structured Market Kit from a GitHub repository URL or local folder path. "
            "Returns naming, positioning, brand, messaging, design-system direction, evidence, and optional artifacts."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "github": {"type": "string", "description": "GitHub repository URL to ingest."},
                "path": {"type": "string", "description": "Local folder path to ingest."},
                "artifacts": {"type": "array", "items": {"type": "string"}, "description": "Artifact tiers: markdown, html, css, market-page."},
                "include_code": {"type": "boolean", "description": "Include supporting code evidence. Default: true."},
                "include_issues": {"type": "boolean", "description": "Include GitHub issue evidence. Default: false."},
                "include_prs": {"type": "boolean", "description": "Include GitHub pull request evidence. Default: false."},
                "include_commits": {"type": "boolean", "description": "Include GitHub commit trajectory evidence. Default: false."},
                "max_signals": {"type": "integer", "description": "Maximum Corpus Signals to include. Default: 80."},
            },
        },
    },
]


def _send(msg):
    """Write a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _read():
    """Read a JSON-RPC message from stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())


def _handle_initialize(params):
    return {
        "protocolVersion": _PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
    }


def _handle_tools_list(_params):
    return {"tools": _TOOLS}


def _handle_tools_call(params):
    name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if name == "create_soul":
            return _tool_create_soul(arguments)
        elif name == "run_game":
            return _tool_run_game(arguments)
        elif name == "extract_entities":
            return _tool_extract_entities(arguments)
        elif name == "analyze_patterns":
            return _tool_analyze_patterns(arguments)
        elif name == "translate_text":
            return _tool_translate(arguments)
        elif name == "research_name":
            return _tool_research_name(arguments)
        elif name == "name_from_identity":
            return _tool_name_from_identity(arguments)
        elif name == "ingest_source":
            return _tool_ingest_source(arguments)
        elif name == "create_market_kit":
            return _tool_create_market_kit(arguments)
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "isError": True,
        }


def _tool_create_soul(args):
    brain_dump = args.get("brain_dump", "")
    is_valid, error, meta = validate_brain_dump(brain_dump)
    if not is_valid:
        return {"content": [{"type": "text", "text": f"Validation error: {error}"}], "isError": True}
    brain_dump = meta.get("sanitized_text", brain_dump)

    from .engine import GameEngine
    engine = GameEngine()
    soulmd = engine.run_full(brain_dump, lens="identity")
    state = engine.state
    graph = state.metadata.get("pattern_graph", {})
    threads = graph.get("threads") or serialize_threads(state.threads)
    result = {
        "entity_count": len(state.beads),
        "thread_count": graph.get("thread_count", len(state.threads)),
        "cross_domain_thread_count": graph.get("cross_domain_thread_count", 0),
        "threads": threads[:8],
        "top_patterns": [p.get("name") for p in graph.get("patterns", [])[:3]],
        "emergent_topic": graph.get("emergent_topic"),
        "emergent_theme": graph.get("emergent_theme"),
        "consensus_score": graph.get("consensus_score"),
        "process_trace": process_trace_from_state(state, lens="identity"),
        "soulmd": soulmd,
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _tool_run_game(args):
    brain_dump = args.get("brain_dump", "")
    lens = args.get("lens", "identity")
    if lens not in {"identity", "brand", "design"}:
        return {
            "content": [{"type": "text", "text": "Validation error: lens must be one of identity, brand, design"}],
            "isError": True,
        }

    is_valid, error, meta = validate_brain_dump(brain_dump)
    if not is_valid:
        return {"content": [{"type": "text", "text": f"Validation error: {error}"}], "isError": True}
    brain_dump = meta.get("sanitized_text", brain_dump)

    from .engine import GameEngine
    engine = GameEngine()
    output = engine.run_full(brain_dump, lens=lens)
    state = engine.state
    graph = state.metadata.get("pattern_graph", {})
    threads = graph.get("threads") or serialize_threads(state.threads)
    result = {
        "lens": lens,
        "entity_count": len(state.beads),
        "thread_count": graph.get("thread_count", len(state.threads)),
        "cross_domain_thread_count": graph.get("cross_domain_thread_count", 0),
        "threads": threads[:8],
        "tension_count": len(state.tensions),
        "top_patterns": [p.get("name") for p in graph.get("patterns", [])[:3]],
        "emergent_topic": graph.get("emergent_topic"),
        "emergent_theme": graph.get("emergent_theme"),
        "consensus_score": graph.get("consensus_score"),
        "process_trace": process_trace_from_state(state, lens=lens),
        "output": output,
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _tool_extract_entities(args):
    text = args.get("text", "")
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        return {"content": [{"type": "text", "text": f"Validation error: {error}"}], "isError": True}
    text = meta.get("sanitized_text", text)
    entities = extract_entities(text)
    out = []
    for e in entities[:15]:
        out.append({
            "name": e.get("canonical", ""),
            "type": e.get("type", ""),
            "themes": e.get("themes", []),
        })
    return {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}


def _tool_analyze_patterns(args):
    text = args.get("text", "")
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        return {"content": [{"type": "text", "text": f"Validation error: {error}"}], "isError": True}
    text = meta.get("sanitized_text", text)
    entities = extract_entities(text)
    graph = build_pattern_graph(entities, text)
    result = {
        "patterns": [
            {"name": p["name"], "probability": round(p["probability"], 3)}
            for p in graph.get("patterns", [])
        ],
        "emergent_topic": graph.get("emergent_topic"),
        "emergent_theme": graph.get("emergent_theme"),
        "consensus_score": graph.get("consensus_score"),
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _tool_translate(args):
    text = args.get("text", "")
    target_lang = args.get("target_lang", "")
    source_lang = args.get("source_lang", "en")
    if not text or not text.strip():
        return {"content": [{"type": "text", "text": "Error: 'text' must be a non-empty string"}], "isError": True}
    if not target_lang or len(target_lang) != 2:
        return {"content": [{"type": "text", "text": "Error: 'target_lang' must be a 2-letter language code"}], "isError": True}
    result = translate_text(text, target_lang, source_lang)
    if result.get("success"):
        return {"content": [{"type": "text", "text": result.get("translated_text", "")}]}
    return {
        "content": [{"type": "text", "text": f"Translation failed: {result.get('error', 'unknown')}"}],
        "isError": True,
    }


def _tool_research_name(args):
    name = args.get("name", "")
    context = args.get("context", "")
    generate_variants = args.get("generate_variants", True)
    source = args.get("source", "general")
    if not name or not name.strip():
        return {"content": [{"type": "text", "text": "Error: 'name' must be a non-empty string"}], "isError": True}
    report = research_name(name, context, generate_variants, source=source)
    summary = {
        "input_name": report.get("input_name"),
        "semantics": report.get("semantics"),
        "variants": [v.get("name") for v in report.get("variants", [])[:5]],
        "recommendations": report.get("recommendations", [])[:3],
    }
    return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}


def _tool_name_from_identity(args):
    brain_dump = args.get("brain_dump", "")
    source = args.get("source", "taxonomy")
    is_valid, error, meta = validate_brain_dump(brain_dump)
    if not is_valid:
        return {"content": [{"type": "text", "text": f"Validation error: {error}"}], "isError": True}
    brain_dump = meta.get("sanitized_text", brain_dump)

    from .engine import GameEngine
    engine = GameEngine()
    engine.declare_themes(brain_dump)
    engine.elaborate()
    engine.connect_domains()
    report = engine.name(source=source)

    summary = {
        "emergent_theme": report.get("identity_context", {}).get("emergent_theme"),
        "dominant_patterns": [
            p.get("name") for p in report.get("identity_context", {}).get("dominant_patterns", [])
        ],
        "variants": [
            {"name": v.get("name"), "fit": f"{v.get('identity_fit', 0):.0%}", "style": v.get("style")}
            for v in report.get("variants", [])[:5]
        ],
        "recommendations": report.get("recommendations", [])[:3],
    }
    return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}


def _tool_ingest_source(args):
    from .ingest import ingest_source

    try:
        result = ingest_source(
            github=args.get("github"),
            path=args.get("path"),
            artifacts=args.get("artifacts") or [],
            include_code=bool(args.get("include_code", False)),
            include_issues=bool(args.get("include_issues", False)),
            include_prs=bool(args.get("include_prs", False)),
            include_commits=bool(args.get("include_commits", False)),
            include_hidden=bool(args.get("include_hidden", False)),
            include_large_files=bool(args.get("include_large_files", False)),
            include_visual_analysis=bool(args.get("include_visual_analysis", False)),
            max_signals=int(args.get("max_signals", 80)),
        )
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"Validation error: {exc}"}], "isError": True}
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _tool_create_market_kit(args):
    from .market import create_market_kit

    try:
        result = create_market_kit(
            github=args.get("github"),
            path=args.get("path"),
            artifacts=args.get("artifacts") or [],
            include_code=bool(args.get("include_code", True)),
            include_issues=bool(args.get("include_issues", False)),
            include_prs=bool(args.get("include_prs", False)),
            include_commits=bool(args.get("include_commits", False)),
            include_hidden=bool(args.get("include_hidden", False)),
            include_large_files=bool(args.get("include_large_files", False)),
            include_visual_analysis=bool(args.get("include_visual_analysis", False)),
            max_signals=int(args.get("max_signals", 80)),
        )
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"Validation error: {exc}"}], "isError": True}
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


_HANDLERS = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}


def main():
    """Run the MCP server on stdio."""
    while True:
        msg = _read()
        if msg is None:
            break

        method = msg.get("method", "")
        params = msg.get("params", {})
        msg_id = msg.get("id")

        # Notification (no id) — skip
        if msg_id is None and method == "notifications/initialized":
            continue

        handler = _HANDLERS.get(method)
        if handler:
            try:
                result = handler(params)
                _send({"jsonrpc": "2.0", "id": msg_id, "result": result})
            except Exception as e:
                _send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)},
                })
        else:
            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })


if __name__ == "__main__":
    main()
