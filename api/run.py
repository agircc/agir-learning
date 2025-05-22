#!/usr/bin/env python3
"""
Run the AGIR API server
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("API_PORT", 8000))
    
    print(f"Starting AGIR API server on port {port}...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True) 