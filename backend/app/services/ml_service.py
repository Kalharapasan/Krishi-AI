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

class PlantDiseaseClassifier(nn.Module):
    def __init__(self, num_classes=38):
        super().__init__()
        self.model = models.efficientnet_b0(weights=None)
        in_features = self.model.classifier[1].in_features
        self.model.classifier = nn.Identity()

        self.fc1 = nn.Linear(in_features, 512)
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(0.4)

        self.fc2 = nn.Linear(512, 128)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(0.3)

        self.fc3 = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.model(x)
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.drop1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.drop2(x)
        x = self.fc3(x)
        return x

def load_model():
    global model
    print("Loading PyTorch model into memory...")
    try:
        pytorch_model = PlantDiseaseClassifier(num_classes=settings.NUM_CLASSES)
        state_dict = torch.load(settings.LOCAL_MODEL_PATH, map_location=device)
        pytorch_model.load_state_dict(state_dict)
        pytorch_model.to(device)
        pytorch_model.eval()
        
        model = pytorch_model
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
    
def predict(image_bytes: bytes):
    if model is None:
        raise RuntimeError("Model is not loaded. Please upload a model or check logs.")
        
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    # 1. Standard Inference
    with torch.no_grad():
        outputs = model(input_tensor)
        _, predicted_idx = torch.max(outputs, 1)
        confidence = torch.nn.functional.softmax(outputs, dim=1)[0][predicted_idx].item()
        
    disease_name = settings.CLASS_NAMES[predicted_idx.item()] if predicted_idx.item() < len(settings.CLASS_NAMES) else f"Unknown ({predicted_idx.item()})"
    
    # 2. Explainable AI (Grad-CAM)
    heatmap_base64 = None
    try:
        from pytorch_grad_cam import GradCAM
        from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
        from pytorch_grad_cam.utils.image import show_cam_on_image
        
        # Target the last convolutional layer of EfficientNet
        target_layers = [model.model.features[-1]]
        cam = GradCAM(model=model, target_layers=target_layers)
        targets = [ClassifierOutputTarget(predicted_idx.item())]
        
        grayscale_cam = cam(input_tensor=input_tensor, targets=targets)
        grayscale_cam = grayscale_cam[0, :]
        
        # Resize original image to match tensor size (224x224) and normalize [0, 1]
        rgb_img = np.float32(image.resize((224, 224))) / 255
        cam_image = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
        
        # Encode as Base64 JPEG
        cam_pil = Image.fromarray(cam_image)
        buffered = io.BytesIO()
        cam_pil.save(buffered, format="JPEG")
        heatmap_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    except Exception as e:
        print(f"Grad-CAM generation failed: {e}")
        
    return disease_name, round(confidence * 100, 2), heatmap_base64