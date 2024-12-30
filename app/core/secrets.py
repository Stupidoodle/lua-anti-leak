import hvac
import jwt
import os
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


class VaultClient:
    def __init__(self) -> None:
        self.client = hvac.Client(
            url=settings.VAULT_ADDRESS,
            token=settings.VAULT_TOKEN,
        )
        self.mount_point = settings.VAULT_MOUNT_POINT

    def initialize(self):
        """Initialize Vault with required secrets if they do not exist."""
        mounted_secrets_engines = self.client.sys.list_mounted_secrets_engines()

        if f"{self.mount_point}/" in mounted_secrets_engines:
            return

        if self.mount_point not in self.client.sys.list_mounted_secrets_engines():
            self.client.sys.enable_secrets_engine(
                backend_type="kv",
                path=self.mount_point,
                options={"version": "2"},
            )

        secrets = {
            "jwt_secret": Fernet.generate_key().decode(),
            "master_sym_key": Fernet.generate_key().decode(),
        }

        for key, value in secrets.items():
            try:
                self.client.secrets.kv.v2.read_secret_version(
                    path=key,
                    mount_point=self.mount_point,
                )
            except hvac.exceptions.InvalidPath:
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=key,
                    mount_point=self.mount_point,
                    secret=dict(value=value),
                )

    def get_secret(self, key: str) -> str:
        """Retrieve a secret from Vault."""
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount_point,
            )
            return secret["data"]["data"]["value"]
        except Exception as e:
            raise Exception(f"Failed to retrieve secret {key}: {str(e)}")


@lru_cache()
def get_vault_client() -> VaultClient:
    client = VaultClient()
    client.initialize()
    return client


class TokenManager:
    def __init__(self, vault_client: VaultClient) -> None:
        self.vault_client = vault_client

    def create_token(
        self, user_id: int, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT token for the given user_id."""
        jwt_secret = self.vault_client.get_secret("jwt_secret")

        if not expires_delta:
            expires_delta = timedelta(minutes=settings.JWT_EXPIRATION)

        expires = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            "uid": user_id,
            "exp": expires,
        }

        return jwt.encode(to_encode, jwt_secret, algorithm=settings.JWT_ALGORITHM)

    def verify_token(self, token: str) -> dict:
        """Verify the JWT token and return the payload."""
        jwt_secret = self.vault_client.get_secret("jwt_secret")

        try:
            payload = jwt.decode(
                token, jwt_secret, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.JWTError:
            raise Exception("Invalid token")
