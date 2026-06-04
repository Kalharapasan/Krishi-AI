import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]


def _resolve_model_path() -> str:
    raw_path = os.getenv("LOCAL_MODEL_PATH", "model/best_plant_model.pth").strip().strip('"').strip("'")
    candidate_paths = []

    if raw_path:
        raw_candidate = Path(raw_path)
        candidate_paths.append(raw_candidate)

        if raw_candidate.is_absolute():
            candidate_paths.append(BASE_DIR / raw_candidate.as_posix().lstrip("/\\"))
        else:
            candidate_paths.append(BASE_DIR / raw_candidate)

    candidate_paths.extend(
        [
            BASE_DIR / "model" / "best_plant_model.pth",
            BASE_DIR / "model" / "latest_model.pth",
        ]
    )

    for candidate in candidate_paths:
        if candidate.exists():
            return str(candidate)

    return str(BASE_DIR / "model" / "best_plant_model.pth")

class Settings:
    PROJECT_NAME = os.getenv("PROJECT_NAME", "Krishi AI Advanced Backend")

    # Storage & Database
    DATABASE_URL    = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/krishi_db")
    LOCAL_MODEL_PATH = _resolve_model_path()

    # Security
    TRAINING_API_KEY = os.getenv("TRAINING_API_KEY", "krishi_secure_api_key_2026")

    # ML Model Config
    NUM_CLASSES = int(os.getenv("NUM_CLASSES", "38"))
    # If true, skip expensive Grad-CAM heatmap generation to speed up inference
    SKIP_HEATMAP = os.getenv("SKIP_HEATMAP", "false").lower() in ("1", "true", "yes")

    # ✅ FIXED: All 38 real PlantVillage dataset class names (alphabetical order,
    # matching datasets.ImageFolder which sorts folder names alphabetically).
    # These MUST match the class folders in the Kaggle dataset exactly.
    CLASS_NAMES = [
        "Apple___Apple_scab",
        "Apple___Black_rot",
        "Apple___Cedar_apple_rust",
        "Apple___healthy",
        "Blueberry___healthy",
        "Cherry_(including_sour)___Powdery_mildew",
        "Cherry_(including_sour)___healthy",
        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
        "Corn_(maize)___Common_rust_",
        "Corn_(maize)___Northern_Leaf_Blight",
        "Corn_(maize)___healthy",
        "Grape___Black_rot",
        "Grape___Esca_(Black_Measles)",
        "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
        "Grape___healthy",
        "Orange___Haunglongbing_(Citrus_greening)",
        "Peach___Bacterial_spot",
        "Peach___healthy",
        "Pepper,_bell___Bacterial_spot",
        "Pepper,_bell___healthy",
        "Potato___Early_blight",
        "Potato___Late_blight",
        "Potato___healthy",
        "Raspberry___healthy",
        "Soybean___healthy",
        "Squash___Powdery_mildew",
        "Strawberry___Leaf_scorch",
        "Strawberry___healthy",
        "Tomato___Bacterial_spot",
        "Tomato___Early_blight",
        "Tomato___Late_blight",
        "Tomato___Leaf_Mold",
        "Tomato___Septoria_leaf_spot",
        "Tomato___Spider_mites Two-spotted_spider_mite",
        "Tomato___Target_Spot",
        "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
        "Tomato___Tomato_mosaic_virus",
        "Tomato___healthy",
    ]

settings = Settings()
