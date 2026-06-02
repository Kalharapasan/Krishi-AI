"""
Krishi AI - Google Colab Training Script
=========================================
INSTRUCTIONS (run these steps in order):
  1. Open this in Google Colab (Runtime > Change runtime type > GPU)
  2. Run Cell 0 to install dependencies
  3. Paste your Ngrok URL in BACKEND_URL (optional - only needed for continuous learning)
  4. Run all cells - the model trains, saves to Google Drive, and uploads to backend
"""

# ==============================================================================
# CELL 0: Install Dependencies  ← RUN THIS FIRST!
# ==============================================================================
# Paste this into the first Colab cell and run it:
#
# !pip install kagglehub torch torchvision pillow opencv-python-headless requests

# ==============================================================================
# CELL 1: Imports
# ==============================================================================
import os
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader, ConcatDataset
import requests
import zipfile

# ==============================================================================
# CELL 2: Configuration  ← SET YOUR NGROK URL HERE (optional)
# ==============================================================================
# STEP 1: Start your backend locally and expose it with Ngrok:
#   ngrok http 8000
#   Then paste the URL below, e.g.: "https://abc123.ngrok-free.app/api"
#
# STEP 2: The API key MUST match TRAINING_API_KEY in your backend/.env file
#   Current backend key: "krishi_secure_api_key_2026"

BACKEND_URL = "http://YOUR_NGROK_URL/api"   # Replace with real Ngrok URL, or leave to skip
API_KEY = "krishi_secure_api_key_2026"       # ✅ FIXED: matches backend/.env

# Google Drive path to save the trained model (so it persists after Colab session ends)
GDRIVE_SAVE_PATH = "/content/drive/MyDrive/krishi_ai_models/best_plant_model.pth"
LOCAL_MODEL_PATH = "best_plant_model.pth"

# ==============================================================================
# CELL 3: Mount Google Drive (to save model permanently)
# ==============================================================================
try:
    from google.colab import drive
    drive.mount('/content/drive')
    os.makedirs(os.path.dirname(GDRIVE_SAVE_PATH), exist_ok=True)
    print("✅ Google Drive mounted. Model will be saved to:", GDRIVE_SAVE_PATH)
    USE_GDRIVE = True
except Exception as e:
    print(f"⚠️  Google Drive not mounted: {e}")
    print("    Model will only be saved locally (lost when session ends).")
    USE_GDRIVE = False

# ==============================================================================
# CELL 4: Optional - Download verified data from backend (Continuous Learning)
# ==============================================================================
live_data_dir = './live_data'
headers = {"x-api-key": API_KEY}

if BACKEND_URL != "http://YOUR_NGROK_URL/api":
    print(f"Connecting to backend at {BACKEND_URL} ...")
    try:
        response = requests.get(f"{BACKEND_URL}/export-data", headers=headers, timeout=30)
        if response.status_code == 200:
            with open("verified_data.zip", "wb") as f:
                f.write(response.content)
            with zipfile.ZipFile("verified_data.zip", 'r') as zip_ref:
                zip_ref.extractall(live_data_dir)
            print("✅ Downloaded user-verified data from backend!")
        elif response.status_code == 404:
            print("ℹ️  No verified data on backend yet — training with Kaggle data only.")
        else:
            print(f"⚠️  Backend returned {response.status_code}. Training with Kaggle data only.")
    except Exception as e:
        print(f"⚠️  Could not connect to backend: {e}\n    Training with Kaggle data only.")
else:
    print("ℹ️  No backend URL set. Skipping live data download.")

# ==============================================================================
# CELL 5: Model Architecture (EfficientNet-B0 + custom head)
# ==============================================================================
class PlantDiseaseClassifier(nn.Module):
    def __init__(self, num_classes=38):
        super().__init__()
        self.model = models.efficientnet_b0(weights='DEFAULT')
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
        x = self.fc1(x);  x = self.relu1(x);  x = self.drop1(x)
        x = self.fc2(x);  x = self.relu2(x);  x = self.drop2(x)
        x = self.fc3(x)
        return x

# ==============================================================================
# CELL 6: Data Transforms & Download Dataset
# ==============================================================================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# ✅ FIXED: Install kagglehub first (Cell 0), then download automatically in Colab
print("Downloading Plant Disease Dataset from Kaggle...")
try:
    import kagglehub
    dataset_path = kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset")
    print(f"✅ Dataset downloaded to: {dataset_path}")
except ImportError:
    raise RuntimeError(
        "❌ kagglehub not installed!\n"
        "Run this in a Colab cell first:\n"
        "  !pip install kagglehub\n"
        "Then restart the runtime and run again."
    )
except Exception as e:
    raise RuntimeError(f"❌ Failed to download dataset: {e}")

# Build paths (handles different kagglehub cache structures)
base = dataset_path
for root, dirs, files in os.walk(base):
    if "train" in dirs and "valid" in dirs:
        train_path = os.path.join(root, "train")
        val_path   = os.path.join(root, "valid")
        break
else:
    # Fallback: search one level deeper
    augmented = os.path.join(base, "New Plant Diseases Dataset(Augmented)", "New Plant Diseases Dataset(Augmented)")
    train_path = os.path.join(augmented, "train")
    val_path   = os.path.join(augmented, "valid")

print(f"Train path: {train_path}")
print(f"Valid path: {val_path}")
assert os.path.exists(train_path), f"Train path not found: {train_path}"
assert os.path.exists(val_path),   f"Val path not found: {val_path}"

train_dataset = datasets.ImageFolder(root=train_path, transform=transform)
val_dataset   = datasets.ImageFolder(root=val_path,   transform=transform)
class_names   = train_dataset.classes
print(f"✅ Found {len(class_names)} classes, {len(train_dataset)} training images.")

