import math
import re
from collections import Counter
from typing import Protocol

from services.llm import format_openai_error
from services.model_config import ModelConfig, ModelConfigInput


try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class EmbeddingProvider(Protocol):
    mode: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingProviderError(RuntimeError):
    pass


class LocalEmbeddingProvider:
    mode = "local"
    _VECTOR_DIMENSION = 64
    _TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self._embed_single_text(text) for text in texts]

    def _embed_single_text(self, text: str) -> list[float]:
        buckets = [0.0] * self._VECTOR_DIMENSION

        # 使用稳定哈希桶生成固定维度向量，保证本地模式可重复且不依赖外部模型。
        for token, count in Counter(self._tokenize(text)).items():
            bucket_index = sum(token.encode("utf-8")) % self._VECTOR_DIMENSION
            buckets[bucket_index] += float(count)

        norm = math.sqrt(sum(value * value for value in buckets))
        if norm == 0:
            return buckets

        # 做 L2 归一化，便于后续统一按余弦相似度或点积检索。
        return [value / norm for value in buckets]

    def _tokenize(self, text: str) -> list[str]:
        tokens = [token.lower() for token in self._TOKEN_PATTERN.findall(text)]
        if tokens:
            return tokens

        # 对纯标点、emoji 或空文本回退到稳定占位 token，避免产生全零向量。
        normalized_text = text.strip()
        if normalized_text:
            return [f"__fallback__:{normalized_text}"]
        return ["__fallback__:empty"]


class RemoteEmbeddingProvider:
    mode = "remote"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model_name: str,
        openai_class=OpenAI,
    ) -> None:
        self._api_key = api_key.strip()
        self._base_url = base_url.strip()
        self._model_name = model_name.strip()
        self._openai_class = openai_class

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._openai_class is None:
            raise EmbeddingProviderError("当前环境未安装 OpenAI SDK，无法使用远端向量化。")

        try:
            client = self._openai_class(
                api_key=self._api_key,
                base_url=self._base_url or None,
            )
            response = client.embeddings.create(
                model=self._model_name,
                input=texts,
            )
        except Exception as exc:
            raise EmbeddingProviderError(_format_embedding_error(exc)) from exc

        return _normalize_remote_embeddings(texts, response.data)


def build_embedding_provider(
    config: ModelConfig | ModelConfigInput,
) -> EmbeddingProvider:
    if _has_remote_embedding_config(config):
        return RemoteEmbeddingProvider(
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url,
            model_name=config.embedding_model_name,
        )
    return LocalEmbeddingProvider()


def _has_remote_embedding_config(config: ModelConfig | ModelConfigInput) -> bool:
    # 只有关键字段完整时才切远端，避免半配置状态阻断默认本地模式。
    return bool(
        config.embedding_api_key.strip()
        and config.embedding_base_url.strip()
        and config.embedding_model_name.strip()
    )


def embed_texts(
    config: ModelConfig | ModelConfigInput,
    texts: list[str],
) -> list[list[float]]:
    # 统一暴露模块级入口，调用方无需关心 provider 选择细节。
    if not texts:
        return []
    return build_embedding_provider(config).embed_texts(texts)


def _format_embedding_error(exc: Exception) -> str:
    formatted_message = format_openai_error(exc)
    if formatted_message.startswith("模型调用失败："):
        return "Embedding 服务调用失败，请稍后重试或检查配置。"
    return formatted_message


def _normalize_remote_embeddings(texts: list[str], items: list[object]) -> list[list[float]]:
    if len(items) != len(texts):
        raise EmbeddingProviderError("Embedding 返回数量与输入数量不一致。")

    vectors = [list(item.embedding) for item in items]
    if not vectors:
        return vectors

    expected_dimension = len(vectors[0])
    # 远端返回维度必须统一，否则后续索引和相似度计算会失真。
    if any(len(vector) != expected_dimension for vector in vectors[1:]):
        raise EmbeddingProviderError("Embedding 返回向量维度不一致。")

    return vectors
