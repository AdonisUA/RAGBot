print('MAIN_MINIMAL_LOADED')

from fastapi import FastAPI
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import chat

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Minimal app works!"}
