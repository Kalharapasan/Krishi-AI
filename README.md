# Krishi AI

Krishi AI is a plant disease diagnosis project with a Flutter mobile app and a FastAPI backend powered by a PyTorch model. The app lets you pick or capture a leaf photo, send it to the backend, and show the prediction result plus an optional Grad-CAM heatmap.

## Tech Stack

- Flutter for the mobile app
- Dart for the client logic
- FastAPI for the backend API
- PyTorch and TorchVision for inference
- OpenCV and Grad-CAM for explainability output
- PostgreSQL for diagnosis history and feedback
- Docker for backend deployment

## Project Structure

- `app/` Flutter application
- `backend/` FastAPI server and model inference code
- `model/` local PyTorch model weights
- `data/` raw and verified image storage

## Features

- Capture a leaf photo from camera or gallery
- Upload the image to the backend for diagnosis
- Show disease name, confidence, and AI heatmap
- Submit feedback to improve future predictions
- Store diagnosis history in PostgreSQL

## Requirements

- Flutter 3.x or newer
- Python 3.12 or newer
- PostgreSQL database
- A trained `.pth` model file in `model/`
- Backend environment variables configured in `backend/.env`
- App environment variables configured in `app/.env`

## Backend Setup

Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Create a `backend/.env` file with values like:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/krishi_ai
LOCAL_MODEL_PATH=model/best_plant_model.pth
TRAINING_API_KEY=your_training_api_key
NUM_CLASSES=38
SKIP_HEATMAP=false
PROJECT_NAME=Krishi AI Backend
```

Run the API locally:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

The API will be available at:

- `http://localhost:7860/health`
- `http://localhost:7860/api/diagnose`

## Flutter App Setup

Install packages:

```bash
cd app
flutter pub get
```

Create an `app/.env` file and point it to your backend URL:

```env
BASE_URL=http://10.16.25.26:5407
```

Run the app:

```bash
cd app
flutter run
```

If you are testing on a physical device, make sure the backend URL is reachable from that device and update it from the app settings screen if needed.

## How to Use

1. Start the backend server.
2. Open the Flutter app.
3. Tap camera or gallery to choose a plant leaf image.
4. Tap Diagnose Plant.
5. Review the prediction, confidence score, and heatmap.
6. If the result is wrong, submit feedback from the app.

## Deployment

### Backend Deployment

The backend includes a Dockerfile, so you can build and run it with Docker:

```bash
cd backend
docker build -t krishi-ai-backend .
docker run -p 7860:7860 --env-file .env krishi-ai-backend
```

Before deploying, make sure the following are available in the container or host environment:

- `DATABASE_URL`
- `TRAINING_API_KEY`
- `NUM_CLASSES`
- `LOCAL_MODEL_PATH`

### Flutter Deployment

Build the Android release APK:

```bash
cd app
flutter build apk --release
```

If you want iOS or web builds, use the normal Flutter release commands for those targets.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.

## Notes

- The Flutter app loads its backend URL from `app/.env` and also lets you update it from the settings dialog.
- The backend expects image uploads as multipart form data with the `file` field.
- The model must be loaded before diagnosis will work; if it is missing, the backend returns a helpful error.
