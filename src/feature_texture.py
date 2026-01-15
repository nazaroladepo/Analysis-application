import torch
import numpy as np
import cv2
import io
import os
import boto3
from pathlib import Path
from scipy.signal import convolve2d
from sklearn.decomposition import PCA
import torch.nn.functional as F
from src.composite import convert_to_uint8
from skimage.feature import local_binary_pattern, hog
from skimage import exposure
from scipy import ndimage, signal
from torchvision import transforms

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

# Use function to get S3 client instead of global variable
def _get_s3():
    """Lazy initialization of S3 client."""
    if not hasattr(_get_s3, '_client'):
        _get_s3._client = get_s3_client()
    return _get_s3._client

s3 = None  # Will be initialized on first use
def lbp_image(gray, P=8, R=1):
    lbp = local_binary_pattern(gray, P, R, method='uniform')
    return convert_to_uint8(lbp)

def hog_image(gray, orientations=9, pixels_per_cell=(8,8), cells_per_block=(2,2)):
    _, vis = hog(gray,
                 orientations=orientations,
                 pixels_per_cell=pixels_per_cell,
                 cells_per_block=cells_per_block,
                 visualize=True,
                 feature_vector=True)
    return exposure.rescale_intensity(vis, out_range=(0,255)).astype(np.uint8)


# Cell 7: Lacunarity & EHD

from src.DBC_Lacunarity import DBC_Lacunarity

def compute_local_lac(gray, w):
    arr = gray.astype(np.float32)
    m1 = ndimage.uniform_filter(arr, size=w)
    m2 = ndimage.uniform_filter(arr*arr, size=w)
    var = m2 - m1*m1
    eps = 1e-6
    lac = var/(m1*m1+eps) + 1
    lac[m1<=eps] = 0
    return lac

