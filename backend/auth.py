import os
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

# Simple API key header dependency. Protect sensitive endpoints by requiring this key.
API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header_value: str = Security(api_key_header)) -> str:
    expected = os.environ.get("BACKEND_API_KEY")
    env = os.environ.get("ENV", "dev")
    if not expected:
        # Only allow unprotected in dev
        if env == "dev":
            return "dev-unprotected"
        raise HTTPException(status_code=500, detail="API key not configured on server")

    if not api_key_header_value or api_key_header_value != expected:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return api_key_header_value
