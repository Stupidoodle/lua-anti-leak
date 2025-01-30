import base64

import aiofiles
import asyncio
import json
import redis
import time
from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Depends

from app.core.secrets import get_vault_client, TokenManager
from app.core.config import get_settings
from app.utils.chunking_utils import chunk_lua_script, refresh_chunks
from app.utils.crypto_utils import encrypt_aes_gcm, sign_data
from app.utils.encryption_utils import mock_encrypt

router = APIRouter()
settings = get_settings()
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

chunked_script_length: int = 0


def get_token_manager() -> TokenManager:
    vault_client = get_vault_client()
    return TokenManager(vault_client)


@router.get("/script_chunk/{chunk_index}")
def get_script_chunk(
    chunk_index: int,
    token: str = Query(...),
    token_manager: TokenManager = Depends(get_token_manager),
):
    global chunked_script_length
    token_manager.verify_token(token)

    ephemeral_key = r.get(f"ephemeral:{token}")
    if not ephemeral_key:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    if chunked_script_length == 0:
        raise HTTPException(status_code=404, detail="Script not available")

    if chunk_index < 0 or chunk_index >= chunked_script_length:
        raise HTTPException(status_code=404, detail="Chunk not found")

    time_window = int(time.time()) // 60
    metadata_key = f"chunk_metadata:{time_window}"
    metadata = r.get(metadata_key)

    if not metadata:
        raise HTTPException(status_code=404, detail="Chunks not available or expired")

    metadata = json.loads(metadata)
    chunk_key = metadata["chunks"].get(str(chunk_index))

    if not chunk_key:
        raise HTTPException(status_code=404, detail="Chunk {chunk_index} not found")

    raw_chunk = r.get(chunk_key)

    encrypted_chunk = mock_encrypt(raw_chunk)

    if isinstance(encrypted_chunk, str):
        chunk_bytes = encrypted_chunk.encode("utf-8")
    else:
        chunk_bytes = encrypted_chunk

    encrypted_data = encrypt_aes_gcm(chunk_bytes, ephemeral_key)

    combined_for_signing = base64.b64decode(
        encrypted_data["nonce"]
    ) + base64.b64decode(encrypted_data["ciphertext"])
    signature_b64 = sign_data(combined_for_signing)

    return {
        "nonce": encrypted_data["nonce"],
        "ciphertext": encrypted_data["ciphertext"],
        "signature": signature_b64,
    }


# FIXME
@router.on_event("startup")
async def startup_event() -> None:
    global chunked_script_length
    try:
        async with aiofiles.open(
            "app/assets/private_script.lua", mode="r"
        ) as lua_file:
            lua_script = await lua_file.read()
            chunk_size = 10
            interval = 60
            chunks = await chunk_lua_script(lua_script, chunk_size)
            chunked_script_length = len(chunks)
            asyncio.create_task(refresh_chunks(chunks, interval))
    except Exception as e:
        print(f"Error during startup: {e}")
