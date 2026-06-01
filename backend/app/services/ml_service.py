import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from app.config import settings
import io
import base64
import numpy as np
import cv2