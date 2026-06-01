import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router
from app.services.ml_service import load_model
from app.config import settings

from app.database import init_db