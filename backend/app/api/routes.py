from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from app.services.ml_service import predict, load_model
from app.database import save_diagnosis, update_feedback, get_image_path
from app.config import settings
import os
import shutil
import uuid

router = APIRouter()

# Security dependency for Colab connection
def verify_colab_key(x_api_key: str = Header(...)):
    if x_api_key != settings.TRAINING_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# Directories for storing images
os.makedirs("data/raw",      exist_ok=True)
os.makedirs("data/verified", exist_ok=True)


@router.post("/diagnose")
async def diagnose_crop(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    try:
        image_bytes = await file.read()

        import asyncio
        disease_name, confidence, heatmap_base64 = await asyncio.to_thread(predict, image_bytes)

        filename = f"{uuid.uuid4()}.jpg"
        filepath = f"data/raw/{filename}"
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        record_id = save_diagnosis(filepath, disease_name, confidence)

        return {
            "id":         record_id,
            "disease":    disease_name,
            "confidence": confidence,
            "heatmap":    heatmap_base64,
            "message":    "Diagnosis complete."
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/feedback")
async def submit_feedback(record_id: int = Form(...), correct_disease: str = Form(...)):
    # ✅ FIXED: use get_image_path() from database module (no inline psycopg2 here)
    update_feedback(record_id, correct_disease)

    image_path = get_image_path(record_id)
    if image_path and os.path.exists(image_path):
        filename  = os.path.basename(image_path)
        disease_dir = os.path.join("data/verified", correct_disease)
        os.makedirs(disease_dir, exist_ok=True)
        shutil.move(image_path, os.path.join(disease_dir, filename))

    return {"status": "success", "message": "Feedback saved for continuous learning."}


@router.get("/export-data", dependencies=[Depends(verify_colab_key)])
def export_verified_data():
    """Colab calls this to download verified images directly from the backend."""
    if not os.path.exists("data/verified") or not os.listdir("data/verified"):
        raise HTTPException(status_code=404, detail="No verified data available yet.")

    shutil.make_archive("verified_data", 'zip', "data/verified")
    return FileResponse("verified_data.zip", media_type="application/zip",
                        filename="verified_data.zip")


@router.post("/upload-model", dependencies=[Depends(verify_colab_key)])
async def upload_new_model(file: UploadFile = File(...)):
    """Colab (or manual upload) sends the newly trained model; backend reloads it instantly."""
    if not file.filename.endswith('.pth'):
        raise HTTPException(status_code=400, detail="Must be a .pth file")

    with open(settings.LOCAL_MODEL_PATH, "wb") as f:
        f.write(await file.read())

    load_model()
    return {"status": "success", "message": "Model uploaded and reloaded successfully!"}


@router.get("/health")
def health_check():
    from app.services import ml_service
    model_loaded = ml_service.model is not None
    return {
        "status":       "ok",
        "model_loaded": model_loaded,
        "message":      "Krishi AI backend is running." if model_loaded
                        else "Backend running but model not loaded — upload a model first."
    }
