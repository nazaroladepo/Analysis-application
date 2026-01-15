import os
import numpy as np
from pathlib import Path
from src.composite import convert_to_uint8
import cv2
import boto3
import io
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists() and not os.environ.get("AWS_ACCESS_KEY_ID"):
        load_dotenv(env_file)
except (ImportError, Exception):
    pass


index_cmap_settings = {
    "NDVI": (cm.RdYlGn, -1, 1),
    "GNDVI": (cm.RdYlGn, -1, 1),
    "NDRE": (cm.RdYlGn, -1, 1),
    "GRNDVI": (cm.RdYlGn, -1, 1),
    "TNDVI": (cm.RdYlGn, 0, 1),
    "MGRVI": (cm.RdYlGn, -1, 1),
    "GRVI": (cm.YlGn, 0, None),
    "NGRDI": (cm.RdYlGn, -1, 1),
    "MSAVI": (cm.YlGn, 0, 1),
    "OSAVI": (cm.YlGn, 0, 1),
    "TSAVI": (cm.YlGn, 0, 1),
    "GSAVI": (cm.YlGn, 0, 1),
    "GOSAVI": (cm.YlGn, 0, 1),
    "GDVI": (cm.Greens, 0, None),
    "NDWI": (cm.Blues, -1, 1),
    "DSWI4": (cm.Blues, 0, None),
    "CIRE": (cm.viridis, 0, 10),
    "LCI": (cm.RdYlGn, -1, 1),
    "CIgreen": (cm.viridis, 0, 5),
    "MCARI": (cm.viridis, 0, 1.5),
    "MCARI1": (cm.viridis, -2, 2),
    "MCARI2": (cm.viridis, 0, 1.5),
    "MTVI1": (cm.viridis, -2, 2),
    "MTVI2": (cm.viridis, 0, 1.5),
    "CVI": (cm.plasma, 0, 10),
    "ARI": (cm.magma, 0, 1),
    "ARI2": (cm.magma, 0, None),
    "DVI": (cm.Greens, 0, None),
    "WDVI": (cm.Greens, 0, None),
    "SR": (cm.viridis, 0, 10),
    "MSR": (cm.viridis, 0, 5),
    "PVI": (cm.cividis, None, None),
    "GEMI": (cm.cividis, 0, 1),
    "ExR": (cm.Reds, -1, 1),
    "RI": (cm.Reds, -1, 1),
    "RRI1": (cm.Reds, 0, 10),
    "RRI2": (cm.Reds, 0, 10),
    "RRI": (cm.Reds, 0, 10),
    "AVI": (cm.magma, 0, 1),
    "SIPI2": (cm.inferno, 0, 1),
    "TCARI": (cm.viridis, 0, 2),
    "TCARIOSAVI": (cm.viridis, 0, 1),
    "CCCI": (cm.plasma, 0, 2),
    "RDVI": (cm.RdYlGn, 0, None),
    "NLI": (cm.cividis, 0, 1),
    "BIXS": (cm.plasma, 0, None),
    "IPVI": (cm.YlGn, 0, 1),
    "EVI2": (cm.RdYlGn, 0, 2)
}



# Save image to S3 helper
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

def save_index_to_s3(bucket, key, image_np):
    s3 = get_s3_client()
    success, encoded_img = cv2.imencode('.png', image_np)
    if success:
        s3.upload_fileobj(io.BytesIO(encoded_img.tobytes()), bucket, key)

def save_image_to_s3(bucket, key, img_np, cmap_name='viridis', title=None):
    cmap, vmin, vmax = index_cmap_settings.get(title, (cm.viridis, np.nanmin(img_np), np.nanmax(img_np)))
    
    # Handle None ranges
    if vmin is None:
        vmin = np.nanmin(img_np)
    if vmax is None:
        vmax = np.nanmax(img_np)

    # Normalize and apply colormap (set background NaNs to white)
    norm = Normalize(vmin=vmin, vmax=vmax)
    colored = cmap(norm(img_np))
    colored[np.isnan(img_np)] = [1, 1, 1, 1]  # White background for NaNs

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow(colored)
    ax.axis('off')

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.046, pad=0.04)
    cbar.set_label(title)

    buf = io.BytesIO()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    s3 = get_s3_client()
    s3.upload_fileobj(buf, bucket, key)

# Vegetation Indices
epsilon = 1e-10
soil_factor = 0.16

VEG_INDEX_FORMULAS = {
    "NDVI": lambda nir, red: (nir - red) / (nir + red + epsilon),
    "GNDVI": lambda nir, green: (nir - green) / (nir + green + epsilon),
    "NDRE": lambda nir, red_edge: (nir - red_edge) / (nir + red_edge + epsilon),
    "GRNDVI": lambda nir, green, red: (nir - (green + red)) / (nir + (green + red) + epsilon),
    "TNDVI": lambda nir, red: np.sqrt(np.clip(((nir - red) / (nir + red + epsilon)) + 0.5, 0, None)),
    "MGRVI": lambda green, red: (green**2 - red**2) / (green**2 + red**2 + epsilon),
    "GRVI": lambda nir, green: nir / (green + epsilon),
    "NGRDI": lambda green, red: (green - red) / (green + red + epsilon),
    "MSAVI": lambda nir, red: 0.5 * (2.0 * nir + 1 - np.sqrt((2 * nir + 1)**2 - 8 * (nir - red))),
    "OSAVI": lambda nir, red: (nir - red) / (nir + red + soil_factor + epsilon),
    "TSAVI": lambda nir, red, s=0.33, a=0.5, X=1.5: (s * (nir - s * red - a)) / (a * nir + red - a * s + X * (1 + s**2) + epsilon),
    "GSAVI": lambda nir, green, l=0.5: (1 + l) * (nir - green) / (nir + green + l + epsilon),
    "GOSAVI": lambda nir, green: (nir - green) / (nir + green + 0.16 + epsilon),
    "GDVI": lambda nir, green: nir - green,
    "NDWI": lambda green, nir: (green - nir) / (green + nir + epsilon),
    "DSWI4": lambda green, red: green / (red + epsilon),
    "CIRE": lambda nir, red_edge: (nir / (red_edge + epsilon)) - 1.0,
    "LCI": lambda nir, red_edge: (nir - red_edge) / (nir + red_edge + epsilon),
    "CIgreen": lambda nir, green: (nir / (green + epsilon)) - 1,
    "MCARI": lambda red_edge, red, green: ((red_edge - red) - 0.2 * (red_edge - green)) * (red_edge / (red + epsilon)),
    "MCARI1": lambda nir, red, green: 1.2 * (2.5 * (nir - red) - 1.3 * (nir - green)),
    "MCARI2": lambda nir, red, green: (1.5 * (2.5 * (nir - red) - 1.3 * (nir - green))) / np.sqrt((2 * nir + 1)**2 - (6 * nir - 5 * np.sqrt(red + epsilon))),
    "MTVI1": lambda nir, red, green: 1.2 * (1.2 * (nir - green) - 2.5 * (red - green)),
    "MTVI2": lambda nir, red, green: (1.5 * (1.2 * (nir - green) - 2.5 * (red - green))) / np.sqrt((2 * nir + 1)**2 - (6 * nir - 5 * np.sqrt(red + epsilon)) - 0.5 + epsilon),
    "CVI": lambda nir, red, green: (nir * red) / (green**2 + epsilon),
    "ARI": lambda green, red_edge: (1.0 / (green + epsilon)) - (1.0 / (red_edge + epsilon)),
    "ARI2": lambda nir, green, red_edge: nir * (1.0 / (green + epsilon)) - nir * (1.0 / (red_edge + epsilon)),
    "DVI": lambda nir, red: nir - red,
    "WDVI": lambda nir, red, a=0.5: nir - a * red,
    "SR": lambda nir, red: nir / (red + epsilon),
    "MSR": lambda nir, red: (nir / (red + epsilon) - 1) / np.sqrt(nir / (red + epsilon) + 1),
    "PVI": lambda nir, red, a=0.5, b=0.3: (nir - a * red - b) / (np.sqrt(1 + a**2) + epsilon),
    "GEMI": lambda nir, red: ((2 * (nir**2 - red**2) + 1.5 * nir + 0.5 * red) / (nir + red + 0.5 + epsilon)) * (1 - 0.25 * ((2 * (nir**2 - red**2) + 1.5 * nir + 0.5 * red) / (nir + red + 0.5 + epsilon))) - ((red - 0.125) / (1 - red + epsilon)),
    "ExR": lambda red, green: 1.3 * red - green,
    "RI": lambda red, green: (red - green) / (red + green + epsilon),
    "RRI1": lambda nir, red_edge: nir / (red_edge + epsilon),
    "RRI2": lambda red_edge, red: red_edge / (red + epsilon),
    "RRI": lambda nir, red_edge: nir / (red_edge + epsilon),
    "AVI": lambda nir, red: np.cbrt(nir * (1.0 - red) * (nir - red + epsilon)),
    "SIPI2": lambda nir, green, red: (nir - green) / (nir - red + epsilon),
    "TCARI": lambda red_edge, red, green: 3 * ((red_edge - red) - 0.2 * (red_edge - green) * (red_edge / (red + epsilon))),
    "TCARIOSAVI": lambda red_edge, red, green, nir: (3 * (red_edge - red) - 0.2 * (red_edge - green) * (red_edge / (red + epsilon))) / (1 + 0.16 * ((nir - red) / (nir + red + 0.16 + epsilon))),
    "CCCI": lambda nir, red_edge, red: (((nir - red_edge) * (nir + red)) / ((nir + red_edge) * (nir - red) + epsilon)),
    "RDVI": lambda nir, red: (nir - red) / (np.sqrt(nir + red + epsilon)),
    "NLI": lambda nir, red: ((nir**2) - red) / ((nir**2) + red + epsilon),
    "BIXS": lambda green, red: np.sqrt(((green**2) + (red**2)) / 2.0),
    "IPVI": lambda nir, red: nir / (nir + red + epsilon),
    "EVI2": lambda nir, red: 2.4 * (nir - red) / (nir + red + 1.0 + epsilon)
}
# --- 9b. Required bands for each index ---
# Keys must match VEG_INDEX_FORMULAS
# --- Mapping: Vegetation Index -> Required Spectral Bands ---
VEG_INDEX_CHANNELS = {
    "NDVI": ["nir", "red"],
    "GNDVI": ["nir", "green"],
    "NDRE": ["nir", "red_edge"],
    "GRNDVI": ["nir", "green", "red"],
    "TNDVI": ["nir", "red"],
    "MGRVI": ["green", "red"],
    "GRVI": ["nir", "green"],
    "NGRDI": ["green", "red"],
    "MSAVI": ["nir", "red"],
    "OSAVI": ["nir", "red"],
    "TSAVI": ["nir", "red"],
    "GSAVI": ["nir", "green"],
    "GOSAVI": ["nir", "green"],
    "GDVI": ["nir", "green"],
    "NDWI": ["green", "nir"],
    "DSWI4": ["green", "red"],
    "CIRE": ["nir", "red_edge"],
    "LCI": ["nir", "red_edge"],
    "CIgreen": ["nir", "green"],
    "MCARI": ["red_edge", "red", "green"],
    "MCARI1": ["nir", "red", "green"],
    "MCARI2": ["nir", "red", "green"],
    "MTVI1": ["nir", "red", "green"],
    "MTVI2": ["nir", "red", "green"],
    "CVI": ["nir", "red", "green"],
    "ARI": ["green", "red_edge"],
    "ARI2": ["nir", "green", "red_edge"],
    "DVI": ["nir", "red"],
    "WDVI": ["nir", "red"],
    "SR": ["nir", "red"],
    "MSR": ["nir", "red"],
    "PVI": ["nir", "red"],
    "GEMI": ["nir", "red"],
    "ExR": ["red", "green"],
    "RI": ["red", "green"],
    "RRI1": ["nir", "red_edge"],
    "RRI2": ["red_edge", "red"],
    "RRI": ["nir", "red_edge"],
    "AVI": ["nir", "red"],
    "SIPI2": ["nir", "green", "red"],
    "TCARI": ["red_edge", "red", "green"],
    "TCARIOSAVI": ["red_edge", "red", "green", "nir"],
    "CCCI": ["nir", "red_edge", "red"],
    "RDVI": ["nir", "red"],
    "NLI": ["nir", "red"],
    "BIXS": ["green", "red"],
    "IPVI": ["nir", "red"],
    "EVI2": ["nir", "red"]
}

