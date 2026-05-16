from dataclasses import dataclass
from typing import Dict


Message = Dict[str, str]


@dataclass(frozen=True)
class ModelRequestOptions:
    max_tokens: int
    context_message_limit: int
    timeout_seconds: float
    max_retries: int
