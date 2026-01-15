# src/morphology.py
import os, sys, cv2, contextlib
import numpy as np
import matplotlib
matplotlib.use("Agg")  # safe for headless servers
import matplotlib.pyplot as plt
from plantcv import plantcv as pcv
import os
# -----------------------------
# Global PCV params
# -----------------------------
pcv.params.debug = None
pcv.params.text_size = 0.7
pcv.params.text_thickness = 2
pcv.params.line_thickness = 3
pcv.params.dpi = 100

# Pixel-to-centimeter scale (update if your calibration changes)
OFFSET = 0.1099609375  # px -> cm

# -----------------------------
# Utilities
# -----------------------------
def preprocess_mask(mask, kernel_size: int = 7, min_area: int = 1000):
    """Return a clean binary (0/255, uint8) mask."""
    if mask is None:
        return None
    if isinstance(mask, tuple):
        mask = mask[0]
    # to binary 0/255
    mask = ((mask.astype(np.int32) > 0).astype(np.uint8)) * 255
    # opening
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # remove small CCs
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    clean = np.zeros_like(opened)
    for lbl in range(1, num_labels):  # skip background
        if stats[lbl, cv2.CC_STAT_AREA] >= min_area:
            clean[labels == lbl] = 255
    return clean


def sanitize_image_for_pcv(img):
    """Ensure 3-channel uint8 RGB for pcv.analyze.size."""
    if img is None:
        return None
    if isinstance(img, tuple):
        img = img[0]
    arr = img
    if arr.ndim == 2:
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    elif arr.ndim == 3 and arr.shape[2] == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
    elif arr.ndim == 3 and arr.shape[2] == 3:
        pass
    else:
        # unsupported shape
        return None
    if arr.dtype != np.uint8:
        # robust convert to 0-255
        a = arr.astype(np.float32)
        mn, mx = np.nanmin(a), np.nanmax(a)
        if mx > mn:
            a = (a - mn) / (mx - mn)
        a = np.clip(a * 255.0, 0, 255).astype(np.uint8)
        arr = a
    return arr


class FilteredStream:
    """Filter noisy PlantCV prints (optional)."""
    def __init__(self, stream): self.stream = stream
    def write(self, msg):
        skip = ("got pruned", "Slope of contour", "cannot be plotted")
        if not any(s in msg for s in skip):
            self.stream.write(msg)
    def flush(self):
        try: self.stream.flush()
        except Exception: pass


def _safe_fill_segments(mask, objects):
    """Colored overlay of segments; returns uint8 RGB image."""
    overlay = np.zeros((*mask.shape, 3), dtype=np.uint8)
    if not objects:
        return overlay
    cmap = plt.get_cmap("hsv", len(objects))
    for i, cnt in enumerate(objects):
        color = tuple((np.array(cmap(i)[:3]) * 255).astype(np.uint8).tolist())
        cv2.drawContours(overlay, [cnt], -1, color, thickness=cv2.FILLED)
    return overlay


def _reset_pcv_outputs():
    """Avoid leakage of previous observations/images."""
    try:
        if hasattr(pcv.outputs, "clear"):
            pcv.outputs.clear()
        elif hasattr(pcv.outputs, "reset"):
            pcv.outputs.reset()
    except Exception:
        pass


def _first_obs_label():
    """Find the first available label in pcv.outputs.observations."""
    obs = getattr(pcv, "outputs", None)
    obs_dict = getattr(obs, "observations", {}) if obs is not None else {}
    # Prefer default_1, fall back to any
    if "default_1" in obs_dict:
        return "default_1", obs_dict
    if "default" in obs_dict:
        return "default", obs_dict
    # otherwise, take first key if any
    if obs_dict:
        return next(iter(obs_dict.keys())), obs_dict
    return None, {}


