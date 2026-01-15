import os
import glob
import json
import numpy as np
import cv2
import boto3
from pathlib import Path
from PIL import Image
import io

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists() and not os.environ.get("AWS_ACCESS_KEY_ID"):
        load_dotenv(env_file)
except (ImportError, Exception):
    pass

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

def load_single_frame_from_s3(bucket, key):
    """
    Load a single image from S3 and return it as a PIL Image (without converting color).
    """
    s3 = get_s3_client()
    response = s3.get_object(Bucket=bucket, Key=key)
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    return image


def load_selected_frame_flat(input_root_folder):
    """
    Load frames per plant across all dates, flattening so each
    dict key is YYYY_MM_DD_plantX_frameY and each value is:
      {'raw_image': (PIL.Image, filename)}

    Respects your same substitutes, frame_overrides, and multi-frame sets.
    """
    substitutes = {
        'plant16': 'plant15', 'plant15': 'plant14', 'plant14': 'plant13',
        'plant13': 'plant13', 'plant33': 'plant34', 'plant34': 'plant35',
        'plant24': 'plant25', 'plant25': 'plant25', 'plant35': 'plant36',
        'plant36': 'plant37', 'plant37': 'plant37', 'plant44': 'plant43',
        'plant45': 'plant44',
    }
    frame_override = {
        'plant1':'9','plant2':'10','plant3':'9','plant5':'7','plant6':'9', 'plant8':'5',
        'plant7':'9','plant10':'9','plant11':'9','plant12':'9',
        'plant13':'10','plant14':'8','plant15':'11','plant19':'4','plant20':'7',
        'plant21':'9','plant22':'10','plant25':'4','plant26':'2','plant27':'10','plant28':'9','plant29':'2',
        'plant30':'9','plant31':'10','plant32':'9','plant33':'8',
        'plant35':'9','plant36':'4','plant38':'9','plant39':'9','plant41':'9',
        'plant42':'6','plant43':'10','plant44':'9','plant45':'7',
        'plant47':'10','plant48':'11',
    }
    

    flat = {}
    for date in sorted(os.listdir(input_root_folder)):
        date_path = os.path.join(input_root_folder, date)
        if not os.path.isdir(date_path):
            continue

        # switch dashes → underscores for key
        date_key = date.replace('-', '_')

        for plant in sorted(os.listdir(date_path)):
            plant_path = os.path.join(date_path, plant)
            if not os.path.isdir(plant_path):
                continue

            source = substitutes.get(plant, plant)

            
            frames = [int(frame_override.get(plant, '8'))]

            for f in frames:
                fn = f"{source}_frame{f}.tif"
                fp = os.path.join(date_path, source, fn)
                if os.path.exists(fp):
                    try:
                        img = Image.open(fp)
                        key = f"{date_key}_{plant}_frame{f}"
                        flat[key] = {'raw_image': (img, fn)}
                    except Exception as e:
                        print(f"❌ Failed to load {fp}: {e}")
                else:
                    print(f"⚠ Missing {fn} in {os.path.join(date_path, source)}")

    return flat