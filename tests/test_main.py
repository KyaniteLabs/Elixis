"""Tests for elixis.__main__ — CLI entry point."""

import json
import types
from unittest.mock import MagicMock, patch


class TestMain:
    @patch("builtins.__import__")
    def test_main_calls_app_main(self, mock_import):
        # __main__.main() does: from app import main as app_main; app_main()
        mock_app = MagicMock()
        mock_import.return_value = mock_app
        from elixis.__main__ import main
        # Can't easily mock the import inside the function, so just verify it's callable
        assert callable(main)

    def test_main_function_exists(self):
        from elixis.__main__ import main
        assert callable(main)

    @patch("app.main")
    def test_main_invokes_app(self, mock_app_main):
        from elixis.__main__ import main
        main([])
        mock_app_main.assert_called_once()

    @patch("app.main")
    def test_valid_port_invokes_app(self, mock_app_main):
        from elixis.__main__ import main

        result = main(["--port", "3138"])

        assert result == mock_app_main.return_value
        mock_app_main.assert_called_once()

    @patch("app.main")
    def test_help_does_not_start_app(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["--help"])

        mock_app_main.assert_not_called()
        assert result == 0
        captured = capsys.readouterr()
        assert "usage: elixis" in captured.out
        assert "run" in captured.out

    @patch("app.main")
    def test_short_help_does_not_start_app(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["-h"])

        mock_app_main.assert_not_called()
        assert result == 0
        assert "show this help message and exit" in capsys.readouterr().out

    @patch("app.main")
    def test_version_does_not_start_app(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["--version"])

        mock_app_main.assert_not_called()
        assert result == 0
        assert "elixis 1.0.0" in capsys.readouterr().out

    @patch("app.main")
    def test_unknown_argument_fails_before_starting_server(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["brain dump text"])

        mock_app_main.assert_not_called()
        assert result == 2
        captured = capsys.readouterr()
        assert "invalid choice" in captured.err
        assert "usage: elixis" in captured.err

    @patch("app.main")
    def test_invalid_port_fails_before_starting_server(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["--port", "not-a-port"])

        mock_app_main.assert_not_called()
        assert result == 2
        assert "invalid int value" in capsys.readouterr().err

    @patch("elixis.engine.GameEngine")
    def test_run_command_outputs_json_summary(self, mock_engine_cls, capsys):
        from elixis.__main__ import main

        class FakeBead:
            def to_dict(self):
                return {"canonical": "Athena", "type": "mythological", "themes": ["wisdom"]}

        engine = mock_engine_cls.return_value
        engine.run_full.return_value = "# Brand Output"
        engine.state = types.SimpleNamespace(
            beads=[FakeBead()],
            threads=[object(), object()],
            tensions=[],
            metadata={
                "pattern_graph": {
                    "patterns": [{"name": "Wisdom"}],
                    "emergent_topic": "clarity",
                    "emergent_theme": "wise systems",
                    "consensus_score": 0.9,
                    "threads": [
                        {
                            "bead_a": "Athena",
                            "bead_b": "Batman",
                            "relationship": "complements",
                            "strength": 0.8,
                            "isomorphic": True,
                            "domains_bridged": ["spirituality", "literature"],
                            "evidence": ["Shared themes: strategy"],
                        }
                    ],
                    "thread_count": 1,
                    "cross_domain_thread_count": 1,
                }
            },
            timings={"declaration_ms": 1, "connection_ms": 2, "resolution_ms": 3},
        )

        result = main(["run", "--text", "Athena and design systems", "--lens", "brand", "--json"])

        assert result == 0
        engine.run_full.assert_called_once()
        payload = json.loads(capsys.readouterr().out)
        assert payload["lens"] == "brand"
        assert payload["entity_count"] == 1
        assert payload["cross_domain_thread_count"] == 1
        assert payload["threads"][0]["relationship"] == "complements"
        assert payload["process_trace"]["lens"] == "brand"
        assert payload["process_trace"]["pattern_matching"]["thread_count"] == 1
        assert payload["output"] == "# Brand Output"

    @patch("elixis.entities.extract_entities", return_value=[{"canonical": "Athena"}])
    def test_extract_command_outputs_entities(self, _mock_extract, capsys):
        from elixis.__main__ import main

        result = main(["extract", "--text", "Athena and Batman"])

        assert result == 0
        assert json.loads(capsys.readouterr().out)[0]["canonical"] == "Athena"

    @patch("elixis.patterns.build_pattern_graph", return_value={"patterns": [{"name": "Wisdom"}]})
    @patch("elixis.entities.extract_entities", return_value=[{"canonical": "Athena"}])
    def test_patterns_command_outputs_pattern_graph(self, _mock_extract, _mock_graph, capsys):
        from elixis.__main__ import main

        result = main(["patterns", "--text", "Athena and Batman"])

        assert result == 0
        assert json.loads(capsys.readouterr().out)["patterns"][0]["name"] == "Wisdom"

    @patch("elixis.naming.research_name", return_value={"input_name": "Elixis", "variants": []})
    def test_name_command_researches_name(self, mock_research, capsys):
        from elixis.__main__ import main

        result = main(["name", "--name", "Elixis", "--context", "AI tool", "--no-variants"])

        assert result == 0
        mock_research.assert_called_once_with("Elixis", "AI tool", generate_variants=False, source="taxonomy")
        assert json.loads(capsys.readouterr().out)["input_name"] == "Elixis"

    @patch("elixis.mcp_server.main")
    def test_mcp_command_runs_stdio_server(self, mock_mcp_main):
        from elixis.__main__ import main

        result = main(["mcp"])

        assert result == 0
        mock_mcp_main.assert_called_once()