# -----------------------------
# Main worker
# -----------------------------
def create_morphology_outputs(refined_plants: dict):
    """
    Compute per-plant morphology + size features and diagnostic images.

    Args:
        refined_plants: dict mapping plant_id -> {
            "composite": HxWx3 uint8 RGB,
            "mask": HxW uint8 {0,255},
        }

    Returns:
        dict mapping plant_id -> {
          "size_traits": {...},
          "morphology_traits": {...},
          "images": { name: np.uint8 image, ... }
        }
    """
    results = {}
    for plant_id, pdata in refined_plants.items():
        print(f"▶ Processing {plant_id}...")
        _reset_pcv_outputs()

        try:
            # --- get & sanitize inputs
            img_raw = pdata.get("composite")
            mask_raw = pdata.get("mask")
            
            # Validate inputs
            if img_raw is None or mask_raw is None:
                print(f"⚠ Skipping {plant_id}: missing composite or mask")
                results[plant_id] = {"size_traits": {}, "morphology_traits": {}, "images": {}}
                continue
            
            # Ensure img_raw is uint8 (properly normalize 16-bit/float images)
            if img_raw.dtype != np.uint8:
                print(f"[WARN] Converting composite from {img_raw.dtype} to uint8")
                if img_raw.max() > 255 or img_raw.dtype in [np.uint16, np.float32, np.float64]:
                    # Normalize 16-bit or float images to 0-255 range
                    img_raw = cv2.normalize(img_raw, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                else:
                    img_raw = img_raw.astype(np.uint8)
            
            # Ensure mask_raw is 2D uint8 and matches image dimensions
            if len(mask_raw.shape) > 2:
                mask_raw = mask_raw[:, :, 0] if mask_raw.shape[2] == 1 else cv2.cvtColor(mask_raw, cv2.COLOR_BGR2GRAY)
            if mask_raw.dtype != np.uint8:
                if mask_raw.max() > 255 or mask_raw.dtype in [np.uint16, np.float32, np.float64]:
                    mask_raw = cv2.normalize(mask_raw, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                else:
                    mask_raw = mask_raw.astype(np.uint8)
            
            # Resize mask if dimensions don't match image
            img_h, img_w = img_raw.shape[:2]
            mask_h, mask_w = mask_raw.shape[:2]
            if (mask_h, mask_w) != (img_h, img_w):
                print(f"[WARN] Resizing mask from {mask_raw.shape} to match image {img_raw.shape[:2]}")
                mask_raw = cv2.resize(mask_raw, (img_w, img_h), interpolation=cv2.INTER_NEAREST)
            
            #change img_raw to rgb
            img_raw = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
            #mask out img_raw using mask_raw
            img_raw = cv2.bitwise_and(img_raw, img_raw, mask=mask_raw)
            img = img_raw
            mask = mask_raw
            print(f"processing {plant_id} image and mask") 
            # mask = preprocess_mask(mask_raw, kernel_size=7, min_area=1000)

            # if img is None or mask is None:
            #     print(f"⚠ Skipping {plant_id}: invalid composite/mask.")
            #     results[plant_id] = {"size_traits": {}, "morphology_traits": {}, "images": {}}
            #     continue

            with contextlib.redirect_stdout(FilteredStream(sys.stdout)), \
                 contextlib.redirect_stderr(FilteredStream(sys.stderr)):

                # --- skeletonize
                skeleton = pcv.morphology.skeletonize(mask=mask)

                # --- prune: sequence to reduce tip explosion
                prune_sizes = [200, 100, 50, 30, 10]
                pruned_skel = skeleton
                pruned_imgs = {}
                edge_objects = None

                for s in prune_sizes:
                    pruned_skel, pruned_img, edge_objects = pcv.morphology.prune(
                        skel_img=pruned_skel, size=s, mask=mask
                    )
                    pruned_imgs[f"pruned_{s}"] = pruned_img

                edge_objects = list(edge_objects) if edge_objects is not None else []

                # --- branch/tip detection
                branch_pts_img = pcv.morphology.find_branch_pts(pruned_skel, mask)
                try:
                    tip_pts_img = pcv.morphology.find_tips(pruned_skel, mask)
                except Exception as e:
                    tip_pts_img = None
                    if "Too many tips" in str(e):
                        print(f"ℹ Tips skipped ({plant_id}): too many tips after pruning.")
                    else:
                        print(f"ℹ Tips skipped ({plant_id}): {e}")

                # --- segment objects (stem merging may fail)
                try:
                    leaf_obj, stem_obj = pcv.morphology.segment_sort(pruned_skel, edge_objects, mask)
                except Exception as e:
                    leaf_obj, stem_obj = [], []
                    print(f"ℹ segment_sort skipped ({plant_id}): {e}")

                segmented_id_img = None
                if leaf_obj:
                    segmented_id_img, _ = pcv.morphology.segment_id(pruned_skel, leaf_obj, mask)
                # Downsize parameters to make annotations more readable 
                pcv.params.text_size = 2
                pcv.params.text_thickness = 3
                pcv.params.line_thickness = 10
                path_lengths_img = (pcv.morphology.segment_path_length(segmented_id_img, leaf_obj)
                                    if segmented_id_img is not None else None)
                euclidean_lengths_img = (pcv.morphology.segment_euclidean_length(segmented_id_img, leaf_obj)
                                    if segmented_id_img is not None else None)
                curvature_img = (pcv.morphology.segment_curvature(segmented_id_img, leaf_obj)
                                    if segmented_id_img is not None else None)
                angles_img = (pcv.morphology.segment_angle(segmented_id_img, leaf_obj)
                                    if segmented_id_img is not None else None)
                tangent_angles_img = (pcv.morphology.segment_tangent_angle(segmented_id_img, leaf_obj, size=15)
                                    if segmented_id_img is not None else None)

                insertion_angles_img = None
                if leaf_obj and stem_obj and segmented_id_img is not None:
                    try:
                        insertion_angles_img = pcv.morphology.segment_insertion_angle(
                            pruned_skel, segmented_id_img, leaf_obj, stem_obj, size=20
                        )
                    except Exception as e:
                        print(f"ℹ insertion_angle skipped ({plant_id}): {e}")

                # --- size analysis (labels + analyze.size)
                labeled_mask, n_labels = pcv.create_labels(mask)
                size_analysis_img = pcv.analyze.size(img, labeled_mask, n_labels, label="default")

            # -----------------------------
            # Gather observations (robust)
            # -----------------------------
            label, obs_dict = _first_obs_label()
            size_traits = {}
            if label:
                traits_to_convert = {
                    "area", "perimeter", "width", "height",
                    "longest_path", "ellipse_major_axis", "ellipse_minor_axis"
                }
                for trait, info in obs_dict.get(label, {}).items():
                    if trait in ("in_bounds", "object_in_frame"):
                        continue
                    val = info.get("value", None)
                    if val is None:
                        continue
                    if trait in traits_to_convert:
                        val = (val * (OFFSET**2)) if trait == "area" else (val * OFFSET)
                    size_traits[trait] = val

            # counts (leaf/stem objects)
            try:
                size_traits["num_leaves"] = len(leaf_obj) if 'leaf_obj' in locals() and leaf_obj is not None else 0
                size_traits["num_branches"] = len(stem_obj) if 'stem_obj' in locals() and stem_obj is not None else 0
            except Exception:
                size_traits["num_leaves"] = 0
                size_traits["num_branches"] = 0

            # morphology traits (if any were recorded under "default")
            morphology_traits = {}
            if "default" in obs_dict:
                for trait, info in obs_dict["default"].items():
                    v = info.get("value", None)
                    if isinstance(v, (list, tuple)):
                        v = "; ".join(map(str, v))
                    morphology_traits[trait] = v

            # --- images (drop None)
            images = {
                "skeleton": skeleton,
                "branch_pts": branch_pts_img,
                "tip_pts": tip_pts_img,
                "segmented_id": segmented_id_img,
                "path_lengths": path_lengths_img,
                "euclidean_lengths": euclidean_lengths_img,
                "curvature": curvature_img,
                "angles": angles_img,
                "tangent_angles": tangent_angles_img,
                "insertion_angles": insertion_angles_img,
                "size_analysis": size_analysis_img,
                "filled_segments": _safe_fill_segments(mask, edge_objects),
            }
            images.update({k: v for k, v in (pruned_imgs or {}).items()})
            images = {k: v for k, v in images.items() if v is not None}

            results[plant_id] = {
                "size_traits": size_traits,
                "morphology_traits": morphology_traits,
                "images": images,
            }
            print(f"✅ {plant_id}")
        except Exception as e:
            # Never break the batch
            print(f"⚠ Feature error in {plant_id}: {e}")
            results[plant_id] = {"size_traits": {}, "morphology_traits": {}, "images": {}}

    return results


# -----------------------------
# Backward-compat wrapper (optional)
# -----------------------------
def detect_and_return_morphology(img, mask):
    """
    Compatibility shim for legacy callers.
    Returns a flat dict of traits (size + morphology) for a single image/mask.
    """
    rp = {"tmp": {"composite": img, "mask": mask}}
    out = create_morphology_outputs(rp).get("tmp", {})
    return {**out.get("size_traits", {}), **out.get("morphology_traits", {})}
