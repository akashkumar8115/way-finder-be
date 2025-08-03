import base64
import json
import secrets
from fastapi import FastAPI

app = FastAPI()

def obfuscate_response(data):
    """Simple obfuscation without encryption for debugging"""
    # Convert data to JSON string
    json_data = json.dumps(data)
    
    # Simple base64 encoding
    encoded_data = base64.b64encode(json_data.encode()).decode()
    
    response = {
        "status": "success",
        "timestamp": secrets.token_hex(8),
        "session": secrets.token_urlsafe(16),
        "payload": encoded_data,
        "meta": secrets.token_hex(12)
    }
    return response