#!/usr/bin/env python3
"""
Development server runner for AI ChatBot Backend
"""

import uvicorn
import sys
import os
from pathlib import Path
from backend.app.core.config import get_settings

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

if __name__ == "__main__":
    # Change to backend directory
    os.chdir(backend_path)

    settings = get_settings()

    # Run the server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )
