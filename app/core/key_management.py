import base64
import structlog
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timezone

from app.core.secrets import VaultClient
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class KeyManager:
    def __init__(self, vault_client: VaultClient) -> None:
        self.vault_client = vault_client
        self.mount_point = settings.VAULT_MOUNT_POINT
        self.active_key_path = "active_rsa_key"  # TODO: Move to settings
        self.key_prefix = "rsa_key_"  # TODO: Move to settings

    @staticmethod
    def generate_key_pair() -> (bytes, bytes):
        """Generate a new RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),  # TODO: Add encryption
        )

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    def rotate_keys(self) -> None:
        """Generate and store a new RSA key pair"""
        try:
            private_pem, public_pem = self.generate_key_pair()

            key_id = f"{int(time.time())}"

            self.vault_client.client.secrets.kv.v2.create_or_update_secret(
                path=f"{self.key_prefix}{key_id}",
                secret={
                    "private_key": base64.b64encode(private_pem).decode("utf-8"),
                    "public_key": base64.b64encode(public_pem).decode("utf-8"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                mount_point=self.mount_point,
            )

            self.vault_client.client.secrets.kv.v2.create_or_update_secret(
                path=self.active_key_path,
                secret={"active_key_id": key_id},
                mount_point=self.mount_point,
            )

            logger.info("key_rotation_successful", key_id=key_id)
            return key_id
        except Exception as e:
            logger.error("key_rotation_failed", error=str(e))
            raise

    def get_active_key(self) -> dict[str, bytes]:
        """Get the currently active key pair"""
        try:
            active_key_data = (
                self.vault_client.client.secrets.kv.v2.read_secret_version(
                    path=self.active_key_path, mount_point=self.mount_point
                )
            )
            active_key_id = active_key_data["data"]["data"]["active_key_id"]

            key_data = self.vault_client.client.secrets.kv.v2.read_secret_version(
                path=f"{self.key_prefix}{active_key_id}", mount_point=self.mount_point
            )

            return {
                "private_key": base64.b64decode(
                    key_data["data"]["data"]["private_key"]
                ),
                "public_key": base64.b64decode(key_data["data"]["data"]["public_key"]),
            }
        except Exception as e:
            logger.error("get_active_keys_failed", error=str(e))
            raise

    def initialize_if_needed(self):
        # noinspection PyBroadException
        try:
            self.vault_client.client.secrets.kv.v2.read_secret_version(
                path=self.active_key_path, mount_point=self.mount_point
            )
        except Exception:
            logger.info("initializing_new_key_pair")
            self.rotate_keys()
