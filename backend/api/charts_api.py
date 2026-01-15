# charts_api.py
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import date

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from backend.db.database import get_db
from backend.db.models import (
    ProcessedData, 
    VegetationIndexTimeline, 
    TextureTimeline, 
    MorphologyTimeline,
    Plant
)

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Path to CSV files (relative to project root)
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "charts"
GENOTYPE_CSV = SCRIPT_DIR / "GENOTYPE_MAPPING_USED.csv"


def genotype_to_label(g: Any) -> str:
    """Convert genotype number to label"""
    try:
        gi = int(g)
    except (ValueError, TypeError):
        return "NT"
    if gi == 8 or gi == 0:
        return "NT"
    return f"group{gi}"


def safe_float(value: Any) -> float:
    """Convert value to float, replacing NaN/Inf with 0.0 for JSON compliance"""
    try:
        val = float(value)
        if not np.isfinite(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0


@router.get("/charts/genotype-mapping")
def get_genotype_mapping():
    """Get genotype mapping from CSV file"""
    try:
        if not GENOTYPE_CSV.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Genotype mapping file not found: {GENOTYPE_CSV}"
            )
        
        df = pd.read_csv(str(GENOTYPE_CSV))
        mapping = df.rename(columns={"Plant_Name": "plant"})
        mapping["mutation"] = mapping["Genotype"].apply(genotype_to_label)
        
        return {
            "mapping": mapping[["plant", "Plant_Number", "Genotype", "mutation"]].to_dict("records")
        }
    except Exception as e:
        logger.error(f"Error reading genotype mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading genotype mapping: {str(e)}")


