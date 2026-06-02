import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torchvision import models, transforms
import cv2
from sklearn.preprocessing import LabelEncoder
from torchvision import datasets
from torch.utils.data import DataLoader, ConcatDataset
import requests
import zipfile

# ==============================================================================
# 1. Connect to Local Backend to Get Live Data (Continuous Learning)
# ==============================================================================
# IMPORTANT: Start your local backend and use Ngrok to get a public URL.
BACKEND_URL = "http://YOUR_NGROK_URL/api" 
API_KEY = "my_super_secret_key_123" # Must match backend config.py

print(f"Connecting to Local Backend at {BACKEND_URL}...")
live_data_dir = './live_data'
headers = {"x-api-key": API_KEY}

try:
    response = requests.get(f"{BACKEND_URL}/export-data", headers=headers)
    if response.status_code == 200:
        with open("verified_data.zip", "wb") as f:
            f.write(response.content)
        with zipfile.ZipFile("verified_data.zip", 'r') as zip_ref:
            zip_ref.extractall(live_data_dir)
        print("Successfully downloaded user-verified data from Local Backend!")
    else:
        print("No new verified data available on backend.")
except Exception as e:
    print(f"Could not connect to backend: {e}")

# ==============================================================================
# 2. Model Architecture
# ==============================================================================
class PlantDiseaseClassifier(nn.Module):
    def __init__(self, num_classes=38):
        super().__init__()
        
        # Load pre-trained EfficientNet-B0 backbone
        self.model = models.efficientnet_b0(weights='DEFAULT')

        # Get the input dimension of the original classifier's linear layer
        in_features = self.model.classifier[1].in_features

        # Replace the original classifier with an Identity layer 
        self.model.classifier = nn.Identity()

        # Custom Multi-layer Perceptron (MLP) for plant disease classification
        self.fc1 = nn.Linear(in_features, 512)
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(0.4)

        self.fc2 = nn.Linear(512, 128)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(0.3)

        self.fc3 = nn.Linear(128, num_classes)

    def forward(self, x):
        # Extract features using the EfficientNet backbone
        x = self.model(x)
        
        # Pass features through the custom classifier head
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.drop1(x)

        x = self.fc2(x)
        x = self.relu2(x)
        x = self.drop2(x)

        x = self.fc3(x)
        return x

# ==============================================================================
# 3. Data Transformations
# ==============================================================================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# ==============================================================================
# 4. Data Loading and Setup
# ==============================================================================
# Fallback mechanism: Check if Kaggle paths exist, otherwise download via kagglehub (for Colab)
train_path = '/kaggle/input/datasets/vipoooool/new-plant-diseases-dataset/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/train'
val_path = '/kaggle/input/datasets/vipoooool/new-plant-diseases-dataset/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/valid'

if not os.path.exists(train_path):
    print("Kaggle path not found. Downloading dataset via kagglehub...")
    import kagglehub
    dataset_path = kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset")
    train_path = os.path.join(dataset_path, "New Plant Diseases Dataset(Augmented)", "New Plant Diseases Dataset(Augmented)", "train")
    val_path = os.path.join(dataset_path, "New Plant Diseases Dataset(Augmented)", "New Plant Diseases Dataset(Augmented)", "valid")

train_dataset = datasets.ImageFolder(root=train_path, transform=transform)
val_dataset = datasets.ImageFolder(root=val_path, transform=transform)

# Merge with live data if available
try:
    if os.path.exists(live_data_dir) and len(os.listdir(live_data_dir)) > 0:
        live_dataset = datasets.ImageFolder(live_data_dir, transform=transform)
        full_train_dataset = ConcatDataset([train_dataset, live_dataset])
        print("Merged Kaggle Data + Backend Live Data!")
    else:
        full_train_dataset = train_dataset
except Exception:
    full_train_dataset = train_dataset

train_loader = DataLoader(full_train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

class_names = train_dataset.classes

# ==============================================================================
# 5. Training Setup and Execution
# ==============================================================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = PlantDiseaseClassifier(num_classes=len(class_names)).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# --- Training Configuration ---
epochs = 50
patience = 5  
best_val_loss = float('inf')
counter = 0

for epoch in range(epochs):
    # --- Training Phase ---
    model.train()  
    train_loss = 0.0
    train_correct = 0 
    
    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item() * images.size(0)
        _, train_predicted = torch.max(outputs, 1)
        train_correct += (train_predicted == labels).sum().item()
    
    # --- Validation Phase ---
    model.eval()  
    val_loss = 0.0
    val_correct = 0 
    
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            val_loss += loss.item() * images.size(0)
            _, val_predicted = torch.max(outputs, 1)
            val_correct += (val_predicted == labels).sum().item()

    # --- Metrics Calculation ---
    avg_train_loss = train_loss / len(train_loader.dataset)
    avg_val_loss = val_loss / len(val_loader.dataset)
    
    train_acc = train_correct / len(train_loader.dataset)
    val_acc = val_correct / len(val_loader.dataset)

    print(f'Epoch {epoch+1}/{epochs}:')
    print(f'Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc:.4f}')
    print(f'Val Loss:   {avg_val_loss:.4f} | Val Acc:   {val_acc:.4f}')

    # --- Early Stopping & Model Checkpointing ---
    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        torch.save(model.state_dict(), 'best_plant_model.pth')
        print("✅ New best model saved!")
        counter = 0 
    else:
        counter += 1
        print(f"⚠️ No improvement. EarlyStopping counter: {counter}/{patience}")
        
        if counter >= patience:
            print("🛑 Early stopping triggered. Training terminated.")
            break
    print('-' * 30)

# ==============================================================================
# 6. Upload Model back to Backend
# ==============================================================================
print("Sending best model directly to Local Backend...")
try:
    with open('best_plant_model.pth', 'rb') as f:
        files = {'file': ('latest_model.pth', f, 'application/octet-stream')}
        res = requests.post(f"{BACKEND_URL}/upload-model", headers=headers, files=files)
        print("Backend Response:", res.json())
        print("SUCCESS! The backend is now using the newly trained model.")
except Exception as e:
    print(f"Failed to upload model to backend: {e}")

# ==============================================================================
# 7. Test the Updated Backend API
# ==============================================================================
print("\nTesting the newly updated Backend API with a sample image...")
try:
    import glob
    # Find a sample image in the validation directory
    sample_images = glob.glob(os.path.join(val_path, "*", "*.jpg")) + glob.glob(os.path.join(val_path, "*", "*.JPG"))
    if sample_images:
        test_img_path = sample_images[0]
        print(f"Sending test image to API: {test_img_path}")
        with open(test_img_path, 'rb') as f:
            files = {'file': ('test_image.jpg', f, 'image/jpeg')}
            res = requests.post(f"{BACKEND_URL}/diagnose", files=files)
            if res.status_code == 200:
                print("API Diagnosis Result:", res.json())
            else:
                print(f"API Error: {res.status_code} - {res.text}")
    else:
        print("No sample images found for testing.")
except Exception as e:
    print(f"API Test failed: {e}")
