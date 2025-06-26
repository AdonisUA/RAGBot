#!/usr/bin/env python3
"""
Development server runner for AI ChatBot Backend
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

if __name__ == "__main__":
    # Change to backend directory
    os.chdir(backend_path)

    # Run the server
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
