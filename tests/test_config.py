import os
from pathlib import Path
import tempfile
from unittest import mock
import unittest
import importlib

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

    def test_get_rag_max_file_size_mb_uses_default_when_env_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                config.get_rag_max_file_size_mb(),
                config.DEFAULT_RAG_MAX_FILE_SIZE_MB,
            )

    def test_get_rag_max_chunks_per_file_parses_env_value(self) -> None:
        with mock.patch.dict(
            os.environ, {"RAG_MAX_CHUNKS_PER_FILE": "123"}, clear=True
        ):
            self.assertEqual(config.get_rag_max_chunks_per_file(), 123)

    def test_get_rag_top_k_clamps_invalid_large_value(self) -> None:
        with mock.patch.dict(os.environ, {"RAG_TOP_K": "999"}, clear=True):
            self.assertEqual(config.get_rag_top_k(), 20)

    def test_get_rag_top_k_uses_default_for_invalid_value(self) -> None:
        with mock.patch.dict(os.environ, {"RAG_TOP_K": "oops"}, clear=True):
            self.assertEqual(config.get_rag_top_k(), config.DEFAULT_RAG_TOP_K)

    def test_load_dotenv_file_sets_missing_env_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "OPENAI_API_KEY=dotenv-key\nOPENAI_CHAT_MODEL=dotenv-model\n",
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {}, clear=True):
                loaded = config.load_dotenv_file(env_file)

                self.assertTrue(loaded)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "dotenv-key")
                self.assertEqual(os.environ["OPENAI_CHAT_MODEL"], "dotenv-model")

    def test_load_dotenv_file_does_not_override_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("OPENAI_API_KEY=dotenv-key\n", encoding="utf-8")

            with mock.patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "shell-key"},
                clear=True,
            ):
                config.load_dotenv_file(env_file)

                self.assertEqual(os.environ["OPENAI_API_KEY"], "shell-key")

    def test_import_loads_dotenv_from_current_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("OPENAI_API_KEY=autoload-key\n", encoding="utf-8")
            original_cwd = os.getcwd()

            try:
                os.chdir(temp_dir)
                with mock.patch.dict(os.environ, {}, clear=True):
                    importlib.reload(config)

                    self.assertEqual(os.environ["OPENAI_API_KEY"], "autoload-key")
            finally:
                os.chdir(original_cwd)
                importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
