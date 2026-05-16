from unittest import mock
import unittest

from services import llm
from services import embeddings
from services.embeddings import (
    EmbeddingProviderError,
    LocalEmbeddingProvider,
    RemoteEmbeddingProvider,
    build_embedding_provider,
    embed_texts,
)
from services.model_config import ModelConfigInput


class EmbeddingsTestCase(unittest.TestCase):
    def test_local_embedding_provider_returns_repeatable_same_dimension_vectors(
        self,
    ) -> None:
        provider = LocalEmbeddingProvider()

        first_result = provider.embed_texts(["alpha beta", "alpha gamma"])
        second_result = provider.embed_texts(["alpha beta", "alpha gamma"])

        self.assertEqual(len(first_result), 2)
        self.assertEqual(len(first_result[0]), len(first_result[1]))
        self.assertEqual(first_result, second_result)

    def test_build_embedding_provider_prefers_remote_when_embedding_config_complete(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="OpenAI",
            provider="OpenAI",
            api_key="sk-chat",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4.1",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="emb-key",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        provider = build_embedding_provider(config)

        self.assertEqual(provider.mode, "remote")

    def test_build_embedding_provider_falls_back_to_local_when_embedding_config_incomplete(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="OpenAI",
            provider="OpenAI",
            api_key="sk-chat",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4.1",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        provider = build_embedding_provider(config)

        self.assertEqual(provider.mode, "local")

    def test_embed_texts_uses_module_level_entrypoint(self) -> None:
        config = ModelConfigInput(
            name="Local",
            provider="Local",
            api_key="",
            base_url="",
            model_name="",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="",
            embedding_base_url="",
            embedding_model_name="",
        )

        result = embed_texts(config, ["alpha beta", "alpha gamma"])

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), len(result[1]))

    def test_embed_texts_returns_empty_list_without_building_provider_for_empty_input(
        self,
    ) -> None:
        config = ModelConfigInput(
            name="Remote",
            provider="OpenAI",
            api_key="sk-chat",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4.1",
            temperature=0.7,
            max_tokens=1024,
            context_message_limit=20,
            timeout_seconds=30.0,
            max_retries=2,
            enabled=True,
            embedding_api_key="emb-key",
            embedding_base_url="https://emb.example.com/v1",
            embedding_model_name="text-embedding-3-small",
        )

        with mock.patch.object(
            embeddings,
            "build_embedding_provider",
            side_effect=AssertionError("should not build provider"),
        ):
            result = embed_texts(config, [])

        self.assertEqual(result, [])

    def test_local_embedding_provider_returns_stable_fallback_for_text_without_tokens(
        self,
    ) -> None:
        provider = LocalEmbeddingProvider()

        first_result = provider.embed_texts(["!!!", "😀😀😀"])
        second_result = provider.embed_texts(["!!!", "😀😀😀"])

        self.assertEqual(first_result, second_result)
        self.assertGreater(sum(abs(value) for value in first_result[0]), 0.0)
        self.assertGreater(sum(abs(value) for value in first_result[1]), 0.0)

    def test_remote_embedding_provider_returns_vectors_from_remote_api(self) -> None:
        class FakeEmbeddingsClient:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return type(
                    "FakeResponse",
                    (),
                    {
                        "data": [
                            type("Item", (), {"embedding": [0.1, 0.2, 0.3]})(),
                            type("Item", (), {"embedding": [0.4, 0.5, 0.6]})(),
                        ]
                    },
                )()

        fake_embeddings = FakeEmbeddingsClient()
        fake_openai = type(
            "FakeOpenAI",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(
                    self, "embeddings", fake_embeddings
                )
            },
        )

        provider = RemoteEmbeddingProvider(
            api_key="emb-key",
            base_url="https://emb.example.com/v1",
            model_name="text-embedding-3-small",
            openai_class=fake_openai,
        )

        result = provider.embed_texts(["alpha", "beta"])

        self.assertEqual(result, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.assertEqual(fake_embeddings.calls[0]["input"], ["alpha", "beta"])
        self.assertEqual(
            fake_embeddings.calls[0]["model"], "text-embedding-3-small"
        )

    def test_remote_embedding_provider_raises_stable_error_when_remote_call_fails(
        self,
    ) -> None:
        class FakeEmbeddingsClient:
            def create(self, **kwargs):
                raise RuntimeError("boom")

        fake_openai = type(
            "FakeOpenAI",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(
                    self, "embeddings", FakeEmbeddingsClient()
                )
            },
        )

        provider = RemoteEmbeddingProvider(
            api_key="emb-key",
            base_url="https://emb.example.com/v1",
            model_name="text-embedding-3-small",
            openai_class=fake_openai,
        )

        with self.assertRaises(EmbeddingProviderError) as context:
            provider.embed_texts(["alpha"])

        self.assertEqual(
            str(context.exception),
            "Embedding 服务调用失败，请稍后重试或检查配置。",
        )

    def test_remote_embedding_provider_maps_sdk_style_error_to_stable_message(
        self,
    ) -> None:
        class FakeAuthenticationError(Exception):
            pass

        class FakeEmbeddingsClient:
            def create(self, **kwargs):
                raise FakeAuthenticationError("bad key")

        fake_openai = type(
            "FakeOpenAI",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(
                    self, "embeddings", FakeEmbeddingsClient()
                )
            },
        )
        provider = RemoteEmbeddingProvider(
            api_key="emb-key",
            base_url="https://emb.example.com/v1",
            model_name="text-embedding-3-small",
            openai_class=fake_openai,
        )

        with mock.patch.object(
            llm,
            "AuthenticationError",
            FakeAuthenticationError,
        ):
            with self.assertRaises(EmbeddingProviderError) as context:
                provider.embed_texts(["alpha"])

        self.assertEqual(
            str(context.exception),
            "鉴权失败：API Key 无效、已过期，或当前服务商不接受该密钥。",
        )

    def test_remote_embedding_provider_raises_stable_error_when_response_count_mismatches(
        self,
    ) -> None:
        class FakeEmbeddingsClient:
            def create(self, **kwargs):
                return type(
                    "FakeResponse",
                    (),
                    {"data": [type("Item", (), {"embedding": [0.1, 0.2]})()]},
                )()

        fake_openai = type(
            "FakeOpenAI",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(
                    self, "embeddings", FakeEmbeddingsClient()
                )
            },
        )
        provider = RemoteEmbeddingProvider(
            api_key="emb-key",
            base_url="https://emb.example.com/v1",
            model_name="text-embedding-3-small",
            openai_class=fake_openai,
        )

        with self.assertRaises(EmbeddingProviderError) as context:
            provider.embed_texts(["alpha", "beta"])

        self.assertEqual(str(context.exception), "Embedding 返回数量与输入数量不一致。")

    def test_remote_embedding_provider_raises_stable_error_when_vector_dimensions_mismatch(
        self,
    ) -> None:
        class FakeEmbeddingsClient:
            def create(self, **kwargs):
                return type(
                    "FakeResponse",
                    (),
                    {
                        "data": [
                            type("Item", (), {"embedding": [0.1, 0.2]})(),
                            type("Item", (), {"embedding": [0.3, 0.4, 0.5]})(),
                        ]
                    },
                )()

        fake_openai = type(
            "FakeOpenAI",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(
                    self, "embeddings", FakeEmbeddingsClient()
                )
            },
        )
        provider = RemoteEmbeddingProvider(
            api_key="emb-key",
            base_url="https://emb.example.com/v1",
            model_name="text-embedding-3-small",
            openai_class=fake_openai,
        )

        with self.assertRaises(EmbeddingProviderError) as context:
            provider.embed_texts(["alpha", "beta"])

        self.assertEqual(str(context.exception), "Embedding 返回向量维度不一致。")

    def test_remote_embedding_provider_raises_stable_error_when_sdk_missing(
        self,
    ) -> None:
        provider = RemoteEmbeddingProvider(
            api_key="emb-key",
            base_url="https://emb.example.com/v1",
            model_name="text-embedding-3-small",
            openai_class=None,
        )

        with self.assertRaises(EmbeddingProviderError) as context:
            provider.embed_texts(["alpha"])

        self.assertEqual(str(context.exception), "当前环境未安装 OpenAI SDK，无法使用远端向量化。")


if __name__ == "__main__":
    unittest.main()