def aggregate_database_to_unified_format(db: Session, species: Optional[str] = None) -> pd.DataFrame:
    """
    Aggregate all database records into unified wide format matching CSV structure.
    Returns DataFrame with one row per plant/date with all features.
    
    Args:
        db: Database session
        species: Optional species name to filter by (e.g., "Sorghum", "Cotton", "Corn")
    """
    logger.info(f"Aggregating database records to unified format{' (filtered by species: ' + species + ')' if species else ''}...")
    
    # Get processed data, optionally filtered by species
    query = db.query(ProcessedData)
    if species:
        # Filter by species through the Plant relationship
        query = query.join(Plant).filter(Plant.species == species)
    all_processed = query.all()
    logger.info(f"Found {len(all_processed)} processed data records")
    
    rows = []
    
    for proc in all_processed:
        # Extract plant_id and date from processed_data.id (format: species_plant_id_date)
        # Example: "Sorghum_plant1_2024-12-04"
        parts = proc.id.split('_')
        if len(parts) < 3:
            continue
        
        # Last part is date (format: YYYY-MM-DD)
        date_str = parts[-1]
        # Everything before last part is species_plant_id
        plant_id_full = '_'.join(parts[:-1])
        
        # Extract just plant_id (remove species prefix if present)
        plant_id_short = plant_id_full
        if '_' in plant_id_full:
            # Split by first underscore to separate species and plant_id
            plant_id_parts = plant_id_full.split('_', 1)
            if len(plant_id_parts) > 1:
                plant_id_short = plant_id_parts[1]  # Get plant_id part
        
        # Create base row
        row = {
            'date_key': date_str,
            'plant': plant_id_short,
            'plant_num': None,  # Will be filled from genotype mapping
        }
        
        # Add vegetation features from VegetationIndexTimeline
        veg_data = db.query(VegetationIndexTimeline).filter(
            VegetationIndexTimeline.plant_id == proc.plant_id,
            VegetationIndexTimeline.date_captured == proc.date_captured
        ).all()
        
        for veg in veg_data:
            row[f"{veg.index_type.lower()}_mean"] = veg.mean
            row[f"{veg.index_type.lower()}_median"] = veg.median
            row[f"{veg.index_type.lower()}_std"] = veg.std
            row[f"{veg.index_type.lower()}_q25"] = veg.q25
            row[f"{veg.index_type.lower()}_q75"] = veg.q75
            row[f"{veg.index_type.lower()}_min"] = veg.min
            row[f"{veg.index_type.lower()}_max"] = veg.max
            row[f"{veg.index_type.lower()}_nan_fraction"] = 0.0
        
        # Add texture features from TextureTimeline
        texture_data = db.query(TextureTimeline).filter(
            TextureTimeline.plant_id == proc.plant_id,
            TextureTimeline.date_captured == proc.date_captured
        ).all()
        
        for tex in texture_data:
            key = f"{tex.band_name}_{tex.texture_type}"
            row[f"{key}_mean"] = tex.mean
            row[f"{key}_median"] = tex.median
            row[f"{key}_std"] = tex.std
            row[f"{key}_q25"] = tex.q25
            row[f"{key}_q75"] = tex.q75
            row[f"{key}_min"] = tex.min
            row[f"{key}_max"] = tex.max
            row[f"{key}_nan_fraction"] = 0.0
        
        # Add morphology features from MorphologyTimeline
        morph_data = db.query(MorphologyTimeline).filter(
            MorphologyTimeline.plant_id == proc.plant_id,
            MorphologyTimeline.date_captured == proc.date_captured
        ).first()
        
        if morph_data:
            row['morph_area'] = morph_data.size_area
            row['morph_area_cm2'] = morph_data.size_area / 100.0  # Approximate conversion
            row['morph_height'] = morph_data.size_height
            row['morph_height_cm'] = morph_data.size_height / 10.0  # Approximate conversion
            row['morph_width'] = morph_data.size_width
            row['morph_width_cm'] = morph_data.size_width / 10.0
            row['morph_perimeter'] = morph_data.size_perimeter
            row['morph_perimeter_cm'] = morph_data.size_perimeter / 10.0
            row['morph_solidity'] = morph_data.size_solidity
            row['morph_circularity'] = 4 * np.pi * morph_data.size_area / (morph_data.size_perimeter ** 2) if morph_data.size_perimeter > 0 else 0
            row['morph_convex_hull_area'] = morph_data.size_convex_hull_area
            row['morph_convexity'] = morph_data.size_area / morph_data.size_convex_hull_area if morph_data.size_convex_hull_area > 0 else 0
            row['morph_longest_path'] = morph_data.size_longest_path
            row['morph_num_leaves'] = morph_data.size_num_leaves
            row['morph_num_stems'] = morph_data.size_num_branches
            row['morph_ellipse_major_axis'] = morph_data.size_ellipse_major_axis
            row['morph_ellipse_minor_axis'] = morph_data.size_ellipse_minor_axis
            row['morph_ellipse_angle'] = morph_data.size_ellipse_angle
            row['morph_ellipse_eccentricity'] = morph_data.size_ellipse_eccentricity
            row['morph_aspect_ratio'] = morph_data.size_height / morph_data.size_width if morph_data.size_width > 0 else 0
            row['morph_elongation'] = morph_data.size_ellipse_major_axis / morph_data.size_ellipse_minor_axis if morph_data.size_ellipse_minor_axis > 0 else 0
        
        rows.append(row)
    
    if not rows:
        logger.warning("No data found in database")
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    logger.info(f"Created unified dataframe with {len(df)} rows and {len(df.columns)} columns")
    
    return df


