# upload_processor.py
"""
Service to process uploaded plant images through the analysis pipeline.
Handles file reorganization, pipeline execution, result moving, and database updates.
"""

import os
import re
import logging
import boto3
from datetime import datetime, date
from typing import Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists() and not os.environ.get("AWS_ACCESS_KEY_ID"):
        load_dotenv(env_file)
        logger.info(f"upload_processor: Loaded environment variables from {env_file}")
except (ImportError, Exception):
    pass

# Import pipeline runner
from backend.services.pipeline_runner import process_plant_image

# S3 Configuration - load from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "plant-analysis-data")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("REGION", "us-east-2"))
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")


def get_s3_client():
    """Create and return an S3 client with credentials from environment."""
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        return boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    else:
        # Fallback to default credential chain
        logger.warning("AWS credentials not found in environment, using default credential chain")
        return boto3.client('s3', region_name=S3_REGION)


def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    Parse filename to extract species, date, and plant number.
    Expected format: {Species}_{Date}_plant#.tiff
    Example: Sorghum_2024-12-04_plant1.tiff
    Species may be hyphenated (e.g., Mullet-sorghum).
    
    Returns dict with 'species', 'date', 'plant_num', or None if invalid.
    """
    # Allow crop names that can be hyphenated, e.g. "Mullet-sorghum"
    pattern = r'^([A-Z][A-Za-z-]+)_(\d{4}-\d{2}-\d{2})_plant(\d+)\.(tiff|tif)$'
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if not match:
        logger.error(f"Invalid filename format: {filename}")
        return None
    
    species, date_str, plant_num, ext = match.groups()
    
    # Validate date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        logger.error(f"Invalid date format in filename: {filename}")
        return None
    
    return {
        'species': species,
        'date': date_str,
        'plant_num': plant_num,
        'extension': ext
    }


def reorganize_file_for_pipeline(s3_key: str, parsed_info: Dict[str, str]) -> str:
    """
    Reorganize uploaded file to match pipeline's expected S3 structure.
    Pipeline expects: {species}_dataset/{date}/{plant_id}/{filename}
    
    For uploaded files, we place them under an Uploaded_dataset root, with
    a crop-specific dataset folder derived from the filename species:
        Uploaded_dataset/{Species}_dataset/{date}/{filename}
    
    Returns the new S3 key.
    """
    s3 = get_s3_client()
    
    # Build new structure using the crop/species name from the filename
    crop = parsed_info['species']  # May be hyphenated, e.g. "Mullet-sorghum"
    new_key = f"Uploaded_dataset/{crop}_dataset/{parsed_info['date']}/{os.path.basename(s3_key)}"
    
    # Copy file to new location
    try:
        copy_source = {'Bucket': S3_BUCKET, 'Key': s3_key}
        s3.copy_object(CopySource=copy_source, Bucket=S3_BUCKET, Key=new_key)
        logger.info(f"Reorganized file: {s3_key} -> {new_key}")
        return new_key
    except Exception as e:
        logger.error(f"Failed to reorganize file {s3_key}: {e}")
        raise


def move_results_to_uploaded_folder(pipeline_result: Dict, parsed_info: Dict[str, str], original_filename: str) -> Dict[str, str]:
    """
    (Legacy helper - currently unused)
    
    Originally moved pipeline results from results/Uploaded_results/ to
    an Uploaded files/results/ folder. Kept for backwards compatibility
    but not used in the current pipeline where results are written to
    crop-specific results folders (results/{crop}_results/...).
    """
    s3 = get_s3_client()
    plant_id = f"plant{parsed_info['plant_num']}"
    date_str = parsed_info['date']
    
    # Source prefix (where pipeline would have saved results)
    source_prefix = pipeline_result.get(
        "s3_prefix",
        f"results/Uploaded_results/timeline_images/{plant_id}/{date_str}"
    )
    source_summary_prefix = pipeline_result.get(
        "summary_prefix",
        f"results/Uploaded_results/{plant_id}/{date_str}"
    )
    
    # Destination prefix (where we want results)
    dest_prefix = f"Uploaded files/results/{date_str}/{plant_id}"
    dest_summary_prefix = f"Uploaded files/results/{date_str}/{plant_id}"
    
    moved_files = {}
    
    # List all files in source prefix
    try:
        # Move timeline images
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=source_prefix)
        
        for page in pages:
            for obj in page.get('Contents', []):
                old_key = obj['Key']
                # Build new key
                relative_path = old_key.replace(source_prefix, '').lstrip('/')
                new_key = f"{dest_prefix}/{relative_path}"
                
                # Copy to new location
                copy_source = {'Bucket': S3_BUCKET, 'Key': old_key}
                s3.copy_object(CopySource=copy_source, Bucket=S3_BUCKET, Key=new_key)
                moved_files[old_key] = new_key
                logger.info(f"Moved result: {old_key} -> {new_key}")
        
        # Move summary files (JSON files)
        summary_pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=source_summary_prefix)
        for page in summary_pages:
            for obj in page.get('Contents', []):
                old_key = obj['Key']
                relative_path = old_key.replace(source_summary_prefix, '').lstrip('/')
                new_key = f"{dest_summary_prefix}/{relative_path}"
                
                copy_source = {'Bucket': S3_BUCKET, 'Key': old_key}
                s3.copy_object(CopySource=copy_source, Bucket=S3_BUCKET, Key=new_key)
                moved_files[old_key] = new_key
                logger.info(f"Moved summary: {old_key} -> {new_key}")
        
        # Delete old files after successful copy
        for old_key in moved_files.keys():
            try:
                s3.delete_object(Bucket=S3_BUCKET, Key=old_key)
            except Exception as e:
                logger.warning(f"Failed to delete old file {old_key}: {e}")
        
    except Exception as e:
        logger.error(f"Error moving results: {e}")
        raise
    
    return moved_files


def save_to_database(
    parsed_info: Dict[str, str],
    pipeline_result: Dict,
    image_key: str,
    result_prefix: str
) -> None:
    """
    Save processed data to database with species="Uploaded".
    Also populates timeline tables for vegetation, texture, and morphology.
    """
    logger.info(f"=== SAVING TO DATABASE ===")
    logger.info(f"parsed_info: {parsed_info}")
    logger.info(f"image_key: {image_key}")
    logger.info(f"result_prefix: {result_prefix}")
    
    try:
        from backend.db.database import SessionLocal
        from backend.db.models import Plant, ProcessedData
        from backend.services.db_service import (
            ProcessedDataService, 
            PlantService,
            VegetationIndexService,
            TextureService,
            MorphologyService
        )
        
        db = SessionLocal()
        logger.info("Database session created")
        
        try:
            # Use a plant_id that encodes both that it was uploaded and its species
            plant_id = f"Uploaded_{parsed_info['species']}_plant{parsed_info['plant_num']}"
            date_obj = datetime.strptime(parsed_info['date'], '%Y-%m-%d').date()
            date_str = parsed_info['date']
            plant_id_short = f"plant{parsed_info['plant_num']}"
            
            logger.info(f"Creating/updating plant: {plant_id}, species={parsed_info['species']}, date={date_obj}")
            
            # Create or update Plant entry using PlantService to handle date serialization
            plant = PlantService.create_or_update_plant(
                db=db,
                plant_id=plant_id,
                species=parsed_info['species'],
                capture_date=date_obj
            )
            logger.info(f"Plant created/updated: {plant.id}, dates_captured={plant.dates_captured}")
            
            # Create ProcessedData entry
            processed_data_id = f"{plant_id}_{date_str}"
            
            # Extract features from pipeline result
            vegetation_features = pipeline_result.get('vegetation_features', {})
            texture_features = pipeline_result.get('texture_features', {})
            morphology_features = pipeline_result.get('morphology', {})
            
            # Get first plant's morphology if available
            if morphology_features and isinstance(morphology_features, dict):
                first_plant = next(iter(morphology_features.values()))
                morphology_features = first_plant
            
            ProcessedDataService.create_processed_data_entry(
                db=db,
                plant_id=plant_id,
                date_captured=date_obj,
                image_key=image_key,
                vegetation_features=vegetation_features,
                morphology_features=morphology_features,
                texture_features=texture_features
            )
            
            # Populate VegetationIndexTimeline
            S3_BASE_URL = "https://plant-analysis-data.s3.us-east-2.amazonaws.com"
            if vegetation_features:
                # Handle list format: [{"index": "NDVI", "mean": ..., ...}, ...]
                if isinstance(vegetation_features, list):
                    for stats in vegetation_features:
                        if isinstance(stats, dict) and 'index' in stats:
                            index_name = stats['index']
                            if all(stat in stats for stat in ['mean', 'median', 'std', 'q25', 'q75', 'min', 'max']):
                                try:
                                    VegetationIndexService.create_vegetation_index_entry(
                                        db=db,
                                        plant_id=plant_id,
                                        date_captured=date_obj,
                                        index_type=index_name,
                                        mean=float(stats['mean']),
                                        median=float(stats['median']),
                                        std=float(stats['std']),
                                        q25=float(stats['q25']),
                                        q75=float(stats['q75']),
                                        min_val=float(stats['min']),
                                        max_val=float(stats['max']),
                                        index_image_key=f"{S3_BASE_URL}/{result_prefix}/vegetation_indices/{index_name}.png"
                                    )
                                    logger.info(f"Created vegetation timeline entry: {index_name}")
                                except Exception as e:
                                    logger.warning(f"Failed to create vegetation timeline entry for {index_name}: {e}")
                # Handle dict format: {"NDVI": {"mean": ..., ...}, ...}
                elif isinstance(vegetation_features, dict):
                    for index_name, stats in vegetation_features.items():
                        if isinstance(stats, dict) and all(stat in stats for stat in ['mean', 'median', 'std', 'q25', 'q75', 'min', 'max']):
                            try:
                                VegetationIndexService.create_vegetation_index_entry(
                                    db=db,
                                    plant_id=plant_id,
                                    date_captured=date_obj,
                                    index_type=index_name,
                                    mean=float(stats['mean']),
                                    median=float(stats['median']),
                                    std=float(stats['std']),
                                    q25=float(stats['q25']),
                                    q75=float(stats['q75']),
                                    min_val=float(stats['min']),
                                        max_val=float(stats['max']),
                                        index_image_key=f"{S3_BASE_URL}/{result_prefix}/vegetation_indices/{index_name}.png"
                                )
                                logger.info(f"Created vegetation timeline entry: {index_name}")
                            except Exception as e:
                                logger.warning(f"Failed to create vegetation timeline entry for {index_name}: {e}")
            
            # Populate TextureTimeline
            if texture_features:
                # Handle different formats: list of dicts or nested dict
                if isinstance(texture_features, list) and len(texture_features) > 0:
                    # Format from compute_texture_features: list of feature vectors
                    feature_vector = texture_features[0]  # Get first plant's features
                    
                    # Group features by band_texture_type
                    texture_groups = {}
                    for key, value in feature_vector.items():
                        if key == 'plant_id':
                            continue
                        # Keys are like "band_texture_type_stat" (e.g., "color_lbp_mean")
                        parts = key.rsplit('_', 1)  # Split on last underscore
                        if len(parts) == 2:
                            feature_name = parts[0]  # e.g., "color_lbp"
                            stat_name = parts[1]  # e.g., "mean"
                            
                            if feature_name not in texture_groups:
                                texture_groups[feature_name] = {}
                            texture_groups[feature_name][stat_name] = value
                    
                    # Create timeline entries for each texture feature
                    for feature_name, stats in texture_groups.items():
                        # Parse band and texture type from feature_name (e.g., "color_lbp")
                        parts = feature_name.split('_', 1)
                        if len(parts) == 2:
                            band_name = parts[0]
                            texture_type = parts[1]
                            
                            # Check for required stats - use defaults for missing values
                            required_stats = ['mean', 'std', 'max', 'min', 'median', 'q25', 'q75']
                            has_minimum_stats = all(stat in stats for stat in ['mean', 'std', 'max', 'min'])
                            
                            if has_minimum_stats:
                                try:
                                    TextureService.create_texture_entry(
                                        db=db,
                                        plant_id=plant_id,
                                        date_captured=date_obj,
                                        band_name=band_name,
                                        texture_type=texture_type,
                                        mean=float(stats.get('mean', 0)),
                                        median=float(stats.get('median', stats.get('mean', 0))),  # fallback to mean
                                        std=float(stats.get('std', 0)),
                                        q25=float(stats.get('q25', 0)),
                                        q75=float(stats.get('q75', 0)),
                                        min_val=float(stats.get('min', 0)),
                                        max_val=float(stats.get('max', 0)),
                                        texture_image_key=f"{S3_BASE_URL}/{result_prefix}/texture/{band_name}/{texture_type}.png"
                                    )
                                    logger.info(f"Created texture timeline entry: {band_name}_{texture_type}")
                                except Exception as e:
                                    logger.warning(f"Failed to create texture timeline entry for {feature_name}: {e}")
                elif isinstance(texture_features, dict):
                    # Handle nested dict format: {band_name: {texture_type: stats}}
                    for band_name, texture_types in texture_features.items():
                        if isinstance(texture_types, dict):
                            for texture_type, stats in texture_types.items():
                                if isinstance(stats, dict) and all(stat in stats for stat in ['mean', 'median', 'std', 'q25', 'q75', 'min', 'max']):
                                    try:
                                        TextureService.create_texture_entry(
                                            db=db,
                                            plant_id=plant_id,
                                            date_captured=date_obj,
                                            band_name=band_name,
                                            texture_type=texture_type,
                                            mean=float(stats['mean']),
                                            median=float(stats['median']),
                                            std=float(stats['std']),
                                            q25=float(stats['q25']),
                                            q75=float(stats['q75']),
                                            min_val=float(stats['min']),
                                            max_val=float(stats['max']),
                                            texture_image_key=f"{S3_BASE_URL}/{result_prefix}/texture/{band_name}/{texture_type}.png"
                                        )
                                        logger.info(f"Created texture timeline entry: {band_name}_{texture_type}")
                                    except Exception as e:
                                        logger.warning(f"Failed to create texture timeline entry for {band_name}_{texture_type}: {e}")
            
            # Populate MorphologyTimeline
            if morphology_features and isinstance(morphology_features, dict):
                size_traits = morphology_features.get('size_traits', {})
                morph_traits = morphology_features.get('morphology_traits', {})
                
                if size_traits or morph_traits:
                    try:
                        # Helper function to parse semicolon-separated strings to float lists
                        def parse_float_list(value):
                            if isinstance(value, list):
                                return [float(v) for v in value]
                            elif isinstance(value, str):
                                return [float(v.strip()) for v in value.split(';') if v.strip()]
                            return []
                        
                        # Helper function to parse point lists (could be strings or list of dicts)
                        def parse_point_list(value):
                            if isinstance(value, list):
                                # Already a list, ensure each item is a dict
                                result = []
                                for item in value:
                                    if isinstance(item, dict):
                                        result.append({'x': float(item.get('x', 0)), 'y': float(item.get('y', 0))})
                                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                                        result.append({'x': float(item[0]), 'y': float(item[1])})
                                return result
                            elif isinstance(value, str):
                                # Parse string format like "x1,y1; x2,y2"
                                result = []
                                for pair in value.split(';'):
                                    pair = pair.strip()
                                    if ',' in pair:
                                        parts = pair.split(',')
                                        if len(parts) >= 2:
                                            result.append({'x': float(parts[0].strip()), 'y': float(parts[1].strip())})
                                return result
                            return []
                        
                        # Helper to ensure dict format for center of mass / ellipse center
                        def ensure_point_dict(value):
                            if isinstance(value, dict):
                                return {'x': float(value.get('x', 0)), 'y': float(value.get('y', 0))}
                            elif isinstance(value, (list, tuple)) and len(value) >= 2:
                                return {'x': float(value[0]), 'y': float(value[1])}
                            return {'x': 0, 'y': 0}
                        
                        # Extract size traits
                        size_area = float(size_traits.get('area', 0))
                        size_convex_hull_area = float(size_traits.get('convex_hull_area', 0))
                        size_solidity = float(size_traits.get('solidity', 0))
                        size_perimeter = float(size_traits.get('perimeter', 0))
                        size_width = float(size_traits.get('width', 0))
                        size_height = float(size_traits.get('height', 0))
                        size_longest_path = float(size_traits.get('longest_path', 0))
                        size_center_of_mass = ensure_point_dict(size_traits.get('center_of_mass', {'x': 0, 'y': 0}))
                        size_convex_hull_vertices = parse_point_list(size_traits.get('convex_hull_vertices', []))
                        size_ellipse_center = ensure_point_dict(size_traits.get('ellipse_center', {'x': 0, 'y': 0}))
                        size_ellipse_major_axis = float(size_traits.get('ellipse_major_axis', 0))
                        size_ellipse_minor_axis = float(size_traits.get('ellipse_minor_axis', 0))
                        size_ellipse_angle = float(size_traits.get('ellipse_angle', 0))
                        size_ellipse_eccentricity = float(size_traits.get('ellipse_eccentricity', 0))
                        size_num_leaves = int(size_traits.get('num_leaves', 0))
                        size_num_branches = int(size_traits.get('num_branches', 0))
                        
                        # Extract morphology traits - handle semicolon-separated strings
                        morph_branch_pts = parse_point_list(morph_traits.get('branch_pts', []))
                        morph_tips = parse_point_list(morph_traits.get('tips', []))
                        morph_segment_path_length = parse_float_list(morph_traits.get('segment_path_length', []))
                        morph_segment_eu_length = parse_float_list(morph_traits.get('segment_eu_length', []))
                        morph_segment_curvature = parse_float_list(morph_traits.get('segment_curvature', []))
                        morph_segment_angle = parse_float_list(morph_traits.get('segment_angle', []))
                        morph_segment_tangent_angle = parse_float_list(morph_traits.get('segment_tangent_angle', []))
                        morph_segment_insertion_angle = parse_float_list(morph_traits.get('segment_insertion_angle', []))
                        
                        MorphologyService.create_morphology_entry(
                            db=db,
                            plant_id=plant_id,
                            date_captured=date_obj,
                            size_area=size_area,
                            size_convex_hull_area=size_convex_hull_area,
                            size_solidity=size_solidity,
                            size_perimeter=size_perimeter,
                            size_width=size_width,
                            size_height=size_height,
                            size_longest_path=size_longest_path,
                            size_center_of_mass=size_center_of_mass,
                            size_convex_hull_vertices=size_convex_hull_vertices,
                            size_ellipse_center=size_ellipse_center,
                            size_ellipse_major_axis=size_ellipse_major_axis,
                            size_ellipse_minor_axis=size_ellipse_minor_axis,
                            size_ellipse_angle=size_ellipse_angle,
                            size_ellipse_eccentricity=size_ellipse_eccentricity,
                            size_num_leaves=size_num_leaves,
                            size_num_branches=size_num_branches,
                            morph_branch_pts=morph_branch_pts,
                            morph_tips=morph_tips,
                            morph_segment_path_length=morph_segment_path_length,
                            morph_segment_eu_length=morph_segment_eu_length,
                            morph_segment_curvature=morph_segment_curvature,
                            morph_segment_angle=morph_segment_angle,
                            morph_segment_tangent_angle=morph_segment_tangent_angle,
                            morph_segment_insertion_angle=morph_segment_insertion_angle,
                            morphology_image_key=f"{S3_BASE_URL}/{result_prefix}/morphology/images/"
                        )
                        logger.info(f"Created morphology timeline entry")
                    except Exception as e:
                        logger.warning(f"Failed to create morphology timeline entry: {e}")
            
            db.commit()
            logger.info(f"=== DATABASE SAVE COMPLETE ===")
            logger.info(f"Saved ProcessedData: {processed_data_id}")
            
            # Verify the plant was saved correctly
            saved_plant = db.query(Plant).filter(Plant.id == plant_id).first()
            if saved_plant:
                logger.info(f"Verified plant in DB: {saved_plant.id}, species={saved_plant.species}, dates={saved_plant.dates_captured}")
            else:
                logger.error(f"Plant {plant_id} NOT FOUND in database after save!")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            db.close()
            
    except ImportError as e:
        logger.warning(f"Database not available: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        import traceback
        traceback.print_exc()
        raise


def process_uploaded_file(s3_key: str, filename: str, segmentation_method: str = "sam3") -> Dict:
    """
    Main function to process an uploaded file through the analysis pipeline.
    
    Steps:
    1. Parse filename to extract metadata
    2. Reorganize file to match pipeline structure
       -> {Species}_dataset/{date}/{plant#}/{filename}
    3. Run pipeline analysis (results saved to results/{Species}_results/)
    4. Save to database (species stored as parsed from filename)
    
    Returns dict with processing results.
    """
    logger.info(f"Processing uploaded file: {s3_key}")
    
    # Step 1: Parse filename
    parsed_info = parse_filename(filename)
    if not parsed_info:
        raise ValueError(f"Invalid filename format: {filename}")
    
    # Step 2: Reorganize file
    pipeline_key = reorganize_file_for_pipeline(s3_key, parsed_info)
    
    try:
        # Step 3: Run pipeline (results are saved to results/Uploaded_results/{Species}_results/)
        logger.info(f"Running pipeline for: {pipeline_key} with segmentation method: {segmentation_method}")
        pipeline_result = process_plant_image(S3_BUCKET, pipeline_key, segmentation_method=segmentation_method)
        
        # Step 4: Save to database
        # Use the pipeline's actual output location from the result
        result_prefix = pipeline_result.get(
            's3_prefix',
            f"results/Uploaded_results/{parsed_info['species']}_results/timeline_images/plant{parsed_info['plant_num']}/{parsed_info['date']}"
        )
        
        # Build the image_key URL like populate_db.py does (base URL to timeline images folder)
        S3_BASE_URL = "https://plant-analysis-data.s3.us-east-2.amazonaws.com"
        plant_id_short = f"plant{parsed_info['plant_num']}"
        date_str = parsed_info['date']
        processed_image_key = f"{S3_BASE_URL}/results/Uploaded_results/{parsed_info['species']}_results/timeline_images/{plant_id_short}/{date_str}"
        
        save_to_database(parsed_info, pipeline_result, processed_image_key, result_prefix)
        
        logger.info(f"Successfully processed: {filename}")
        logger.info(f"Results saved to: {result_prefix}")
        
        return {
            'success': True,
            'filename': filename,
            'pipeline_result': pipeline_result,
            'result_prefix': result_prefix,
            'summary_prefix': pipeline_result.get(
                'summary_prefix',
                f"results/Uploaded_results/{parsed_info['species']}_results/plant{parsed_info['plant_num']}/{parsed_info['date']}"
            )
        }
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}")
        raise
    finally:
        # Cleanup: Delete temporary pipeline file
        try:
            s3 = get_s3_client()
            s3.delete_object(Bucket=S3_BUCKET, Key=pipeline_key)
            logger.info(f"Cleaned up temporary file: {pipeline_key}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup {pipeline_key}: {cleanup_error}")

