import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME = os.getenv("PROJECT_NAME", "Krishi AI Advanced Backend")
    
    # Storage & Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/krishi_db")
    LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "latest_model.pth")
    
    # Security
    TRAINING_API_KEY = os.getenv("TRAINING_API_KEY", "fallback_secret_key_123")
    
    # ML Model Config
    NUM_CLASSES = int(os.getenv("NUM_CLASSES", "38"))
    
    # NOTE: You will need to populate this list with the actual 38 class names!
    CLASS_NAMES = ["Healthy", "Apple Scab", "Rice Leaf Smut", "Tomato Blight", "Unknown"] * 8

settings = Settings()