@router.get("/charts/unified-data")
def get_unified_data(species: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get unified features data aggregated from database.
    Returns data in wide format matching CSV structure.
    
    Args:
        species: Species name to filter by (e.g., "Sorghum", "Cotton", "Corn")
    """
    try:
        df = aggregate_database_to_unified_format(db, species=species)
        
        if df.empty:
            return {"data": [], "columns": []}
        
        # Convert to JSON-serializable format
        # Replace NaN with None for JSON compatibility
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        
        return {
            "data": df.to_dict("records"),
            "columns": list(df.columns)
        }
    except Exception as e:
        logger.error(f"Error aggregating unified data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error aggregating unified data: {str(e)}")


def merge_genotype_mapping_to_df(df: pd.DataFrame) -> pd.DataFrame:
    """Merge genotype mapping with dataframe"""
    try:
        if not GENOTYPE_CSV.exists():
            logger.warning(f"Genotype mapping file not found: {GENOTYPE_CSV}")
            return df
        
        mapping_df = pd.read_csv(str(GENOTYPE_CSV))
        mapping = mapping_df.rename(columns={"Plant_Name": "plant"})
        mapping["mutation"] = mapping["Genotype"].apply(genotype_to_label)
        
        # Try merging on plant first
        df = df.merge(mapping[["plant", "mutation"]], on="plant", how="left")
        
        # For rows without mutation from plant merge, try merging on plant_num if available
        if 'plant_num' in df.columns and 'Plant_Number' in mapping.columns:
            unmapped = df[df['mutation'].isna()].copy()
            if len(unmapped) > 0:
                mapping_num = mapping[["Plant_Number", "mutation"]].rename(columns={"Plant_Number": "plant_num"})
                
                # Ensure plant_num columns have the same type before merging
                # Convert both to numeric, handling any non-numeric values
                unmapped['plant_num'] = pd.to_numeric(unmapped['plant_num'], errors='coerce')
                mapping_num['plant_num'] = pd.to_numeric(mapping_num['plant_num'], errors='coerce')
                
                # Drop rows where plant_num is NaN after conversion
                unmapped_clean = unmapped.dropna(subset=['plant_num'])
                mapping_num_clean = mapping_num.dropna(subset=['plant_num'])
                
                if len(unmapped_clean) > 0 and len(mapping_num_clean) > 0:
                    unmapped_mapped = unmapped_clean.merge(mapping_num_clean, on="plant_num", how="left", suffixes=("", "_num"))
                    mask = df['mutation'].isna() & df.index.isin(unmapped_mapped.index[unmapped_mapped['mutation_num'].notna()])
                    df.loc[mask, 'mutation'] = unmapped_mapped.loc[unmapped_mapped['mutation_num'].notna(), 'mutation_num'].values
        
        # Keep only rows with mutation assignments
        df = df[df['mutation'].notna()].reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error merging genotype mapping: {e}")
        return df


def compute_pca_components(df: pd.DataFrame, n_components: int = 2) -> tuple:
    """Compute PCA components"""
    # Get feature columns (exclude metadata)
    excluded_cols = {"plant", "date_key", "mutation", "plant_num", "cluster"}
    feature_cols = [c for c in df.columns if c not in excluded_cols]
    feature_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    
    if len(feature_cols) == 0:
        raise ValueError("No numeric feature columns found")
    
    X = df[feature_cols].values
    
    # Handle NaN and inf values
    col_means = np.nanmean(X, axis=0)
    X = np.where(np.isnan(X), col_means, X)
    X = np.where(np.isinf(X), col_means, X)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Compute PCA
    pca = PCA(n_components=n_components, random_state=42)
    components = pca.fit_transform(X_scaled)
    explained = pca.explained_variance_ratio_
    
    return components, explained, df[["plant", "mutation"]].values


def compute_tsne_components(df: pd.DataFrame, n_components: int = 2) -> tuple:
    """Compute t-SNE components"""
    # Get feature columns (exclude metadata)
    excluded_cols = {"plant", "date_key", "mutation", "plant_num", "cluster"}
    feature_cols = [c for c in df.columns if c not in excluded_cols]
    feature_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    
    if len(feature_cols) == 0:
        raise ValueError("No numeric feature columns found")
    
    X = df[feature_cols].values
    
    # Handle NaN and inf values
    col_means = np.nanmean(X, axis=0)
    X = np.where(np.isnan(X), col_means, X)
    X = np.where(np.isinf(X), col_means, X)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Compute PCA first to reduce dimensionality for t-SNE
    pca_pre = PCA(n_components=min(50, X_scaled.shape[1]), random_state=42)
    X_pca = pca_pre.fit_transform(X_scaled)
    
    # Compute t-SNE
    tsne = TSNE(n_components=n_components, random_state=42, perplexity=30)
    components = tsne.fit_transform(X_pca)
    
    # Calculate explained variance (approximate using variance)
    if n_components == 2:
        var1 = np.var(components[:, 0])
        var2 = np.var(components[:, 1])
        total_var = var1 + var2
        explained = np.array([var1 / total_var, var2 / total_var])
    else:  # 3D
        var1 = np.var(components[:, 0])
        var2 = np.var(components[:, 1])
        var3 = np.var(components[:, 2])
        total_var = var1 + var2 + var3
        explained = np.array([var1 / total_var, var2 / total_var, var3 / total_var])
    
    return components, explained, df[["plant", "mutation"]].values


@router.get("/charts/pca")
def get_pca(
    dimensions: int = 2,
    species: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Compute PCA and return components.
    
    Args:
        dimensions: Number of dimensions (2 or 3)
        species: Optional species name to filter by
    """
    try:
        if dimensions not in [2, 3]:
            raise HTTPException(status_code=400, detail="Dimensions must be 2 or 3")
        
        # Get data
        df = aggregate_database_to_unified_format(db, species=species)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data available for PCA computation")
        
        # Merge genotype mapping
        df = merge_genotype_mapping_to_df(df)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data with mutation assignments available")
        
        # Compute PCA
        components, explained, metadata = compute_pca_components(df, n_components=dimensions)
        
        # Build result
        result = []
        for i in range(len(components)):
            row = {
                "plant": str(metadata[i][0]) if metadata[i][0] is not None else "",
                "mutation": str(metadata[i][1]) if metadata[i][1] is not None else ""
            }
            if dimensions == 2:
                row["pc1"] = safe_float(components[i, 0])
                row["pc2"] = safe_float(components[i, 1])
            else:
                row["pc1"] = safe_float(components[i, 0])
                row["pc2"] = safe_float(components[i, 1])
                row["pc3"] = safe_float(components[i, 2])
            result.append(row)
        
        return {
            "data": result,
            "explained_variance": [safe_float(v) for v in explained]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing PCA: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error computing PCA: {str(e)}")


@router.get("/charts/tsne")
def get_tsne(
    dimensions: int = 2,
    species: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Compute t-SNE and return components.
    
    Args:
        dimensions: Number of dimensions (2 or 3)
        species: Optional species name to filter by
    """
    try:
        if dimensions not in [2, 3]:
            raise HTTPException(status_code=400, detail="Dimensions must be 2 or 3")
        
        # Get data
        df = aggregate_database_to_unified_format(db, species=species)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data available for t-SNE computation")
        
        # Merge genotype mapping
        df = merge_genotype_mapping_to_df(df)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data with mutation assignments available")
        
        # Compute t-SNE
        components, explained, metadata = compute_tsne_components(df, n_components=dimensions)
        
        # Build result
        result = []
        for i in range(len(components)):
            row = {
                "plant": str(metadata[i][0]) if metadata[i][0] is not None else "",
                "mutation": str(metadata[i][1]) if metadata[i][1] is not None else ""
            }
            if dimensions == 2:
                row["tsne1"] = safe_float(components[i, 0])
                row["tsne2"] = safe_float(components[i, 1])
            else:
                row["tsne1"] = safe_float(components[i, 0])
                row["tsne2"] = safe_float(components[i, 1])
                row["tsne3"] = safe_float(components[i, 2])
            result.append(row)
        
        return {
            "data": result,
            "explained_variance": [safe_float(v) for v in explained]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing t-SNE: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error computing t-SNE: {str(e)}")

