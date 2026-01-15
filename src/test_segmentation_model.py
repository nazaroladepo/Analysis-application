import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

# 1. Load the model
print("▶ Loading segmentation model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = (
    AutoModelForImageSegmentation
    .from_pretrained("briaai/RMBG-2.0", trust_remote_code=True)
    .eval()
    .to(device)
)
print("Model loaded.")

# 2. Create a dummy image (RGB, 1024x1024)
dummy_np = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8)
dummy_pil = Image.fromarray(dummy_np)

# 3. Transform the image
transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])
inp = transform_image(dummy_pil).unsqueeze(0).to(device)
print("Dummy image prepared.")

# 4. Run the model
try:
    print("Running model inference...")
    with torch.no_grad():
        preds = model(inp)[-1].sigmoid().cpu()[0].squeeze(0).numpy()
    print("Model inference completed. Output shape:", preds.shape)
except Exception as e:
    print("Error during model inference:", e) 