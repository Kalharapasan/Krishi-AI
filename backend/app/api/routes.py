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

@router.post("/diagnose")
async def diagnose_crop(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    try:
        image_bytes = await file.read()
        
        # Perform Inference using local PyTorch model & generate heatmap
        import asyncio
        disease_name, confidence, heatmap_base64 = await asyncio.to_thread(predict, image_bytes)

        # Save image locally
        filename = f"{uuid.uuid4()}.jpg"
        filepath = f"data/raw/{filename}"
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        # Save to database
        record_id = save_diagnosis(filepath, disease_name, confidence)

        return {
            "id": record_id,
            "disease": disease_name,
            "confidence": confidence,
            "heatmap": heatmap_base64,
            "message": "Diagnosis complete."
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")