# def compute_three_lac(gray, window=LACUNARITY_WINDOW):
#     L1 = compute_local_lac(gray, window)
#     scales = [max(3,window//2), window, window*2]
#     L2 = np.mean([compute_local_lac(gray,s) for s in scales], axis=0)
#     x = torch.from_numpy(gray.astype(np.float32)/255.0).unsqueeze(0).unsqueeze(0)
#     layer = DBC_Lacunarity(window_size=window).eval()
#     with torch.no_grad():
#         dbc = layer(x).squeeze().cpu().numpy()
#     pad = (window-1)//2
#     L3 = np.pad(dbc, ((pad,pad),(pad,pad)), mode='constant')
#     return convert_to_uint8(L1), convert_to_uint8(L2), convert_to_uint8(L3)
def compute_three_lac(gray, window=15):
    L1 = compute_local_lac(gray, window)
    scales = [max(3, window//2), window, window*2]
    L2 = np.mean([compute_local_lac(gray, s) for s in scales], axis=0)

    # DBC output (no pad)
    x     = torch.from_numpy(gray.astype(np.float32)/255.0)[None,None]
    layer = DBC_Lacunarity(window_size=window).eval()
    with torch.no_grad():
        dbc = layer(x).squeeze().cpu().numpy()

    # Return L3 un–padded (you may need to crop/resize to match L1/L2)
    return convert_to_uint8(L1), convert_to_uint8(L2), convert_to_uint8(dbc)



def Generate_masks(mask_size=3, angle_res=45):
    if mask_size < 3 or mask_size % 2 == 0:
        mask_size += 1
    Gy = np.outer([1, 0, -1], [1, 2, 1])
    if mask_size > 3:
        expd = np.outer([1, 2, 1], [1, 2, 1])
        for _ in range((mask_size - 3) // 2):
            Gy = convolve2d(expd, Gy, mode='full')
    angles = np.arange(0, 360, angle_res)
    masks = np.zeros((len(angles), mask_size, mask_size))
    for i, ang in enumerate(angles):
        masks[i] = __import__('scipy').ndimage.rotate(Gy, ang, reshape=False, mode='nearest')
    return masks

def Get_EHD(X, device=None):
    masks = Generate_masks()
    in_channels = X.shape[1]
    masks = torch.tensor(masks).float().unsqueeze(1).repeat(1, in_channels, 1, 1)
    if device:
        masks = masks.to(device)
    edge_responses = F.conv2d(X, masks, dilation=7)
    value, index = torch.max(edge_responses, dim=1)
    index[value < 0.9] = masks.shape[0]

    feat_vect = []
    for edge in range(masks.shape[0] + 1):
        pooled = F.avg_pool2d((index == edge).unsqueeze(1).float(), [5,5], stride=1, count_include_pad=False)
        feat_vect.append(pooled.squeeze(1))

    feat_vect = torch.stack(feat_vect, dim=1)
    return feat_vect

def save_image_to_s3(bucket, key, img_np, cmap='gray'):
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')

    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(img_np, cmap=cmap)
    ax.axis('off')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    s3_client = _get_s3()
    s3_client.upload_fileobj(buf, bucket, key)

def analyze_texture_features(pdata, key=None, s3_bucket=None, s3_prefix=None):
    if not key:
        raise ValueError("Key (plant identifier) must be provided.")

    bands = ['color', 'nir', 'red_edge', 'red', 'green', 'pca']
    filters = Generate_masks(mask_size=3, angle_res=45)
    pdata['texture_maps'] = {}

    for band in bands:
        if band == 'color':
            comp = pdata['composite']
            mask = pdata.get('mask')
            masked = cv2.bitwise_and(comp, comp, mask=mask) if mask is not None else comp
            orig_img = masked
            gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
        elif band == 'pca':
            stack = []
            mask = pdata.get('mask')
            for b in ['nir', 'red_edge', 'red', 'green']:
                arr = pdata['spectral_stack'][b]
                # Handle different shapes: squeeze only if needed
                if arr.ndim == 3:
                    if arr.shape[2] == 1:
                        arr = arr.squeeze(-1)
                    else:
                        arr = arr[:, :, 0]  # Take first channel
                elif arr.ndim > 3:
                    arr = arr.squeeze()
                arr = arr.astype(float)
                arr_m = np.where(mask > 0, arr, np.nan)
                stack.append(arr_m)
            full = np.stack(stack, axis=-1)
            h, w, c = full.shape
            flat = full.reshape(-1, c)
            valid = ~np.isnan(flat).any(axis=1)
            vec = np.zeros(h*w)
            if valid.sum() > 0:
                vec[valid] = PCA(n_components=1, whiten=True).fit_transform(flat[valid].reshape(-1,c)).squeeze()
            gray_f = vec.reshape(h, w)
            m, M = gray_f[mask>0].min(), gray_f[mask>0].max()
            gray = ((gray_f - m)/(M-m)*255).astype(np.uint8) if M > m else np.zeros_like(gray_f, dtype=np.uint8)
            orig_img = gray
        else:
            arr = pdata['spectral_stack'][band]
            # Handle different shapes: squeeze only if needed
            if arr.ndim == 3:
                if arr.shape[2] == 1:
                    arr = arr.squeeze(-1)
                else:
                    arr = arr[:, :, 0]  # Take first channel
            elif arr.ndim > 3:
                arr = arr.squeeze()
            arr = arr.astype(float)
            mask = pdata.get('mask')
            arr_m = np.where(mask > 0, arr, np.nan)
            m, M = np.nanmin(arr_m), np.nanmax(arr_m)
            gray = ((np.nan_to_num(arr_m, nan=m) - m)/(M-m)*255).astype(np.uint8) if M > m else np.zeros_like(arr_m, dtype=np.uint8)
            orig_img = gray

        lbp_map = lbp_image(gray)
        hog_map = cv2.convertScaleAbs(hog_image(gray))
        lac1, lac2, lac3 = compute_three_lac(gray)

        X = torch.from_numpy(gray.astype(np.float32)/255.0).unsqueeze(0).unsqueeze(0)
        feats = Get_EHD(X)
        ehd_feats = feats.squeeze(0).cpu().numpy()
        ehd_map = np.argmax(ehd_feats, axis=0).astype(np.uint8)

        pdata['texture_maps'][band] = {
            'orig': orig_img, 'gray': gray,
            'lbp': lbp_map, 'hog': hog_map,
            'lac1': lac1, 'lac2': lac2, 'lac3': lac3,
            'ehd_feats': ehd_feats, 'ehd_map': ehd_map
        }

        if s3_bucket and s3_prefix:
            bprefix = f"{s3_prefix}/texture/{band}"
            if band == 'color':
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.imshow(orig_img)
                ax.axis('off')
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                plt.close(fig)
                buf.seek(0)
                s3_client = _get_s3()
                s3_client.upload_fileobj(buf, s3_bucket, f"{bprefix}/orig.png")
            else:
                save_image_to_s3(s3_bucket, f"{bprefix}/orig.png", orig_img, cmap='gray')
            save_image_to_s3(s3_bucket, f"{bprefix}/gray.png", gray, cmap='gray')
            save_image_to_s3(s3_bucket, f"{bprefix}/lbp.png", lbp_map, cmap='gray')
            save_image_to_s3(s3_bucket, f"{bprefix}/hog.png", hog_map, cmap='gray')
            save_image_to_s3(s3_bucket, f"{bprefix}/lac1.png", lac1, cmap='plasma')
            save_image_to_s3(s3_bucket, f"{bprefix}/lac2.png", lac2, cmap='plasma')
            save_image_to_s3(s3_bucket, f"{bprefix}/lac3.png", lac3, cmap='plasma')
            save_image_to_s3(s3_bucket, f"{bprefix}/ehd_map.png", ehd_map, cmap='viridis')

            for i in range(ehd_feats.shape[0]):
                channel = ehd_feats[i]
                rng = np.max(channel) - np.min(channel)
                if rng == 0:
                    ch8 = np.zeros_like(channel, dtype=np.uint8)
                else:
                    ch8 = ((channel - np.min(channel)) / rng * 255).astype(np.uint8)
                save_image_to_s3(s3_bucket, f"{bprefix}//ehd_feat_{i}.png", ch8, cmap='magma')


    return pdata

def compute_texture_features(plants):
    feature_table = []

    for plant_id, pdata in plants.items():
        mask = pdata.get("mask")
        texture_maps = pdata.get("texture_maps")

        if mask is None or texture_maps is None:
            continue

        mask = (mask == 255)
        feature_vector = {"plant_id": str(plant_id)}

        for band, maps in texture_maps.items():
            for key in ['lbp', 'hog', 'lac1', 'lac2', 'lac3']:
                img = maps.get(key)
                if img is None:
                    continue

                # 🔧 Ensure image matches mask size
                if img.shape != mask.shape:
                    img = cv2.resize(img, (mask.shape[1], mask.shape[0]), interpolation=cv2.INTER_NEAREST)

                values = img[mask]
                if values.size == 0:
                    continue

                feature_vector[f"{band}_{key}_mean"] = float(np.nanmean(values))
                feature_vector[f"{band}_{key}_std"] = float(np.nanstd(values))
                feature_vector[f"{band}_{key}_max"] = float(np.nanmax(values))
                feature_vector[f"{band}_{key}_min"] = float(np.nanmin(values))
                feature_vector[f"{band}_{key}_median"] = float(np.nanmedian(values))
                feature_vector[f"{band}_{key}_q25"] = float(np.nanpercentile(values, 25))
                feature_vector[f"{band}_{key}_q75"] = float(np.nanpercentile(values, 75))
                feature_vector[f"{band}_{key}_nan_fraction"] = float(np.isnan(values).sum() / values.size)

        feature_table.append(feature_vector)

    return feature_table
