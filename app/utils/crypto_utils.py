import os
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import get_settings
from app.core.secrets import get_vault_client
from app.core.key_management import KeyManager

settings = get_settings()
key_manager = KeyManager(get_vault_client())


def generate_ephemeral_key() -> bytes:
    """Generates a random 32-bytes AES key (for AES-256)"""
    #  return AESGCM.generate_key(bit_length=256).decode()
    return os.urandom(32)


def encrypt_aes_gcm(plaintext: bytes, key: bytes) -> dict[str, str]:
    """
    Encrypts plaintext with AES-GCM. Returns a dict containing
    base64-encoded ciphertext, nonce, and tag (though cryptography
    puts the tag in the ciphertext).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


def sign_data(data: bytes) -> str:
    """
    Sign data with RSA private key using PKCS#1 v1.5 and SHA256.
    Return base64-encoded signature.
    """
    private_key, public_key = (
        serialization.load_pem_private_key(
            key_manager.get_active_key()["private_key"], password=None
        ),  # TODO: Add password
        serialization.load_pem_public_key(key_manager.get_active_key()["public_key"]),
    )

    signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def verify_signature(data: bytes, signature_b64: str) -> bool:
    """
    Verify signature with the public key. Not typically needed server-side,
    but included for reference.
    """
    private_key, public_key = (
        serialization.load_pem_private_key(
            key_manager.get_active_key()["private_key"], password=None
        ),  # TODO: Add password
        serialization.load_pem_public_key(key_manager.get_active_key()["public_key"]),
    )

    signature = base64.b64decode(signature_b64)
    # noinspection PyBroadException
    try:
        public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except:
        return False
