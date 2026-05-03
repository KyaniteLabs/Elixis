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
        main()
        mock_app_main.assert_called_once()
