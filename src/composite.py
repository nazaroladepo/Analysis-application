# Cell 4: Composite & Spectral Stack
import numpy as np
from itertools import product

def convert_to_uint8(arr):
    a = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    norm = (a - a.min()) / (np.ptp(a) + 1e-6) * 255
    return norm.astype(np.uint8)


def process_raw_image(pil_img):
    """
    Process raw image for Mullet or other crops.
    Handles RGB images that might be single-band saved as RGB (like Mullet data).
    """
    # Handle RGB images (like Dr. Mullet's dataset) - check if all channels are identical
    img_arr = np.array(pil_img)
    
    # If image is RGB/RGBA, check if it's actually a single-band image saved as RGB
    if len(img_arr.shape) == 3 and img_arr.shape[2] >= 3:
        # Check if R, G, B channels are identical (single band saved as RGB)
        if np.allclose(img_arr[:, :, 0], img_arr[:, :, 1]) and np.allclose(img_arr[:, :, 1], img_arr[:, :, 2]):
            # Convert to grayscale
            pil_img = pil_img.convert('L')
        elif pil_img.mode in ('RGB', 'RGBA', 'P'):
            # For palette mode or if channels differ, try converting to grayscale
            pil_img = pil_img.convert('L')
    
    # Now process as single-band image - split into 4 quadrants for 4 bands
    d = pil_img.size[0] // 2
    boxes = [(j, i, j + d, i + d) for i, j in product(range(0, pil_img.height, d), range(0, pil_img.width, d))]
    
    # Extract tiles and ensure they're 2D arrays
    tiles = []
    for box in boxes:
        tile = np.array(pil_img.crop(box), dtype=float)
        # Ensure tile is 2D (height, width)
        if tile.ndim > 2:
            # If multi-dimensional, take first channel or convert to grayscale
            tile = tile[:, :, 0] if tile.ndim == 3 else tile.squeeze()
        tiles.append(tile)
    
    # Stack tiles along a new axis (creates 3D: height, width, 4_bands)
    stack = np.stack(tiles, axis=-1)
    
    # Ensure we have exactly 4 bands
    if stack.shape[-1] != 4:
        # If we don't have 4 bands, pad or repeat the last band
        if stack.shape[-1] < 4:
            num_missing = 4 - stack.shape[-1]
            last_band = stack[:, :, -1:]
            padding = np.repeat(last_band, num_missing, axis=-1)
            stack = np.concatenate([stack, padding], axis=-1)
        else:
            # If more than 4, take first 4
            stack = stack[:, :, :4]
    
    # Split into 4 bands: [green, red, red_edge, nir]
    green, red, red_edge, nir = np.split(stack, 4, axis=-1)
    
    # Build pseudo-RGB composite as (green, red_edge, red) - matching reference pipeline
    composite = np.concatenate([green, red_edge, red], axis=-1)
    composite_uint8 = convert_to_uint8(composite)
    
    # Prepare spectral stack (ensure 2D format by squeezing last dimension)
    spectral_bands = {
        "green": green.squeeze(-1) if green.ndim == 3 and green.shape[2] == 1 else green,
        "red": red.squeeze(-1) if red.ndim == 3 and red.shape[2] == 1 else red,
        "red_edge": red_edge.squeeze(-1) if red_edge.ndim == 3 and red_edge.shape[2] == 1 else red_edge,
        "nir": nir.squeeze(-1) if nir.ndim == 3 and nir.shape[2] == 1 else nir
    }
    
    return composite_uint8, spectral_bands

# def create_composites(plants):
#     """
#     For each plant, take the first raw image (frame5), generate a pseudo-RGB composite
#     and store both the 8-bit composite and the full spectral stack.
#     """
#     for p, d in plants.items():
#         if not d.get("raw_images"):  # skip if no images
#             continue
#         im, _ = d["raw_images"][0]
#         comp, spec = process_raw_image(im)
#         d["composite"] = comp           # pseudo-RGB BGR-ready composite
#         d["spectral_stack"] = spec      # dict of raw bands
#     return plants
def create_composites(plants):
    """
    For each item in `plants` (whether flat or grouped),
    grab exactly one raw image and produce:
      pdata["composite"]      = 8-bit BGR numpy array
      pdata["spectral_stack"] = whatever your process_raw_image returns
    """
    for key, pdata in plants.items():
        # 1) find the PIL.Image in either flat or grouped fields
        if "raw_image" in pdata:
            im, _ = pdata["raw_image"]
        elif pdata.get("raw_images"):
            im, _ = pdata["raw_images"][0]
        else:
            # nothing to do here
            continue

        # 2) process it
        comp, spec = process_raw_image(im)

        # 3) attach exactly these two keys
        pdata["composite"]      = comp
        pdata["spectral_stack"] = spec

    return plants
