# src/process_plant.py  (or wherever this lives)

import os
import io
import json
import re
import cv2
import boto3
import torch
import yaml  # if you need it elsewhere; safe to remove if unused
import numpy as np
import matplotlib
matplotlib.use("Agg")  # safe for headless servers
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists() and not os.environ.get("AWS_ACCESS_KEY_ID"):
        load_dotenv(env_file)
        print(f"pipeline_runner: Loaded environment variables from {env_file}")
except (ImportError, Exception) as e:
    print(f"pipeline_runner: Could not load .env file: {e}")

from PIL import Image
import numpy as np
from src.data_loader import load_single_frame_from_s3
from src.composite import create_composites, convert_to_uint8
from src.features import compute_veg_indices, compute_veg_index_features, VEG_INDEX_CHANNELS
from src.morphology import detect_and_return_morphology
from src.feature_texture import analyze_texture_features, compute_texture_features

from torchvision import transforms
import torch.nn.functional as F
from transformers import AutoModelForImageSegmentation, AutoProcessor
from huggingface_hub import login

# Try to import SAM3 (may not be available in all transformers versions)
SAM3_AVAILABLE = False
Sam3Processor = None
Sam3Model = None

try:
    # Try direct import first
    from transformers import Sam3Processor, Sam3Model
    SAM3_AVAILABLE = True
except ImportError:
    try:
        # Try using AutoProcessor/AutoModel as fallback
        from transformers import AutoProcessor, AutoModelForImageSegmentation
        # Check if SAM3 model exists on HuggingFace
        try:
            # Test if we can load the processor
            test_processor = AutoProcessor.from_pretrained("facebook/sam3", token=os.getenv("HF_TOKEN"))
            # If successful, use Auto classes
            Sam3Processor = AutoProcessor
            Sam3Model = AutoModelForImageSegmentation
            SAM3_AVAILABLE = True
            print("[INFO] SAM3 available via AutoProcessor/AutoModel")
        except Exception as e:
            SAM3_AVAILABLE = False
            print(f"[WARN] SAM3 not available: {e}")
    except Exception as e:
        SAM3_AVAILABLE = False
        print(f"[WARN] Could not check SAM3 availability: {e}")

from src.data_loader import load_single_frame_from_s3
from src.composite import create_composites, convert_to_uint8
from src.features import compute_veg_indices, compute_veg_index_features, VEG_INDEX_CHANNELS
from src.feature_texture import analyze_texture_features, compute_texture_features
from src.morphology import create_morphology_outputs  # NEW

# -----------------------------
# Auth: Hugging Face (if token present)
# -----------------------------
S3_BUCKET = "plant-analysis-data"
S3_PREFIX = "results/{species}_results/{plant_id}/{date}/"

hf_token = os.getenv("HF_TOKEN")
# Set HuggingFace cache to home directory to avoid /scratch permission issues
hf_home = str(Path.home() / ".cache" / "huggingface")
os.environ["HF_HOME"] = hf_home
os.environ["TRANSFORMERS_CACHE"] = hf_home
os.environ["HF_HUB_CACHE"] = hf_home

if hf_token:
    try:
        login(token=hf_token)
    except Exception:
        # non-fatal
        pass

# -----------------------------
# Global: S3 helpers
# -----------------------------
def get_s3_client():
    """Create and return an S3 client with credentials from environment."""
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    S3_REGION = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("REGION", "us-east-2"))
    
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        return boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    else:
        # Fallback to default credential chain
        return boto3.client('s3', region_name=S3_REGION)

def save_json_to_s3(obj, bucket, key, content_type="application/json"):
    s3 = get_s3_client()
    s3.upload_fileobj(io.BytesIO(json.dumps(obj, indent=2).encode("utf-8")), bucket, key,
                      ExtraArgs={"ContentType": content_type})

def save_image_to_s3(bucket, key, image_np):
    s3 = get_s3_client()
    success, encoded_img = cv2.imencode('.png', image_np)
    if not success:
        print(f"[ERROR] cv2.imencode failed for {key} with image shape {getattr(image_np, 'shape', None)} and dtype {getattr(image_np, 'dtype', None)}")
        return
    s3.upload_fileobj(io.BytesIO(encoded_img.tobytes()), bucket, key, ExtraArgs={'ContentType': 'image/png'})

def save_morph_images_to_s3(images_dict, bucket, prefix):
    """images_dict: name -> np.uint8 image; returns name->s3_key"""
    out = {}
    for name, im in images_dict.items():
        key = f"{prefix}/morphology/images/{name}.png"
        save_image_to_s3(bucket, key, im)
        out[name] = key
    return out

def save_morph_csv(morph_results, bucket, key):
    """Write a simple CSV across plants with size + morphology traits."""
    import csv
    # gather columns
    all_size, all_morph = set(), set()
    for _, r in morph_results.items():
        all_size |= set(r.get("size_traits", {}).keys())
        all_morph |= set(r.get("morphology_traits", {}).keys())
    size_cols = sorted(all_size)
    morph_cols = sorted(all_morph)
    cols = ["plant_id"] + [f"size.{c}" for c in size_cols] + [f"morph.{c}" for c in morph_cols]

    bio = io.StringIO()
    w = csv.writer(bio)
    w.writerow(cols)
    for pid, r in morph_results.items():
        size = r.get("size_traits", {})
        morph = r.get("morphology_traits", {})
        row = [pid] + [size.get(c, "") for c in size_cols] + [morph.get(c, "") for c in morph_cols]
        w.writerow(row)
    data = bio.getvalue().encode("utf-8")
    s3 = get_s3_client()
    s3.upload_fileobj(io.BytesIO(data), bucket, key, ExtraArgs={"ContentType":"text/csv"})

