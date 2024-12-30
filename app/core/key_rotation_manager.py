import redis
import structlog
from datetime import datetime, timedelta, timezone

from app.core.key_management import KeyManager

logger = structlog.get_logger()


class KeyRotationManager:
    def __init__(self, redis_client: redis.Redis, key_manager: KeyManager) -> None:
        self.redis = redis_client
        self.key_manager = key_manager
        self.rotation_interval = timedelta(days=1)
        self.rotation_lock_key = "key_rotation_lock"
        self.last_rotation_key = "last_key_rotation"

    async def check_and_rotate_keys(self) -> None:
        """Check if keys need to be rotated and rotate them if necessary."""
        lock_acquired = self.redis.set(
            self.rotation_lock_key,
            "1",
            ex=300,  # TODO: Move to settings
            nx=True,
        )

        if not lock_acquired:
            return

        try:
            last_rotation = await self.redis.get(self.last_rotation_key)
            if last_rotation:
                last_rotation_time = datetime.fromisoformat(last_rotation.decode())
                if (
                    datetime.now(timezone.utc) - last_rotation_time
                    < self.rotation_interval
                ):
                    return

            self.key_manager.rotate_keys()

            await self.redis.set(
                self.last_rotation_key,
                datetime.now(timezone.utc).isoformat(),
            )

            logger.info("key_rotation_check_complete")
        finally:
            await self.redis.delete(self.rotation_lock_key)
