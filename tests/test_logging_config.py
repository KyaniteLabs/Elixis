"""Logging configuration tests."""

import logging
import unittest

from elixis.logging_config import RequestContextFilter, clear_request_id, get_logger, set_request_id


class TestLoggingConfig(unittest.TestCase):
    def tearDown(self):
        clear_request_id()

    def test_named_logger_does_not_duplicate_via_root_propagation(self):
        logger = get_logger("elixis.test.logging")

        self.assertFalse(logger.propagate)
        self.assertTrue(any(isinstance(filter_, RequestContextFilter) for filter_ in logger.filters))

    def test_existing_named_logger_gets_context_filter(self):
        logger = logging.getLogger("elixis.test.preconfigured")
        logger.handlers = [logging.NullHandler()]
        logger.filters = []
        logger.propagate = True

        configured = get_logger("elixis.test.preconfigured")

        self.assertIs(configured, logger)
        self.assertFalse(configured.propagate)
        self.assertTrue(any(isinstance(filter_, RequestContextFilter) for filter_ in configured.filters))

    def test_request_context_filter_adds_current_request_id(self):
        record = logging.LogRecord("elixis.test", logging.INFO, __file__, 1, "hello", (), None)

        set_request_id("abc123")
        RequestContextFilter().filter(record)

        self.assertEqual(record.request_id, "abc123")
        self.assertEqual(record.service, "elixis")


if __name__ == "__main__":
    unittest.main()