# -----------------------------
# Global: Segmentation models (load ONCE)
# -----------------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# RMBG-2.0 model (legacy/default fallback)
try:
    # Use home directory cache to avoid /scratch permission issues
    cache_dir = str(Path.home() / ".cache" / "huggingface")
    os.makedirs(cache_dir, exist_ok=True)
    RMBG_PROCESSOR = AutoProcessor.from_pretrained(
        "briaai/RMBG-2.0", 
        trust_remote_code=True,
        cache_dir=cache_dir
    )
    RMBG = (AutoModelForImageSegmentation
            .from_pretrained(
                "briaai/RMBG-2.0", 
                trust_remote_code=True,
                cache_dir=cache_dir
            )
            .eval()
            .to(DEVICE))
    torch.set_float32_matmul_precision('high')
    print(f"[INFO] RMBG-2.0 model loaded successfully")
except Exception as e:
    RMBG = None
    RMBG_PROCESSOR = None
    print(f"[WARN] Could not load RMBG-2.0 model: {e}")
    print(f"[WARN] Error details: {str(e)}")

# SAM3 model (main/default method)
SAM3_MODEL = None
SAM3_PROCESSOR = None
if SAM3_AVAILABLE:
    try:
        if hf_token:
            # Use home directory cache (already set via environment variables above)
            cache_dir = hf_home
            os.makedirs(cache_dir, exist_ok=True)
            
            # Try loading SAM3 with token
            if Sam3Processor and Sam3Model:
                SAM3_MODEL = Sam3Model.from_pretrained(
                    "facebook/sam3", 
                    token=hf_token, 
                    cache_dir=cache_dir,
                    trust_remote_code=True
                ).to(DEVICE).eval()
                SAM3_PROCESSOR = Sam3Processor.from_pretrained(
                    "facebook/sam3", 
                    token=hf_token, 
                    cache_dir=cache_dir,
                    trust_remote_code=True
                )
                print(f"[INFO] SAM3 model loaded successfully from facebook/sam3")
            else:
                print(f"[WARN] SAM3 classes not available")
        else:
            print(f"[WARN] HF_TOKEN not found; SAM3 model not loaded")
    except Exception as e:
        SAM3_MODEL = None
        SAM3_PROCESSOR = None
        print(f"[WARN] Could not load SAM3 model: {e}")
        print(f"[WARN] Error details: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print(f"[WARN] SAM3 not available in transformers library; will use RMBG as default")

TRANSFORM_IMAGE = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# -----------------------------
# Global: YOLO detector for Mullet pot/vase removal
# -----------------------------
YOLO_MODEL = None
YOLO_MODEL_PATH = Path(__file__).parent / "weights" / "yolo11s.pt"
YOLO_FALLBACK_PATH = Path(__file__).parent / "weights" / "yolov8n.pt"

try:
    from ultralytics import YOLO
    if YOLO_MODEL_PATH.exists():
        YOLO_MODEL = YOLO(str(YOLO_MODEL_PATH))
        print(f"[INFO] Loaded YOLO model from {YOLO_MODEL_PATH}")
    elif YOLO_FALLBACK_PATH.exists():
        YOLO_MODEL = YOLO(str(YOLO_FALLBACK_PATH))
        print(f"[INFO] Loaded fallback YOLO model from {YOLO_FALLBACK_PATH}")
    else:
        print(f"[WARN] No YOLO weights found at {YOLO_MODEL_PATH} or {YOLO_FALLBACK_PATH}")
except ImportError:
    print("[WARN] ultralytics not installed; YOLO detection disabled")
except Exception as e:
    print(f"[WARN] Could not load YOLO model: {e}")


def run_yolo_detection(image: np.ndarray) -> Dict[str, Any]:
    """
    Run YOLO detection on an image to find plant bbox and vase/pot boxes to exclude.
    
    Args:
        image: BGR or RGB image as numpy array
        
    Returns:
        Dict with 'largest_box' (plant bbox) and 'vase_boxes' (list of pot/vase bboxes)
    """
    result = {
        'largest_box': None,
        'vase_boxes': [],
        'boxes': [],
        'scores': [],
        'class_names': []
    }
    
    if YOLO_MODEL is None:
        return result
    
    try:
        # YOLO expects RGB; if BGR, convert
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # Run inference
        detections = YOLO_MODEL(image_rgb, verbose=False)
        
        if not detections or len(detections) == 0:
            return result
        
        det = detections[0]
        if det.boxes is None or len(det.boxes) == 0:
            return result
        
        boxes = det.boxes.xyxy.cpu().numpy()
        scores = det.boxes.conf.cpu().numpy()
        class_ids = det.boxes.cls.cpu().numpy().astype(int)
        
        # Get class names from model
        names = det.names if hasattr(det, 'names') else {}
        
        plant_boxes = []
        vase_boxes = []
        
        for i, (box, score, cls_id) in enumerate(zip(boxes, scores, class_ids)):
            x1, y1, x2, y2 = map(int, box)
            cls_name = names.get(cls_id, str(cls_id)).lower()
            
            result['boxes'].append((x1, y1, x2, y2))
            result['scores'].append(float(score))
            result['class_names'].append(cls_name)
            
            # Heuristics: identify plant vs vase/pot
            # Common COCO class: 'vase' (id 75), 'potted plant' (id 58)
            if any(kw in cls_name for kw in ['vase', 'pot', 'container', 'planter']):
                vase_boxes.append((x1, y1, x2, y2))
            elif any(kw in cls_name for kw in ['plant', 'sorghum', 'potted']):
                plant_boxes.append((x1, y1, x2, y2, float(score)))
        
        # If no explicit plant boxes, use largest detection as plant
        if plant_boxes:
            # Use highest confidence plant box
            plant_boxes.sort(key=lambda x: x[4], reverse=True)
            result['largest_box'] = plant_boxes[0][:4]
        elif result['boxes']:
            # Fallback: largest box by area
            areas = [(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in result['boxes']]
            largest_idx = int(np.argmax(areas))
            result['largest_box'] = result['boxes'][largest_idx]
        
        result['vase_boxes'] = vase_boxes
        
        print(f"[YOLO] Detected {len(result['boxes'])} objects, largest_box={result['largest_box']}, vase_boxes={len(vase_boxes)}")
        
    except Exception as e:
        print(f"[WARN] YOLO detection failed: {e}")
    
    return result

# -----------------------------
# Vegetation index helper (unchanged)
# -----------------------------
def save_index(idx, func, spec, mask, s3_bucket, s3_prefix):
    bands = VEG_INDEX_CHANNELS.get(idx)
    if bands is None:
        print(f"[WARN] No bands found for index {idx}, skipping.")
        return
    try:
        vals = [spec[b].squeeze(-1) for b in bands]
    except KeyError as e:
        print(f"[WARN] Missing band {e} for index {idx}, skipping.")
        return
    arr = func(*vals)
    masked = np.where(mask == 255, arr, np.nan)
    img8 = convert_to_uint8(masked)
    if img8 is None or not isinstance(img8, np.ndarray) or img8.size == 0 or np.all(img8 == 0):
        print(f"[WARN] img8 for {idx} is invalid or all zeros, skipping.")
        return
    fig = plt.figure(figsize=(8, 8))
    try:
        im = plt.imshow(img8, cmap='YlGn')
        plt.axis('off')
        cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
        cbar.set_ticks([0, 255])
        cbar.set_ticklabels([f"{np.nanmin(masked):.2f}", f"{np.nanmax(masked):.2f}"])
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        buf.seek(0)
        s3 = get_s3_client()
        s3_key = f"{s3_prefix}/vegetation_indices/{idx}.png"
        s3.upload_fileobj(buf, s3_bucket, s3_key, ExtraArgs={'ContentType': 'image/png'})
    except Exception as e:
        print(f"[ERROR] Failed to plot/save index {idx}: {e}")
    finally:
        plt.close(fig)

# -----------------------------
# SAM3 Segmentation Functions
# -----------------------------
def segment_with_sam3(image: Image.Image, text_prompt: str = "plant") -> Dict:
    """
    Segment image using SAM3 with text prompt.
    
    Args:
        image: PIL Image to segment
        text_prompt: Text description of the object (e.g., "plant")
        
    Returns:
        Dict with 'masks', 'boxes', 'scores'
    """
    if SAM3_MODEL is None or SAM3_PROCESSOR is None:
        raise ValueError("SAM3 model not available")
    
    inputs = SAM3_PROCESSOR(images=image, text=text_prompt, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        outputs = SAM3_MODEL(**inputs)
    results = SAM3_PROCESSOR.post_process_instance_segmentation(
        outputs, threshold=0.5, mask_threshold=0.5, target_sizes=inputs.get("original_sizes").tolist()
    )[0]
    return {"masks": results["masks"], "boxes": results["boxes"], "scores": results["scores"]}


def select_middle_plant(masks: torch.Tensor, boxes: torch.Tensor, image_shape: Tuple[int, int]) -> np.ndarray:
    """Select the plant closest to the image center (spatial center)."""
    if len(masks) == 0:
        return np.zeros(image_shape[:2], dtype=np.uint8)
    if len(masks) == 1:
        return (masks[0].cpu().numpy().squeeze() * 255).astype(np.uint8)
    centers = []
    for box in boxes:
        x1, y1, x2, y2 = box.cpu().numpy()
        centers.append(((x1 + x2) / 2, (y1 + y2) / 2))
    img_center = (image_shape[1] / 2, image_shape[0] / 2)
    distances = [np.sqrt((c[0] - img_center[0])**2 + (c[1] - img_center[1])**2) for c in centers]
    middle_idx = int(np.argmin(distances))
    return (masks[middle_idx].cpu().numpy().squeeze() * 255).astype(np.uint8)


def select_middle_front_plant(masks: torch.Tensor, boxes: torch.Tensor, scores: torch.Tensor = None, image_shape: Tuple[int, int] = None) -> np.ndarray:
    """
    Select the middle front (closest to camera) plant.
    Combines:
    1. Horizontal position (middle of image) - 40% weight
    2. Vertical position (lower = closer to camera) - 30% weight  
    3. Size (larger = closer) - 30% weight
    """
    if image_shape is None:
        raise ValueError("image_shape is required for select_middle_front_plant")
    if len(masks) == 0:
        return np.zeros(image_shape[:2], dtype=np.uint8)
    if len(masks) == 1:
        return (masks[0].cpu().numpy().squeeze() * 255).astype(np.uint8)
    
    img_height, img_width = image_shape[:2]
    img_center_x = img_width / 2
    img_center_y = img_height / 2
    
    horizontal_scores = []
    vertical_scores = []
    size_scores = []
    
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box.cpu().numpy()
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        horizontal_dist = abs(center_x - img_center_x)
        horizontal_scores.append(1.0 / (1.0 + horizontal_dist / img_width))
        
        vertical_scores.append(center_y / img_height)
        
        mask_area = masks[i].cpu().numpy().sum()
        size_scores.append(mask_area)
    
    max_horizontal = max(horizontal_scores) if max(horizontal_scores) > 0 else 1.0
    max_vertical = max(vertical_scores) if max(vertical_scores) > 0 else 1.0
    max_size = max(size_scores) if max(size_scores) > 0 else 1.0
    
    horizontal_scores = [s / max_horizontal for s in horizontal_scores]
    vertical_scores = [s / max_vertical for s in vertical_scores]
    size_scores = [s / max_size for s in size_scores]
    
    combined_scores = [
        0.4 * h + 0.3 * v + 0.3 * s
        for h, v, s in zip(horizontal_scores, vertical_scores, size_scores)
    ]
    
    selected_idx = int(np.argmax(combined_scores))
    return (masks[selected_idx].cpu().numpy().squeeze() * 255).astype(np.uint8)


def select_plant_only(masks: torch.Tensor, boxes: torch.Tensor, scores: torch.Tensor, image_shape: Tuple[int, int]) -> np.ndarray:
    """
    Select the plant (largest or highest scoring) instead of center plant.
    For plant1, use this method to select 'the plant only'.
    """
    if len(masks) == 0:
        return np.zeros(image_shape[:2], dtype=np.uint8)
    if len(masks) == 1:
        return (masks[0].cpu().numpy().squeeze() * 255).astype(np.uint8)
    
    mask_areas = []
    for mask in masks:
        area = mask.cpu().numpy().sum()
        mask_areas.append(area)
    
    if scores is not None and len(scores) > 0:
        scores_array = scores.cpu().numpy()
        combined_scores = scores_array * 0.7 + (np.array(mask_areas) / max(mask_areas)) * 0.3
        selected_idx = int(np.argmax(combined_scores))
    else:
        selected_idx = int(np.argmax(mask_areas))
    
    return (masks[selected_idx].cpu().numpy().squeeze() * 255).astype(np.uint8)


def select_plant_mask_sorghum(masks: torch.Tensor, boxes: torch.Tensor, scores: torch.Tensor, 
                               image_shape: Tuple[int, int], plant_id: str) -> np.ndarray:
    """
    Select plant mask based on sorghum-specific logic.
    - For plant1: select "the plant only" (largest/highest score)
    - For plant12, plant24, plant2, plant26, plant28, plant29, plant31, plant40, plant42, plant46: 
      use middle plant (not front)
    - For others: select middle-front plant
    """
    if plant_id and plant_id.lower() == "plant1":
        return select_plant_only(masks, boxes, scores, image_shape)
    elif plant_id and plant_id.lower() in ["plant12", "plant24", "plant2", "plant26", "plant28", 
                                            "plant29", "plant31", "plant40", "plant42", "plant46"]:
        return select_middle_plant(masks, boxes, image_shape)
    else:
        return select_middle_front_plant(masks, boxes, scores, image_shape)


# -----------------------------
# Main pipeline for one plant-frame
# -----------------------------
def process_plant_image(bucket, key, segmentation_method: str = "sam3"):
    """
    Runs the full pipeline for a single plant image in S3:
    - load frame
    - create composites
    - crop to bbox (if available)
    - segment RMBG -> mask (largest CC)
    - save original/mask/overlay/segmented
    - compute vegetation indices + JSON
    - compute texture features (maps + JSON)
    - compute morphology (traits + diagnostic images + CSV)

    Returns a dict with veg, texture, morphology, and mask path.
    """
    print(f" >>>>>>>>>>>>>>>>>>>>>>>>>>>>> Processing plant image: {key}")
    parts = key.split("/")

    # Default values
    crop = ""
    date = ""
    plant_id = ""
    fname = ""

    # Handle "Dr. Mullet's Sorghum" path structure:
    #   Dr. Mullet's Sorghum/{date}/{plant}/{filename}
    if len(parts) >= 3 and parts[0] == "Dr. Mullet's Sorghum":
        crop = "Mullet"
        date = parts[1] if len(parts) > 1 else ""
        plant_id = parts[2] if len(parts) > 2 else ""
        fname = parts[3] if len(parts) > 3 else ""
        print(f"🌾 Processing Mullet from Dr. Mullet's Sorghum - date: {date}, plant: {plant_id}")
    
    # Handle new uploaded structure:
    #   Uploaded_dataset/{Species}_dataset/{date}/plant{num}/{filename}
    if len(parts) >= 5 and parts[0] == "Uploaded_dataset" and parts[1].endswith("_dataset"):
        dataset_root = parts[0]
        species_dataset = parts[1]
        crop = species_dataset.replace("_dataset", "") if species_dataset else ""
        date = parts[2]
        plant_id = parts[3]
        fname = parts[4] if len(parts) > 4 else ""
        print(f"🌾 Processing uploaded file (new structure) - crop from folder: {crop}")

    else:
        # Legacy Uploaded_dataset without species subfolder:
        #   Uploaded_dataset/{date}/{plant}/{filename}
        # or standard structure:
        #   {Species}_dataset/{date}/{plant}/{filename}
        dataset = parts[0] if len(parts) > 0 else ""
        date = parts[1] if len(parts) > 1 else ""
        plant_id = parts[2] if len(parts) > 2 else ""
        fname = parts[3] if len(parts) > 3 else ""

        if dataset == "Uploaded_dataset" and fname:
            # Extract crop name from filename format: {Species}_{Date}_plant#.tiff
            # Example: Sorghum_2024-12-04_plant1.tiff -> crop = "Sorghum"
            pattern = r'^([A-Z][A-Za-z-]+)_(\d{4}-\d{2}-\d{2})_plant(\d+)\.(tiff|tif)$'
            match = re.match(pattern, fname, re.IGNORECASE)
            if match:
                crop = match.group(1)
                print(f"🌾 Processing uploaded file (legacy) - crop extracted from filename: {crop}")
            else:
                crop = "Uploaded"
                print(f"🌾 Processing uploaded file (legacy) - filename format not recognized, using default: {crop}")
        else:
            # Standard dataset-based crop
            crop = dataset.replace("_dataset", "") if dataset else ""
            print(f"🌾 Processing crop: {crop}")
    if "Image_" in fname:
        frame_str = fname.split("Image_")[-1].replace(".tif", "").replace(".tiff", "")
    else:
        frame_str = fname.split("_")[-1].replace(".tif", "").replace(".tiff", "")
    date_key = date.replace('-', '_')
    flat_key = f"{date_key}_{plant_id}_{frame_str}"

    # Build dynamic results prefixes based on crop
    # For uploaded data (under Uploaded_dataset), nest results under
    # results/Uploaded_results/{crop}_results/...
    # Special case: Mullet uses "Mullet_result" (singular) instead of "Mullet_results"
    if parts[0] == "Uploaded_dataset":
        results_root = f"results/Uploaded_results/{crop}_results"
    elif crop.lower() == "mullet":
        results_root = "results/Mullet_result"
    else:
        results_root = f"results/{crop}_results"
    prefix = f"{results_root}/timeline_images/{plant_id}/{date}"
    summary_prefix = f"{results_root}/{plant_id}/{date}"

    # 1) Load
    image = load_single_frame_from_s3(bucket, key)
    flats = {flat_key: {'raw_image': (image, os.path.basename(key))}}

    # 2) Composite
    flats = create_composites(flats)

    # 3) For this plant (single entry), build bbox crop + RMBG mask
    is_mullet = crop.lower() == 'mullet'
    
    for _, pdata in flats.items():
        comp = pdata['composite']
        if comp is None or not isinstance(comp, np.ndarray) or comp.size == 0:
            print(f"[ERROR] Invalid composite image for plant")
            continue
        H, W = comp.shape[:2]
        if H <= 0 or W <= 0:
            print(f"[ERROR] Invalid image dimensions: {H}x{W}")
            continue

        # For Sorghum, try to use bounding box if available; for Corn/Cotton skip bbox
        bbox = None
        yolo_vase_boxes: List[Tuple[int, int, int, int]] = []
        
        # For Mullet crops, use YOLO detection to find plant bbox and vase/pot boxes
        if is_mullet and YOLO_MODEL is not None:
            print("▶ Running YOLO detection for Mullet crop (pot removal)")
            yolo_result = run_yolo_detection(comp)
            if yolo_result['largest_box'] is not None:
                bbox = tuple(yolo_result['largest_box'])
                pdata['yolo_bbox'] = bbox
                print(f"[YOLO] Using detected plant bbox: {bbox}")
            if yolo_result['vase_boxes']:
                yolo_vase_boxes = yolo_result['vase_boxes']
                pdata['yolo_vase_boxes'] = yolo_vase_boxes
                print(f"[YOLO] Found {len(yolo_vase_boxes)} vase/pot boxes to exclude")
        elif crop.lower() == 'sorghum':
            bbox_bucket = bucket
            bbox_key = f"bouningbox/{plant_id}.json"
            s3 = get_s3_client()
            try:
                bbox_data = s3.get_object(Bucket=bbox_bucket, Key=bbox_key)['Body'].read()
                jd = json.loads(bbox_data)
                rect = next((s for s in jd.get('shapes', []) if s.get('shape_type') == 'rectangle'), None)
                bbox = (
                    int(rect['points'][0][0]),
                    int(rect['points'][0][1]),
                    int(rect['points'][1][0]),
                    int(rect['points'][1][1])
                ) if rect else None
            except Exception:
                bbox = None

        x1, y1, x2, y2 = bbox if bbox else (0, 0, W, H)
        x1, x2 = max(0, x1), min(W, x2)
        y1, y2 = max(0, y1), min(H, y2)
        
        # Ensure valid crop dimensions
        crop_h = max(1, y2 - y1)
        crop_w = max(1, x2 - x1)

        mask_box = np.zeros((H, W), dtype=np.uint8)
        if crop_h > 0 and crop_w > 0:
            mask_box[y1:y2, x1:x2] = 255

        # For Mullet: create exclusion mask for vase/pot boxes before RMBG
        crop_mask = np.ones((crop_h, crop_w), dtype=np.float32)
        if is_mullet and yolo_vase_boxes:
            for vx1, vy1, vx2, vy2 in yolo_vase_boxes:
                # Convert vase box coordinates to crop-relative coordinates
                crop_vx1 = max(0, vx1 - x1)
                crop_vy1 = max(0, vy1 - y1)
                crop_vx2 = min(crop_w, vx2 - x1)
                crop_vy2 = min(crop_h, vy2 - y1)
                # Only exclude if vase box overlaps with crop region
                if crop_vx2 > crop_vx1 and crop_vy2 > crop_vy1:
                    # Ensure indices are within bounds
                    crop_vx1 = min(crop_vx1, crop_w - 1)
                    crop_vy1 = min(crop_vy1, crop_h - 1)
                    crop_vx2 = min(crop_vx2, crop_w)
                    crop_vy2 = min(crop_vy2, crop_h)
                    if crop_vx2 > crop_vx1 and crop_vy2 > crop_vy1:
                        crop_mask[crop_vy1:crop_vy2, crop_vx1:crop_vx2] = 0.0
                        print(f"[YOLO] Excluding vase box from crop: ({crop_vx1}, {crop_vy1}, {crop_vx2}, {crop_vy2})")

        # Apply bbox mask - ensure mask dimensions match image dimensions
        # Verify comp is valid
        if len(comp.shape) < 2:
            print(f"[ERROR] Invalid comp shape: {comp.shape}")
            continue
        comp_h, comp_w = comp.shape[:2]
        if mask_box.shape[:2] != (comp_h, comp_w):
            print(f"[ERROR] Mask shape {mask_box.shape[:2]} doesn't match comp shape {(comp_h, comp_w)}, resizing mask")
            mask_box = cv2.resize(mask_box, (comp_w, comp_h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
        if mask_box.dtype != np.uint8:
            print(f"[WARN] Converting mask dtype from {mask_box.dtype} to uint8")
            if mask_box.max() > 255 or mask_box.dtype in [np.uint16, np.float32, np.float64]:
                mask_box = cv2.normalize(mask_box, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            else:
                mask_box = mask_box.astype(np.uint8)
        # Ensure comp is uint8 for bitwise operations (create a copy to avoid modifying original)
        comp_for_mask = comp
        if comp.dtype != np.uint8:
            print(f"[WARN] Converting comp dtype from {comp.dtype} to uint8 for bitwise operation")
            if comp.max() > 255 or comp.dtype in [np.uint16, np.float32, np.float64]:
                comp_for_mask = cv2.normalize(comp, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            else:
                comp_for_mask = comp.astype(np.uint8)
        masked = cv2.bitwise_and(comp_for_mask, comp_for_mask, mask=mask_box)
        
        # For Mullet: apply vase exclusion to the cropped region
        if is_mullet and crop_mask.min() < 1.0:
            # Extract the crop region and apply exclusion mask
            crop_region = masked[y1:y2, x1:x2].copy()
            
            # Ensure crop_mask dimensions match crop_region dimensions
            crop_h, crop_w = crop_region.shape[:2]
            if crop_mask.shape[:2] != (crop_h, crop_w):
                print(f"[WARN] Resizing crop_mask from {crop_mask.shape[:2]} to match crop_region {crop_region.shape[:2]}")
                crop_mask = cv2.resize(crop_mask.astype(np.float32), (crop_w, crop_h), interpolation=cv2.INTER_NEAREST)
            
            crop_region = crop_region.astype(np.float32)
            if len(crop_region.shape) == 3:
                # RGB/BGR image - need 3D mask
                crop_mask_3d = np.stack([crop_mask] * crop_region.shape[2], axis=2)
                # Ensure dimensions match exactly
                assert crop_mask_3d.shape == crop_region.shape, f"crop_mask_3d shape {crop_mask_3d.shape} != crop_region shape {crop_region.shape}"
                crop_region = (crop_region * crop_mask_3d).astype(np.uint8)
            else:
                # Grayscale image - use 2D mask directly
                assert crop_mask.shape == crop_region.shape, f"crop_mask shape {crop_mask.shape} != crop_region shape {crop_region.shape}"
                crop_region = (crop_region * crop_mask).astype(np.uint8)
            # Put the excluded crop back into masked
            # Ensure crop_region matches the slice dimensions exactly
            slice_h, slice_w = masked[y1:y2, x1:x2].shape[:2]
            if crop_region.shape[:2] != (slice_h, slice_w):
                print(f"[WARN] Resizing crop_region from {crop_region.shape[:2]} to match slice {slice_h}x{slice_w}")
                crop_region = cv2.resize(crop_region, (slice_w, slice_h), interpolation=cv2.INTER_LINEAR)
            masked[y1:y2, x1:x2] = crop_region
            # Ensure masked still has correct dtype and shape
            assert masked.shape == comp.shape, f"masked shape {masked.shape} != comp shape {comp.shape}"
            assert masked.dtype == comp.dtype, f"masked dtype {masked.dtype} != comp dtype {comp.dtype}"
            print("[YOLO] Applied vase exclusion mask to input image")

        # Segmentation using selected method (default: SAM3)
        # Convert masked image to PIL
        pil = Image.fromarray(cv2.cvtColor(masked, cv2.COLOR_BGR2RGB))
        
        if segmentation_method.lower() == "sam3":
            # SAM3 segmentation (main/default method)
            if SAM3_MODEL is None or SAM3_PROCESSOR is None:
                print("[ERROR] SAM3 model not available; falling back to RMBG.")
                segmentation_method = "rmbg"
            else:
                print("▶ Running SAM3 segmentation...")
                try:
                    sam3_results = segment_with_sam3(pil, text_prompt="plant")
                    
                    # For sorghum plants, use sorghum-specific selection logic
                    if crop.lower() == "sorghum":
                        mask_full = select_plant_mask_sorghum(
                            sam3_results["masks"],
                            sam3_results["boxes"],
                            sam3_results["scores"],
                            (H, W),
                            plant_id
                        )
                    else:
                        # For other crops, use middle-front plant selection
                        mask_full = select_middle_front_plant(
                            sam3_results["masks"],
                            sam3_results["boxes"],
                            sam3_results["scores"],
                            (H, W)
                        )
                    
                    print(f"▶ SAM3 found {len(sam3_results['masks'])} plant(s), selected one")
                except Exception as e:
                    print(f"[ERROR] SAM3 segmentation failed: {e}, falling back to RMBG")
                    segmentation_method = "rmbg"
        
        if segmentation_method.lower() == "rmbg":
            # RMBG segmentation (fallback/legacy method)
            if RMBG is None or RMBG_PROCESSOR is None:
                print("[ERROR] RMBG model not available; cannot segment.")
                return None

            print("▶ Running RMBG segmentation...")
            inputs = RMBG_PROCESSOR(images=pil, return_tensors="pt")
            pixel_values = inputs["pixel_values"].to(DEVICE)

            # Prediction using processor-based inputs (BiRefNet expects tensor as positional arg)
            with torch.no_grad():
                outputs = RMBG(pixel_values)

            # Handle RMBG-2.0 output format - get the last prediction and squeeze properly
            pred = outputs[-1].sigmoid().cpu()
            if pred.dim() == 4:  # (batch, channels, H, W)
                pred = pred[0].squeeze()  # Remove batch and channel dims
            elif pred.dim() == 3:  # (batch, H, W) or (channels, H, W)
                pred = pred[0] if pred.shape[0] == 1 else pred.squeeze()
            pred = pred.numpy()
            print(f"DEBUG: pred shape after processing: {pred.shape}")

            mask_pred = (pred > 0.5).astype(np.uint8) * 255
            mask_full = cv2.resize(mask_pred, (W, H), interpolation=cv2.INTER_NEAREST)
            
            # Ensure mask is single channel for OpenCV and correct dtype
            if len(mask_full.shape) > 2:
                mask_full = mask_full[:, :, 0] if mask_full.shape[2] == 1 else cv2.cvtColor(mask_full, cv2.COLOR_BGR2GRAY)
            mask_full = mask_full.astype(np.uint8)
            
            # Verify mask dimensions match image dimensions
            if mask_full.shape[:2] != (H, W):
                print(f"[WARN] Mask shape {mask_full.shape} doesn't match image shape ({H}, {W}), resizing...")
                mask_full = cv2.resize(mask_full, (W, H), interpolation=cv2.INTER_NEAREST)

        # For Mullet: exclude vase areas from final mask
        if is_mullet and yolo_vase_boxes:
            for vx1, vy1, vx2, vy2 in yolo_vase_boxes:
                # Clamp vase box to image bounds
                vx1 = max(0, min(W, int(vx1)))
                vx2 = max(0, min(W, int(vx2)))
                vy1 = max(0, min(H, int(vy1)))
                vy2 = max(0, min(H, int(vy2)))
                if vx2 > vx1 and vy2 > vy1:
                    mask_full[vy1:vy2, vx1:vx2] = 0
                    print(f"[YOLO] Excluding vase box from final mask: ({vx1}, {vy1}, {vx2}, {vy2})")

        # Largest connected component
        n_lbl, labels, stats, _ = cv2.connectedComponentsWithStats(mask_full, 8)

        if n_lbl > 1:
            largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            mask_full = (labels == largest).astype(np.uint8) * 255

        pdata['mask'] = mask_full

        # Save images (commented out for timeline images script except for original)
        try:
            save_image_to_s3(bucket, f"{prefix}/original.png", comp)
        except Exception:
            pass
        try:
            save_image_to_s3(bucket, f"{prefix}/mask.png", mask_full)
        except Exception:
            pass

        bright = cv2.convertScaleAbs(comp, alpha=1.2, beta=15)
        overlay = bright.copy()
        
        # Ensure mask dimensions match for overlay operation
        if mask_full.shape[:2] != overlay.shape[:2]:
            print(f"[WARN] Mask shape {mask_full.shape} doesn't match overlay shape {overlay.shape[:2]}, resizing...")
            mask_full = cv2.resize(mask_full, (overlay.shape[1], overlay.shape[0]), interpolation=cv2.INTER_NEAREST)
        
        overlay[mask_full == 255] = (0, 255, 0)
        overlay = cv2.addWeighted(bright, 1.0, overlay, 0.5, 0)
        save_image_to_s3(bucket, f"{prefix}/overlay.png", overlay)

        # Ensure mask dimensions match for bitwise_and
        if mask_full.shape[:2] != comp.shape[:2]:
            print(f"[WARN] Mask shape {mask_full.shape} doesn't match comp shape {comp.shape[:2]}, resizing...")
            mask_full = cv2.resize(mask_full, (comp.shape[1], comp.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask_full = mask_full.astype(np.uint8)
        
        # Ensure comp is uint8 for bitwise_and
        comp_uint8 = comp if comp.dtype == np.uint8 else comp.astype(np.uint8)
        
        # Assert mask dimensions and dtype before bitwise_and
        assert mask_full.shape[:2] == comp_uint8.shape[:2], f"Mask shape {mask_full.shape[:2]} doesn't match comp shape {comp_uint8.shape[:2]}"
        assert mask_full.dtype == np.uint8, f"Mask dtype {mask_full.dtype} is not uint8"
        segmented = cv2.bitwise_and(comp_uint8, comp_uint8, mask=mask_full)
        save_image_to_s3(bucket, f"{prefix}/segmented.png", segmented)

        # optional: texture visualization per-plant (uses pdata)
        print("▶ Analyzing texture features")
        try:
            analyze_texture_features(
                pdata,
                key=plant_id,
                s3_bucket=bucket,
                s3_prefix=prefix
            ) #Generates texture images
            print("Texture features analyzed")
        except Exception as e:
            print(f"[WARN] analyze_texture_features failed: {e}")

    # 4) Vegetation indices (over flats) + JSON (commented out for timeline images script)
    print("▶ Computing vegetation Images")
    
    flats = compute_veg_indices(flats, bucket, prefix) #Generates vegetation images
    veg_features = compute_veg_index_features(flats)
    # Save vegetation features JSON to S3 (summary path only)
    try:
        save_json_to_s3(veg_features, bucket, f"{summary_prefix}/vegetation_features.json")
    except Exception as e:
        print(f"[WARN] Could not save vegetation_features.json to summary path: {e}")

    # 5) Aggregate texture features (over flats) + JSON (commented out for timeline images script)
    texture_features = compute_texture_features(flats)
    # Save texture features JSON to S3 (summary path only)
    try:
        save_json_to_s3(texture_features, bucket, f"{summary_prefix}/texture_features.json")
    except Exception as e:
        print(f"[WARN] Could not save texture_features.json to summary path: {e}")

    #6) Morphology (new) — build refined_plants and run (commented out for timeline images script)
    print("▶ Extracting morphology features")
    # We’ll use the single plant_id as the key in refined_plants
    # Pull composite/mask from the (only) flats entry:
    # NOTE: if you ever expand to multiple entries, extend this.
    # any_pdata = next(iter(flats.values()))
    # if "composite" in any_pdata and "mask" in any_pdata:
    #     refined_plants = {
    #         plant_id: {
    #             "composite": any_pdata["composite"],
    #             "mask": any_pdata["mask"],
    #         }
    #     }
    # else:
    #     print("[WARN] Missing composite/mask; skipping morphology.")
    #     refined_plants = {}

    # morph_results = {}
    # if refined_plants:
    morph_results = create_morphology_outputs(flats)

    # Save traits + images to S3
    for pid, mr in morph_results.items():
        # traits JSON (store under crop-level summary path only)
        traits_obj = {
            "size_traits": mr.get("size_traits", {}),
            "morphology_traits": mr.get("morphology_traits", {})
        }
        save_json_to_s3(traits_obj, bucket, f"{summary_prefix}/morphology_traits.json")
        # images
        _ = save_morph_images_to_s3(mr.get("images", {}), bucket, prefix)

    # CSV upload removed per requirements

    print("→ Done.")
    return {
        "vegetation_features": veg_features,
        "texture_features": texture_features,
        "morphology": {pid: {
            "size_traits": mr.get("size_traits", {}),
            "morphology_traits": mr.get("morphology_traits", {})
        } for pid, mr in morph_results.items()},
        "mask_path": f"{prefix}/mask.png",
        "s3_prefix": prefix,
        "summary_prefix": summary_prefix,
        "plant_id": plant_id,
        "date": date,
    }
