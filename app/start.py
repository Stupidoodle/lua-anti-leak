import uvicorn

from app.main import app
from app.core.secrets import get_vault_client

if __name__ == "__main__":
    vault_client = get_vault_client()
    vault_client.initialize()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
