import asyncio
import json

import redis
import time
from random import shuffle

from app.core.config import get_settings
from app.core.logging_config import configure_logger

settings = get_settings()
logger = configure_logger()
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


async def chunk_lua_script(script: str, chunk_size: int) -> list[str]:
    """Split a Lua script into chunks of a given size."""
    lines = script.split("\n")
    chunks = []

    for i in range(0, len(lines), chunk_size):
        chunk = lines[i : i + chunk_size]
        chunk_header = f"-- chunk {len(chunks)}\n"
        chunks.append(chunk_header + "\n".join(chunk))

    return chunks


def update_chunks(chunks: list[str], time_window: int) -> None:
    """Update the Redis cache with the given chunks."""
    old_metadata_keys = r.keys("chunk_metadata:*")
    for metadata_key in old_metadata_keys:
        old_metadata = r.get(metadata_key)
        if old_metadata:
            old_metadata = json.loads(old_metadata)
            for chunk_key in old_metadata["chunks"].values():
                r.delete(chunk_key)  # Remove old chunk keys
            r.delete(metadata_key)  # Remove old metadata

    chunk_metadata = {
        "chunks": {},
        "order": [],
    }

    for idx, chunk in enumerate(chunks):
        chunk_key = f"chunk:{time_window}:{idx}"
        r.set(chunk_key, chunk, ex=120)  # Store new chunk with expiration
        chunk_metadata["chunks"][idx] = chunk_key
        chunk_metadata["order"].append(idx)

    shuffle(chunk_metadata["order"])

    r.set(f"chunk_metadata:{time_window}", json.dumps(chunk_metadata), ex=120)

    logger.info(
        f"Updated Redis with {len(chunks)} chunks for time window {time_window}"
    )


async def refresh_chunks(chunks: list[str], interval: int) -> None:
    """Refresh the chunks in the Redis cache at a given interval."""
    while True:
        time_window = int(time.time()) // 60
        update_chunks(chunks, time_window)
        logger.info(f"Chunks updated for time window: {time_window}")
        await asyncio.sleep(interval)
