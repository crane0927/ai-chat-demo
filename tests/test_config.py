import os
from unittest import mock
import unittest

import config


class ConfigTestCase(unittest.TestCase):
    def test_get_database_url_prefers_app_database_url(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "APP_DATABASE_URL": "postgresql://app-user:pass@localhost:5432/app_db",
                "DATABASE_URL": "postgresql://fallback-user:pass@localhost:5432/fallback_db",
            },
            clear=True,
        ):
            self.assertEqual(
                config.get_database_url(),
                "postgresql://app-user:pass@localhost:5432/app_db",
            )

    def test_get_env_max_tokens_clamps_to_upper_bound(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_MAX_TOKENS": "999999"}, clear=True):
            self.assertEqual(config.get_env_max_tokens(), 32000)

    def test_get_env_timeout_seconds_uses_default_for_invalid_value(self) -> None:
        with mock.patch.dict(
            os.environ, {"OPENAI_TIMEOUT_SECONDS": "oops"}, clear=True
        ):
            self.assertEqual(
                config.get_env_timeout_seconds(), config.DEFAULT_TIMEOUT_SECONDS
            )

    def test_get_env_max_retries_clamps_to_lower_bound(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_MAX_RETRIES": "-5"}, clear=True):
            self.assertEqual(config.get_env_max_retries(), 0)


if __name__ == "__main__":
    unittest.main()