def compute_veg_indices(plants, s3_bucket=None, s3_prefix=None):

    for p, d in plants.items():
        spec, mask = d.get("spectral_stack"), d.get("mask")
        if spec is None or mask is None:
            continue

        raw, disp = {}, {}

        for idx, func in VEG_INDEX_FORMULAS.items():
            bands = VEG_INDEX_CHANNELS.get(idx)
            if bands is None:
                continue
            try:
                # Handle different shapes: squeeze only if needed
                vals = []
                for b in bands:
                    arr = spec[b]
                    if arr.ndim == 3:
                        if arr.shape[2] == 1:
                            arr = arr.squeeze(-1)
                        else:
                            arr = arr[:, :, 0]  # Take first channel
                    elif arr.ndim > 3:
                        arr = arr.squeeze()
                    vals.append(arr)
            except KeyError:
                continue

            arr = func(*vals)
            masked = np.where(mask == 255, arr, np.nan)
            img8 = convert_to_uint8(masked)
            raw[idx], disp[idx] = masked, img8

            if s3_bucket and s3_prefix:
                s3_key = f"{s3_prefix}/vegetation_indices/{idx}.png"
                save_image_to_s3(s3_bucket, s3_key, masked, cmap_name=idx, title=idx)

        d["vegetation_indices"] = disp
        d["original_index_values"] = raw

    return plants

def compute_veg_index_features(plants):
    feature_table = []
    for plant_id, data in plants.items():
        mask = data.get("mask")
        indices = data.get("original_index_values")
        if mask is None or indices is None:
            continue
        mask = (mask == 255)
        for idx_name, idx_array in indices.items():
            if idx_array is None:
                continue
            values = idx_array[mask]
            if values.size == 0:
                continue
            feature_table.append({
                "index": idx_name,
                "mean": float(np.nanmean(values)),
                "std": float(np.nanstd(values)),
                "max": float(np.nanmax(values)),
                "min": float(np.nanmin(values)),
                "median": float(np.nanmedian(values)),
                "q25": float(np.nanpercentile(values, 25)),
                "q75": float(np.nanpercentile(values, 75)),
                "nan_fraction": float(np.isnan(values).sum() / values.size)
            })
    return feature_table
