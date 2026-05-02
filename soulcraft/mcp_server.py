"""SoulCraft MCP Server — stdio transport, zero external dependencies.

Exposes SoulCraft's pipeline as MCP tools for Claude Code, Cursor,
and any MCP-compatible AI assistant.

Usage in Claude Code settings:
  {
    "mcpServers": {
      "soulcraft": {
        "command": "python",
        "args": ["-m", "soulcraft.mcp_server"]
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
from .research import enrich_entities
from .synthesis import synthesize_soulmd
from .translate import translate_text, get_supported_languages
from .validation import validate_brain_dump

_SERVER_NAME = "soulcraft"
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
            },
            "required": ["name"],
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
        elif name == "extract_entities":
            return _tool_extract_entities(arguments)
        elif name == "analyze_patterns":
            return _tool_analyze_patterns(arguments)
        elif name == "translate_text":
            return _tool_translate(arguments)
        elif name == "research_name":
            return _tool_research_name(arguments)
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}\n{traceback.format_exc()}"}],
            "isError": True,
        }


def _tool_create_soul(args):
    brain_dump = args.get("brain_dump", "")
    is_valid, error, meta = validate_brain_dump(brain_dump)
    if not is_valid:
        return {"content": [{"type": "text", "text": f"Validation error: {error}"}], "isError": True}

    entities = extract_entities(brain_dump)
    enrich_entities(entities)
    graph = build_pattern_graph(entities, brain_dump)
    soulmd = synthesize_soulmd(entities, graph)

    result = {
        "entity_count": len(entities),
        "top_patterns": [p["name"] for p in graph.get("patterns", [])[:3]],
        "emergent_topic": graph.get("emergent_topic"),
        "emergent_theme": graph.get("emergent_theme"),
        "consensus_score": graph.get("consensus_score"),
        "soulmd": soulmd,
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _tool_extract_entities(args):
    text = args.get("text", "")
    if not text or not text.strip():
        return {"content": [{"type": "text", "text": "Error: 'text' must be a non-empty string"}], "isError": True}
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
    if not text or not text.strip():
        return {"content": [{"type": "text", "text": "Error: 'text' must be a non-empty string"}], "isError": True}
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
    if not name or not name.strip():
        return {"content": [{"type": "text", "text": "Error: 'name' must be a non-empty string"}], "isError": True}
    report = research_name(name, context, generate_variants)
    summary = {
        "input_name": report.get("input_name"),
        "semantics": report.get("semantics"),
        "variants": [v.get("name") for v in report.get("variants", [])[:5]],
        "recommendations": report.get("recommendations", [])[:3],
    }
    return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}


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
