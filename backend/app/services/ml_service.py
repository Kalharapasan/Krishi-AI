import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from app.config import settings
import io
import base64
import numpy as np
import cv2

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None

# Preprocessing transforms (Must match training!)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])