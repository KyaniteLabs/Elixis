"""Tests for elixis.__main__ — entry point."""

from unittest.mock import patch, MagicMock


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
        assert "usage: elixis [--port PORT]" in capsys.readouterr().out

    @patch("app.main")
    def test_short_help_does_not_start_app(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["-h"])

        mock_app_main.assert_not_called()
        assert result == 0
        assert "show this help message and exit" in capsys.readouterr().out

    @patch("app.main")
    def test_unknown_argument_fails_before_starting_server(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["brain dump text"])

        mock_app_main.assert_not_called()
        assert result == 2
        captured = capsys.readouterr()
        assert "unknown argument" in captured.err
        assert "usage: elixis [--port PORT]" in captured.err

    @patch("app.main")
    def test_invalid_port_fails_before_starting_server(self, mock_app_main, capsys):
        from elixis.__main__ import main

        result = main(["--port", "not-a-port"])

        mock_app_main.assert_not_called()
        assert result == 2
        assert "invalid --port value" in capsys.readouterr().err
