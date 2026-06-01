import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router
from app.services.ml_service import load_model
from app.config import settings

from app.database import init_db


app = FastAPI(
    title="Krishi AI Backend API",
    description="Backend for crop disease diagnosis using Advanced PyTorch Continuous Learning.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
