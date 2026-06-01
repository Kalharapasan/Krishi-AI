from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from app.services.ml_service import predict, load_model
from app.database import save_diagnosis, update_feedback
from app.config import settings
import os
import shutil
import uuid
import sqlite3

router = APIRouter()

# Security dependency for Colab connection
def verify_colab_key(x_api_key: str = Header(...)):
    if x_api_key != settings.TRAINING_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# Directories for storing images
os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/verified", exist_ok=True)