# Merge with live verified data if available
try:
    if os.path.exists(live_data_dir) and len(os.listdir(live_data_dir)) > 0:
        live_dataset = datasets.ImageFolder(live_data_dir, transform=transform)
        full_train_dataset = ConcatDataset([train_dataset, live_dataset])
        print(f"✅ Merged Kaggle data + {len(live_dataset)} backend verified images!")
    else:
        full_train_dataset = train_dataset
        print("ℹ️  No live data to merge. Training on Kaggle data only.")
except Exception as e:
    print(f"⚠️  Could not load live data: {e}")
    full_train_dataset = train_dataset

train_loader = DataLoader(full_train_dataset, batch_size=32, shuffle=True,  num_workers=2)
val_loader   = DataLoader(val_dataset,         batch_size=32, shuffle=False, num_workers=2)

# Print class names so you can copy them into backend/app/config.py
print("\n📋 CLASS NAMES (copy these into backend/app/config.py → CLASS_NAMES):\n")
print(class_names)

# ==============================================================================
# CELL 7: Training
# ==============================================================================
device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\n🖥️  Training on: {device}")
if device.type == "cpu":
    print("⚠️  WARNING: No GPU detected! Training will be very slow.")
    print("   Go to Runtime > Change runtime type > GPU (T4)")

model     = PlantDiseaseClassifier(num_classes=len(class_names)).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

epochs       = 50
patience     = 5
best_val_loss = float('inf')
counter      = 0

for epoch in range(epochs):
    # --- Training phase ---
    model.train()
    train_loss = train_correct = 0

    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        train_loss    += loss.item() * images.size(0)
        _, predicted   = torch.max(outputs, 1)
        train_correct += (predicted == labels).sum().item()

    # --- Validation phase ---
    model.eval()
    val_loss = val_correct = 0

    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss     = criterion(outputs, labels)
            val_loss    += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            val_correct += (predicted == labels).sum().item()

    avg_train_loss = train_loss / len(train_loader.dataset)
    avg_val_loss   = val_loss   / len(val_loader.dataset)
    train_acc      = train_correct / len(train_loader.dataset)
    val_acc        = val_correct   / len(val_loader.dataset)

    print(f"Epoch {epoch+1}/{epochs} | "
          f"Train Loss: {avg_train_loss:.4f} Acc: {train_acc:.4f} | "
          f"Val Loss: {avg_val_loss:.4f} Acc: {val_acc:.4f}")

    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        # ✅ Save locally
        torch.save(model.state_dict(), LOCAL_MODEL_PATH)
        # ✅ FIXED: Also save to Google Drive so model persists after session
        if USE_GDRIVE:
            torch.save(model.state_dict(), GDRIVE_SAVE_PATH)
            print(f"  ✅ Best model saved locally + to Google Drive!")
        else:
            print(f"  ✅ Best model saved locally!")
        counter = 0
    else:
        counter += 1
        print(f"  ⚠️  No improvement. EarlyStopping: {counter}/{patience}")
        if counter >= patience:
            print("  🛑 Early stopping triggered.")
            break

    print('-' * 60)

print(f"\n🏆 Training complete! Best val loss: {best_val_loss:.4f}")

# ==============================================================================
# CELL 8: Upload Model to Backend (optional - only if Ngrok URL is set)
# ==============================================================================
if BACKEND_URL != "http://YOUR_NGROK_URL/api":
    print("\nUploading model to backend...")
    try:
        with open(LOCAL_MODEL_PATH, 'rb') as f:
            files = {'file': ('latest_model.pth', f, 'application/octet-stream')}
            res = requests.post(
                f"{BACKEND_URL}/upload-model",
                headers=headers,
                files=files,
                timeout=120
            )
        if res.status_code == 200:
            print("✅ Model uploaded to backend successfully!")
            print("   Backend response:", res.json())
        else:
            print(f"❌ Upload failed: {res.status_code} - {res.text}")
            print(f"   You can manually upload the model file: {LOCAL_MODEL_PATH}")
            if USE_GDRIVE:
                print(f"   Or from Google Drive: {GDRIVE_SAVE_PATH}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        print(f"   Manually download the model from: {LOCAL_MODEL_PATH}")
        if USE_GDRIVE:
            print(f"   Or from Google Drive: {GDRIVE_SAVE_PATH}")
else:
    print("\nℹ️  No backend URL set. Model NOT uploaded to backend.")
    print(f"   Download the model from Google Drive: {GDRIVE_SAVE_PATH}")
    print("   Then upload it manually via the backend /api/upload-model endpoint.")

# ==============================================================================
# CELL 9: Quick test on a sample validation image
# ==============================================================================
print("\n🔍 Quick local inference test...")
try:
    import glob
    from PIL import Image
    import io

    sample_images = (
        glob.glob(os.path.join(val_path, "*", "*.jpg")) +
        glob.glob(os.path.join(val_path, "*", "*.JPG")) +
        glob.glob(os.path.join(val_path, "*", "*.png"))
    )
    if sample_images:
        test_img = Image.open(sample_images[0]).convert("RGB")
        tensor   = transform(test_img).unsqueeze(0).to(device)
        model.eval()
        with torch.no_grad():
            out  = model(tensor)
            prob = torch.nn.functional.softmax(out, dim=1)
            idx  = prob.argmax().item()
        print(f"✅ Test image: {os.path.basename(sample_images[0])}")
        print(f"   Predicted: {class_names[idx]} ({prob[0][idx].item()*100:.1f}% confidence)")
    else:
        print("No sample images found for testing.")
except Exception as e:
    print(f"Test failed: {e}")
