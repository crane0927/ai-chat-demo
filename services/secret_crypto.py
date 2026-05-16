import base64
import hashlib
import hmac
import os


ENCRYPTED_PREFIX = "enc:v1:"
NONCE_SIZE = 16
TAG_SIZE = 32


class SecretCryptoError(RuntimeError):
    pass


class MissingSecretKeyError(SecretCryptoError):
    pass


class InvalidCiphertextError(SecretCryptoError):
    pass


def is_encrypted_value(value: str) -> bool:
    return (value or "").startswith(ENCRYPTED_PREFIX)


def _derive_key(secret_key: str, label: str) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        secret_key.encode("utf-8"),
        label.encode("utf-8"),
        120_000,
        dklen=32,
    )


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def _build_keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    blocks = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        block = hmac.new(
            enc_key,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        blocks.append(block)
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_string(plaintext: str, secret_key: str) -> str:
    if not secret_key.strip():
        raise MissingSecretKeyError("缺少 APP_SECRET_KEY，无法加密 API Key。")

    plaintext_bytes = plaintext.encode("utf-8")
    nonce = os.urandom(NONCE_SIZE)
    enc_key = _derive_key(secret_key, "ai-chat-demo:enc")
    mac_key = _derive_key(secret_key, "ai-chat-demo:mac")
    ciphertext = _xor_bytes(
        plaintext_bytes,
        _build_keystream(enc_key, nonce, len(plaintext_bytes)),
    )
    tag = hmac.new(
        mac_key,
        nonce + ciphertext,
        hashlib.sha256,
    ).digest()
    payload = base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{payload}"


def decrypt_string(ciphertext: str, secret_key: str) -> str:
    if not secret_key.strip():
        raise MissingSecretKeyError("缺少 APP_SECRET_KEY，无法解密已保存的 API Key。")

    if not is_encrypted_value(ciphertext):
        raise InvalidCiphertextError("当前值不是受支持的加密格式。")

    encoded_payload = ciphertext[len(ENCRYPTED_PREFIX) :]
    try:
        payload = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
    except Exception as exc:
        raise InvalidCiphertextError("API Key 密文格式无效。") from exc

    if len(payload) < NONCE_SIZE + TAG_SIZE:
        raise InvalidCiphertextError("API Key 密文长度无效。")

    nonce = payload[:NONCE_SIZE]
    tag = payload[NONCE_SIZE : NONCE_SIZE + TAG_SIZE]
    encrypted_bytes = payload[NONCE_SIZE + TAG_SIZE :]
    mac_key = _derive_key(secret_key, "ai-chat-demo:mac")
    expected_tag = hmac.new(
        mac_key,
        nonce + encrypted_bytes,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise InvalidCiphertextError("API Key 密文校验失败，请确认 APP_SECRET_KEY 正确。")

    enc_key = _derive_key(secret_key, "ai-chat-demo:enc")
    plaintext_bytes = _xor_bytes(
        encrypted_bytes,
        _build_keystream(enc_key, nonce, len(encrypted_bytes)),
    )
    return plaintext_bytes.decode("utf-8")
