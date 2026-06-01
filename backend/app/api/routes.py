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

@router.post("/feedback")
async def submit_feedback(record_id: int = Form(...), correct_disease: str = Form(...)):
    update_feedback(record_id, correct_disease)
    import psycopg2
    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT image_path FROM diagnosis_history WHERE id=%s", (record_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and os.path.exists(row[0]):
        old_path = row[0]
        filename = os.path.basename(old_path)
        disease_dir = os.path.join("data/verified", correct_disease)
        os.makedirs(disease_dir, exist_ok=True)
        new_path = os.path.join(disease_dir, filename)
        shutil.move(old_path, new_path)
        
    return {"status": "success", "message": "Feedback saved for continuous learning."}


@router.get("/export-data", dependencies=[Depends(verify_colab_key)])
def export_verified_data():
    """Colab calls this to download verified images directly from the backend."""
    if not os.path.exists("data/verified") or not os.listdir("data/verified"):
        raise HTTPException(status_code=404, detail="No verified data available yet.")
        
    shutil.make_archive("verified_data", 'zip', "data/verified")
    return FileResponse("verified_data.zip", media_type="application/zip", filename="verified_data.zip")

@router.post("/upload-model", dependencies=[Depends(verify_colab_key)])
async def upload_new_model(file: UploadFile = File(...)):
    """Colab calls this to upload the newly trained model, updating the backend instantly."""
    if not file.filename.endswith('.pth'):
        raise HTTPException(status_code=400, detail="Must be a .pth file")
        
    with open(settings.LOCAL_MODEL_PATH, "wb") as f:
        f.write(await file.read())
        
    load_model()
    return {"status": "success", "message": "Model successfully updated and reloaded in real time!"}