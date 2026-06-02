import os
from fastapi import FastAPI, Header, HTTPException
from contextlib import asynccontextmanager
from app.api.routes import router
from app.api.routes import export_verified_data, verify_colab_key
from app.services.ml_service import load_model
from app.config import settings

from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Krishi AI Backend...")
    init_db() # Initialize the PostgreSQL database
    
    # Load model into memory
    if os.path.exists(settings.LOCAL_MODEL_PATH):
        load_model()
    else:
        print("WARNING: Model file not found. Inference will fail until a model is uploaded from Colab.")
        
    yield
    
    # Shutdown
    print("Shutting down Krishi AI Backend...")

app = FastAPI(
    title="Krishi AI Backend API",
    description="Backend for crop disease diagnosis using Advanced PyTorch Continuous Learning.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(router, prefix="/api")


@app.get("/export-data")
def export_data_alias(x_api_key: str = Header(...)):
    verify_colab_key(x_api_key)
    return export_verified_data()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
