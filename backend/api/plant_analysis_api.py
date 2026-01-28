# plant_analysis_api.py

import logging
import sys
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stdout,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True
)

from fastapi import APIRouter, HTTPException, Query, Depends, Body
# from backend.db.session import SessionLocal
# from backend.db.models import ProcessedImage
from fastapi.responses import JSONResponse, Response, StreamingResponse
from io import BytesIO
from typing import List
import zipfile
from pydantic import BaseModel
from tasks import analyze_plant_task
from celery_worker import celery_app
import boto3
import json
import os
import re
from datetime import datetime
from backend.db.database import get_db
from backend.db.models import Plant, ProcessedData, VegetationIndexTimeline, TextureTimeline, MorphologyTimeline, VEGETATION_INDICES, TEXTURE_FEATURES
from backend.services.db_service import PlantService
from sqlalchemy.orm import Session

router = APIRouter()

# Request model for download-images-zip
class DownloadImagesZipRequest(BaseModel):
    image_urls: List[str]
    tab_name: str = "images"

# Check if read-only mode is enabled
READ_ONLY_MODE = os.environ.get("READ_ONLY_MODE", "false").lower() == "true"

S3_BUCKET = "plant-analysis-data"  
S3_IMAGE_PATH_TEMPLATE = "{species}_dataset/{date}/{plant_id}/{plant_id}_frame8.tif" 
S3_RESULTS_PATH = "results/{species}_results/timeline_images/{plant_id}/{date}/" 

@router.post("/sync-plants-from-s3/{species}")
async def sync_plants_from_s3(species: str, date: str = Query(None), db: Session = Depends(get_db)):
    """
    Sync plants from S3 to database for a given species and optional date.
    This ensures plants exist in the database even if they haven't been processed yet.
    """
    try:
        s3 = boto3.client('s3')
        plants_created = 0
        
        if date:
            # Sync plants for a specific date
            prefix = f"{species}_dataset/{date}/"
            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix, Delimiter='/')
            
            for prefix_obj in response.get('CommonPrefixes', []):
                plant_folder = prefix_obj['Prefix'].split('/')[-2]
                if plant_folder.startswith('plant'):
                    plant_id = f"{species}_{plant_folder}"
                    
                    # Check if plant exists
                    plant = db.query(Plant).filter(Plant.id == plant_id).first()
                    if not plant:
                        # Create plant
                        plant = Plant(id=plant_id, name=None, species=species, dates_captured=[])
                        db.add(plant)
                        plants_created += 1
                    
                    # Add date if not already present
                    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                    if plant.dates_captured is None:
                        plant.dates_captured = []
                    if date_obj not in plant.dates_captured:
                        plant.dates_captured.append(date_obj)
        else:
            # Sync all dates for the species
            prefix = f"{species}_dataset/"
            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix, Delimiter='/')
            
            dates = []
            for prefix_obj in response.get('CommonPrefixes', []):
                date_str = prefix_obj['Prefix'].split('/')[-2]
                if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                    dates.append(date_str)
            
            # For each date, get plants
            for date_str in dates:
                date_prefix = f"{species}_dataset/{date_str}/"
                date_response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=date_prefix, Delimiter='/')
                
                for prefix_obj in date_response.get('CommonPrefixes', []):
                    plant_folder = prefix_obj['Prefix'].split('/')[-2]
                    if plant_folder.startswith('plant'):
                        plant_id = f"{species}_{plant_folder}"
                        
                        # Check if plant exists
                        plant = db.query(Plant).filter(Plant.id == plant_id).first()
                        if not plant:
                            # Create plant
                            plant = Plant(id=plant_id, name=None, species=species, dates_captured=[])
                            db.add(plant)
                            plants_created += 1
                        
                        # Add date if not already present
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if plant.dates_captured is None:
                            plant.dates_captured = []
                        if date_obj not in plant.dates_captured:
                            plant.dates_captured.append(date_obj)
        
        db.commit()
        return {"message": f"Synced {plants_created} new plants for {species}", "plants_created": plants_created}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error syncing plants from S3: {str(e)}")

@router.post("/analyze-plant/{species}/{plant_id}")
async def analyze_plant(species: str, plant_id: str, date: str, segmentation_method: str = "sam3", db: Session = Depends(get_db)):
    if READ_ONLY_MODE:
        raise HTTPException(status_code=403, detail="Read-only mode: Plant analysis is disabled")
    
    # Ensure plant exists in database (create if it doesn't)
    full_plant_id = f"{species}_{plant_id}"
    plant = db.query(Plant).filter(Plant.id == full_plant_id).first()
    if not plant:
        from datetime import datetime as dt
        date_obj = dt.strptime(date, "%Y-%m-%d").date()
        plant = Plant(id=full_plant_id, name=None, species=species, dates_captured=[date_obj])
        db.add(plant)
        db.commit()
        print(f"Created plant entry: {full_plant_id} with date {date}")
    else:
        # Add date if not already present
        from datetime import datetime as dt
        date_obj = dt.strptime(date, "%Y-%m-%d").date()
        if plant.dates_captured is None:
            plant.dates_captured = []
        if date_obj not in plant.dates_captured:
            plant.dates_captured.append(date_obj)
            db.commit()
    
    # Construct the S3 key for the plant image
    key = S3_IMAGE_PATH_TEMPLATE.format(species=species, date=date, plant_id=plant_id)
    task = analyze_plant_task.delay(S3_BUCKET, key, species, segmentation_method)
    return {"task_id": task.id, "status": "processing started"}

@router.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": task.state,
        "result": task.result if task.state == 'SUCCESS' else None
    }

@router.get("/plant-results/{species}/{plant_id}")
def get_plant_results(species: str, plant_id: str, date: str):
    s3 = boto3.client('s3', region_name='us-east-2')
    bucket = "plant-analysis-data"
    prefix = S3_RESULTS_PATH.format(species=species, plant_id=plant_id, date=date)
    
    print(f"🔍 Looking for files in S3: bucket={bucket}, prefix={prefix}")
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        files = []
        for page in page_iterator:
            if 'Contents' in page:
                files.extend([obj['Key'] for obj in page['Contents']])
        
        print(f"📁 Found {len(files)} files: {files}")
        
        if not files:
            print(f"⚠️ No files found for {species}_{plant_id} on {date}")
            return {"error": "No analysis results found for this plant and date"}
        
        result = {}
        for file in files:
            rel_path = file[len(prefix):] if file.startswith(prefix) else file
            clean_key = rel_path.replace('/', '_').replace('.png', '').replace('.json', '')
            region = 'us-east-2'
            url = f"https://{bucket}.s3.{region}.amazonaws.com/{file}"
            
            print(f"📄 Processing file: {file} -> clean_key: {clean_key}")
            
            if file.endswith('.png'):
                result[clean_key] = url
                print(f"🖼️ Added image: {clean_key} = {url}")
            elif file.endswith('.json'):
                obj = s3.get_object(Bucket=bucket, Key=file)
                data = json.loads(obj['Body'].read().decode('utf-8'))
                result[clean_key] = data
                print(f"📊 Added JSON data: {clean_key}")
                # If this is a *_result key, align vegetation_features and texture_features
                if clean_key.endswith('_result') and isinstance(data, dict):
                    # Vegetation features
                    if 'vegetation_indices' in data and isinstance(data['vegetation_indices'], list):
                        data['vegetation_features'] = data['vegetation_indices']
                    elif 'vegetation_indices_vegetation_features' in data and isinstance(data['vegetation_indices_vegetation_features'], list):
                        data['vegetation_features'] = data['vegetation_indices_vegetation_features']
                    # Texture features
                    if 'texture_features' in data and isinstance(data['texture_features'], list):
                        data['texture_features'] = data['texture_features']
                    elif 'texture_texture_features' in data and isinstance(data['texture_texture_features'], list):
                        data['texture_features'] = data['texture_texture_features']
                # Expose morphology traits as a flat dict for frontend compatibility
                if ('/morphology/' in file and file.endswith('_traits.json') and isinstance(data, dict)):
                    size_traits = data.get('size_traits', {}) if isinstance(data.get('size_traits', {}), dict) else {}
                    morph_traits = data.get('morphology_traits', {}) if isinstance(data.get('morphology_traits', {}), dict) else {}
                    merged = {}
                    merged.update(size_traits)
                    merged.update(morph_traits)
                    result['morphology_features'] = merged
        return result
    except Exception as e:
        print(f"❌ Error fetching results: {str(e)}")
        logging.error(f"Error fetching results: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Error fetching results: {str(e)}")


@router.get("/plant-database-data/{species}/{plant_id}")
def get_plant_database_data(species: str, plant_id: str, date: str, db: Session = Depends(get_db)):
    """
    Get Actual Data from Database to use in the frontend

    TODO: ADD MORPHOLOGY DATA
    """
    try:
        # Convert date string to date object
        from datetime import datetime
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Get processed data
        # Handle uploaded plants: plant_id format is "Uploaded_{species}_plant{num}" in database
        # but frontend sends "Uploaded_plant{num}" or just "plant{num}"
        if plant_id.startswith("Uploaded_"):
            # If plant_id already starts with "Uploaded_", check if it includes species
            if f"Uploaded_{species}_" in plant_id:
                # Already has full format: "Uploaded_{species}_plant{num}"
                full_plant_id = plant_id
            else:
                # Format: "Uploaded_plant{num}" -> convert to "Uploaded_{species}_plant{num}"
                full_plant_id = plant_id.replace("Uploaded_", f"Uploaded_{species}_")
        else:
            # Regular plant: "plant{num}" -> "{species}_plant{num}"
            full_plant_id = f"{species}_{plant_id}"
        
        processed_id = f"{full_plant_id}_{date}"
        processed_data = db.query(ProcessedData).filter(
            ProcessedData.id == processed_id
        ).first()
        
        if not processed_data:
            # Try alternative lookup by plant_id and date_captured
            processed_data = db.query(ProcessedData).filter(
                ProcessedData.plant_id == full_plant_id,
                ProcessedData.date_captured == date_obj
            ).first()
        
        if not processed_data:
            raise HTTPException(status_code=404, detail=f"No data found for this plant and date. Looked for processed_id: {processed_id}, plant_id: {full_plant_id}")
        
        base_path = processed_data.image_key

        # Get main images using the correct S3 URL format
        S3_BASE_URL = "https://plant-analysis-data.s3.us-east-2.amazonaws.com"
        
        # For uploaded plants, use Uploaded_results path; for regular plants, use species_results path
        if full_plant_id.startswith("Uploaded_"):
            # Extract plant number from full_plant_id (e.g., "Uploaded_Mullet_plant5" -> "plant5")
            plant_num = full_plant_id.split("_")[-1]  # Gets "plant5"
            image_base = f"{S3_BASE_URL}/results/Uploaded_results/{species}_results/timeline_images/{plant_num}/{date}"
        else:
            image_base = f"{S3_BASE_URL}/results/{species}_results/timeline_images/{plant_id}/{date}"
        
        mainImages = {
            'original': f"{image_base}/original.png",
            'mask': f"{image_base}/mask.png", 
            'overlay': f"{image_base}/overlay.png",
            'segmented': f"{image_base}/segmented.png"
        }
        
        # Get texture data from timeline on specific date
        texture_data = db.query(TextureTimeline).filter(
            TextureTimeline.plant_id == full_plant_id,
            TextureTimeline.date_captured == date_obj
        ).all()

        # Get texture images - use URLs stored in database
        textureImages = {}
        for texture in texture_data:
            textureImages[f"{texture.band_name}_{texture.texture_type}"] = texture.texture_image_key
        
        # Get vegetation index data from timeline on specific date
        veg_data = db.query(VegetationIndexTimeline).filter(
            VegetationIndexTimeline.plant_id == full_plant_id,
            VegetationIndexTimeline.date_captured == date_obj
        ).all()
        
        # Get vegetation indices images - use URLs stored in database
        vegImages = {}
        for veg in veg_data:
            vegImages[veg.index_type] = veg.index_image_key
        
        # Get vegetation indices table data
        vegTable = []
        for veg in veg_data:
            vegTable.append({
                'index': veg.index_type,
                'mean': veg.mean,
                'std': veg.std,
                'min': veg.min,
                'max': veg.max,
                'q25': veg.q25,
                'median': veg.median,
                'q75': veg.q75
            })
        
        # Get texture features table data
        textureTable = []
        for texture in texture_data:
            textureTable.append({
                'feature': f"{texture.band_name}_{texture.texture_type}",
                'band': texture.band_name,
                'texture_type': texture.texture_type,
                'mean': texture.mean,
                'std': texture.std,
                'min': texture.min,
                'max': texture.max,
                'q25': texture.q25,
                'median': texture.median,
                'q75': texture.q75
            })
        
        # Get morphology data from timeline on specific date
        morphology_data = db.query(MorphologyTimeline).filter(
            MorphologyTimeline.plant_id == full_plant_id,
            MorphologyTimeline.date_captured == date_obj
        ).first()
        
        print(f"Morphology data found: {morphology_data is not None}")
        if morphology_data:
            print(f"Morphology data for {species}_{plant_id} on {date}: {morphology_data}")
        
        # Get morphology features table data
        morphologyTable = []
        morphologyImagesBase = None
        morphologyImages = {}
        if morphology_data:
            # Size-related features
            morphologyTable.extend([
                {'feature': 'Area', 'value': morphology_data.size_area, 'unit': 'pixels²'},
                {'feature': 'Convex Hull Area', 'value': morphology_data.size_convex_hull_area, 'unit': 'pixels²'},
                {'feature': 'Solidity', 'value': morphology_data.size_solidity, 'unit': 'ratio'},
                {'feature': 'Perimeter', 'value': morphology_data.size_perimeter, 'unit': 'pixels'},
                {'feature': 'Width', 'value': morphology_data.size_width, 'unit': 'pixels'},
                {'feature': 'Height', 'value': morphology_data.size_height, 'unit': 'pixels'},
                {'feature': 'Longest Path', 'value': morphology_data.size_longest_path, 'unit': 'pixels'},
                {'feature': 'Number of Leaves', 'value': morphology_data.size_num_leaves, 'unit': 'count'},
                {'feature': 'Number of Branches', 'value': morphology_data.size_num_branches, 'unit': 'count'},
                {'feature': 'Ellipse Major Axis', 'value': morphology_data.size_ellipse_major_axis, 'unit': 'pixels'},
                {'feature': 'Ellipse Minor Axis', 'value': morphology_data.size_ellipse_minor_axis, 'unit': 'pixels'},
                {'feature': 'Ellipse Angle', 'value': morphology_data.size_ellipse_angle, 'unit': 'degrees'},
                {'feature': 'Ellipse Eccentricity', 'value': morphology_data.size_ellipse_eccentricity, 'unit': 'ratio'},
                {'feature': 'Center of Mass X', 'value': morphology_data.size_center_of_mass.get('x', 0), 'unit': 'pixels'},
                {'feature': 'Center of Mass Y', 'value': morphology_data.size_center_of_mass.get('y', 0), 'unit': 'pixels'},
                {'feature': 'Ellipse Center X', 'value': morphology_data.size_ellipse_center.get('x', 0), 'unit': 'pixels'},
                {'feature': 'Ellipse Center Y', 'value': morphology_data.size_ellipse_center.get('y', 0), 'unit': 'pixels'},
                {'feature': 'Number of Branch Points', 'value': len(morphology_data.morph_branch_pts), 'unit': 'count'},
                {'feature': 'Number of Tips', 'value': len(morphology_data.morph_tips), 'unit': 'count'},
                {'feature': 'Number of Segments', 'value': len(morphology_data.morph_segment_path_length), 'unit': 'count'},
                {'feature': 'Average Segment Path Length', 'value': sum(morphology_data.morph_segment_path_length) / len(morphology_data.morph_segment_path_length) if morphology_data.morph_segment_path_length else 0, 'unit': 'pixels'},
                {'feature': 'Average Segment Euclidean Length', 'value': sum(morphology_data.morph_segment_eu_length) / len(morphology_data.morph_segment_eu_length) if morphology_data.morph_segment_eu_length else 0, 'unit': 'pixels'},
                {'feature': 'Average Segment Curvature', 'value': sum(morphology_data.morph_segment_curvature) / len(morphology_data.morph_segment_curvature) if morphology_data.morph_segment_curvature else 0, 'unit': 'radians'},
                {'feature': 'Average Segment Angle', 'value': sum(morphology_data.morph_segment_angle) / len(morphology_data.morph_segment_angle) if morphology_data.morph_segment_angle else 0, 'unit': 'degrees'},
                {'feature': 'Average Segment Tangent Angle', 'value': sum(morphology_data.morph_segment_tangent_angle) / len(morphology_data.morph_segment_tangent_angle) if morphology_data.morph_segment_tangent_angle else 0, 'unit': 'degrees'},
                {'feature': 'Average Segment Insertion Angle', 'value': sum(morphology_data.morph_segment_insertion_angle) / len(morphology_data.morph_segment_insertion_angle) if morphology_data.morph_segment_insertion_angle else 0, 'unit': 'degrees'}
            ])
            # Morphology images base and typed image URLs
            morphologyImagesBase = f"https://plant-analysis-data.s3.us-east-2.amazonaws.com/results/{species}_results/timeline_images/{plant_id}/{date}/morphology/images/" 
            expected_types = [
                'skeleton',
                'branch_pts',
                'tip_pts',
                'segmented_id',
                'path_lengths',
                'euclidean_lengths',
                'curvature',
                'angles',
                'tangent_angles',
                'insertion_angles',
                'size_analysis',
                'filled_segments',
                'pruned_200',
                'pruned_100',
                'pruned_50',
                'pruned_30',
                'pruned_10'
            ]
            for t in expected_types:
                morphologyImages[t] = f"{morphologyImagesBase}{t}.png"
        else:
            # Fallback: no DB row. List S3 to build morphologyImages so UI can still render
            try:
                s3 = boto3.client('s3', region_name='us-east-2')
                bucket = "plant-analysis-data"
                prefix = f"results/{species}_results/timeline_images/{plant_id}/{date}/morphology/images/"
                paginator = s3.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
                files = []
                for page in page_iterator:
                    if 'Contents' in page:
                        files.extend([obj['Key'] for obj in page['Contents'] if obj['Key'].endswith('.png')])
                if files:
                    morphologyImagesBase = f"https://{bucket}.s3.us-east-2.amazonaws.com/{prefix}"
                    # Expected names without extension
                    expected_types = [
                        'skeleton','branch_pts','tip_pts','segmented_id','path_lengths','euclidean_lengths',
                        'curvature','angles','tangent_angles','insertion_angles','size_analysis','filled_segments',
                        'pruned_200','pruned_100','pruned_50','pruned_30','pruned_10'
                    ]
                    available = {f.split('/')[-1].replace('.png',''): f for f in files}
                    for t in expected_types:
                        if t in available:
                            morphologyImages[t] = f"https://{bucket}.s3.us-east-2.amazonaws.com/{available[t]}"
            except Exception as s3e:
                print(f"S3 fallback for morphology images failed: {s3e}")
        
        result = {
            "mainImages": mainImages,
            "textureImages": textureImages,
            "vegetationIndicesImages": vegImages,
            "vegetationIndicesTable": vegTable,
            "textureFeaturesTable": textureTable,
            "morphologyFeaturesTable": morphologyTable,
            "morphologyImagesBase": morphologyImagesBase,
            "morphologyImages": morphologyImages
        }
        
        print(f"Returning morphology table with {len(morphologyTable)} items")
        return result
        
    except Exception as e:
        print(f"Error getting plant tab data: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving tab data: {str(e)}")


@router.get("/plant-timeline/{species}/{plant_id}/vegetation/{index_type}")
def get_vegetation_timeline(species: str, plant_id: str, index_type: str, db: Session = Depends(get_db)):
    """
    Get timeline data for a specific vegetation index.
    """
    try:
        timeline_data = db.query(VegetationIndexTimeline).filter(
            VegetationIndexTimeline.plant_id == f"{species}_{plant_id}",
            VegetationIndexTimeline.index_type == index_type
        ).order_by(VegetationIndexTimeline.date_captured).all()
        
        return {
            "plant_id": f"{species}_{plant_id}",
            "index_type": index_type,
            "timeline": [
                {
                    "date": str(v.date_captured),
                    "mean": v.mean,
                    "median": v.median,
                    "std": v.std,
                    "q25": v.q25,
                    "q75": v.q75,
                    "min": v.min,
                    "max": v.max,
                    "image_key": f"https://plant-analysis-data.s3.us-east-2.amazonaws.com/results/{species}_results/timeline_images/{plant_id}/{v.date_captured}/vegetation_indices/{index_type}.png"
                } for v in timeline_data
            ]
        }
        
    except Exception as e:
        print(f"Error getting vegetation timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving vegetation timeline: {str(e)}")

@router.get("/available-plants")
def get_available_plants(db: Session = Depends(get_db)):
    """
    Get all available species and their plants with dates.
    """
    try:
        # Helper function to extract plant number for sorting
        def extract_plant_number(plant_id):
            """Extract numeric part from plant ID for sorting"""
            import re
            # Find all numbers in the plant ID
            numbers = re.findall(r'\d+', plant_id)
            if numbers:
                # Return the first number found, converted to int for proper numerical sorting
                return int(numbers[0])
            # If no numbers found, return 0 to put at the beginning
            return 0
        
        # Get all plants grouped by species
        all_plants = PlantService.get_all_plants(db)
        
        # Group plants by species
        species_data = {}
        for plant in all_plants:
            if plant.species not in species_data:
                species_data[plant.species] = []
            
            # Extract plant ID from the full ID (remove species prefix)
            plant_id_short = plant.id.replace(f"{plant.species}_", "")
            
            species_data[plant.species].append({
                "id": plant_id_short,
                "full_id": plant.id,
                "name": plant.name,
                "dates_captured": [str(date) for date in plant.dates_captured] if plant.dates_captured else []
            })
        
        # Sort plants numerically within each species
        for species in species_data:
            species_data[species].sort(key=lambda plant: extract_plant_number(plant["id"]))
        
        return {
            "species": list(species_data.keys()),
            "plants_by_species": species_data
        }
        
    except Exception as e:
        print(f"Error getting available plants: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving available plants: {str(e)}")

@router.get("/plant-timeline/{species}/{plant_id}/texture/{band_name}/{texture_type}")
def get_texture_timeline(species: str, plant_id: str, band_name: str, texture_type: str, db: Session = Depends(get_db)):
    """
    Get timeline data for a specific texture feature.
    """
    try:
        timeline_data = db.query(TextureTimeline).filter(
            TextureTimeline.plant_id == f"{species}_{plant_id}",
            TextureTimeline.band_name == band_name,
            TextureTimeline.texture_type == texture_type
        ).order_by(TextureTimeline.date_captured).all()
        
        return {
            "plant_id": f"{species}_{plant_id}",
            "band_name": band_name,
            "texture_type": texture_type,
            "timeline": [
                {
                    "date": str(t.date_captured),
                    "mean": t.mean,
                    "median": t.median,
                    "std": t.std,
                    "q25": t.q25,
                    "q75": t.q75,
                    "min": t.min,
                    "max": t.max,
                    "image_key": f"https://plant-analysis-data.s3.us-east-2.amazonaws.com/results/{species}_results/timeline_images/{plant_id}/{t.date_captured}/texture/{band_name}/{texture_type}.png"
                } for t in timeline_data
            ]
        }
        
    except Exception as e:
        print(f"Error getting texture timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving texture timeline: {str(e)}")

@router.get("/plant-timeline/{species}/{plant_id}/morphology/{feature}")
def get_morphology_timeline(species: str, plant_id: str, feature: str, db: Session = Depends(get_db)):
    """
    Get timeline data for a specific morphology feature.
    Supported features: size_area, size_convex_hull_area, size_solidity, size_perimeter, size_width, size_height,
    size_longest_path, size_center_of_mass, size_convex_hull_vertices, size_ellipse_center, size_ellipse_major_axis,
    size_ellipse_minor_axis, size_ellipse_angle, size_ellipse_eccentricity, size_num_leaves, size_num_branches
    """
    try:
        # Map requested feature to MorphologyTimeline field or derived value
        def extract_value(m: MorphologyTimeline) -> float:
            if feature == "size_area":
                return m.size_area
            if feature == "size_convex_hull_area":
                return m.size_convex_hull_area
            if feature == "size_solidity":
                return m.size_solidity
            if feature == "size_perimeter":
                return m.size_perimeter
            if feature == "size_width":
                return m.size_width
            if feature == "size_height":
                return m.size_height
            if feature == "size_longest_path":
                return m.size_longest_path
            if feature == "size_center_of_mass":
                # Use X coordinate by default for scalar timeline
                return float(m.size_center_of_mass.get("x", 0)) if isinstance(m.size_center_of_mass, dict) else 0.0
            if feature == "size_convex_hull_vertices":
                return float(len(m.size_convex_hull_vertices)) if isinstance(m.size_convex_hull_vertices, list) else 0.0
            if feature == "size_ellipse_center":
                # Use X coordinate by default for scalar timeline
                return float(m.size_ellipse_center.get("x", 0)) if isinstance(m.size_ellipse_center, dict) else 0.0
            if feature == "size_ellipse_major_axis":
                return m.size_ellipse_major_axis
            if feature == "size_ellipse_minor_axis":
                return m.size_ellipse_minor_axis
            if feature == "size_ellipse_angle":
                return m.size_ellipse_angle
            if feature == "size_ellipse_eccentricity":
                return m.size_ellipse_eccentricity
            if feature == "size_num_leaves":
                return float(m.size_num_leaves)
            if feature == "size_num_branches":
                return float(m.size_num_branches)
            raise HTTPException(status_code=400, detail=f"Unsupported morphology feature: {feature}")

        timeline_data = db.query(MorphologyTimeline).filter(
            MorphologyTimeline.plant_id == f"{species}_{plant_id}"
        ).order_by(MorphologyTimeline.date_captured).all()

        # Build uniform response with 'mean'/'median' populated by the value for chart compatibility
        result_timeline = []
        for m in timeline_data:
            val = extract_value(m)
            result_timeline.append({
                "date": str(m.date_captured),
                "mean": val,
                "median": val,
                "std": 0,
                "q25": val,
                "q75": val,
                "min": val,
                "max": val,
                "image_key": f"https://plant-analysis-data.s3.us-east-2.amazonaws.com/results/{species}_results/timeline_images/{plant_id}/{m.date_captured}/morphology/images/"
            })

        return {
            "plant_id": f"{species}_{plant_id}",
            "feature": feature,
            "timeline": result_timeline
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting morphology timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving morphology timeline: {str(e)}")

@router.get("/plant-dates/{species}/{plant_id}")
def get_plant_dates(species: str, plant_id: str, db: Session = Depends(get_db)):
    """
    Get available dates for a specific plant from plants.dates_captured.
    """
    try:
        plant = db.query(Plant).filter(
            Plant.id == f"{species}_{plant_id}"
        ).first()
        
        if not plant:
            raise HTTPException(status_code=404, detail="Plant not found")
        
        return {
            "plant_id": f"{species}_{plant_id}",
            "dates": sorted(plant.dates_captured)
        
        }
        
    except Exception as e:
        print(f"Error getting plant dates: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving plant dates: {str(e)}")

@router.post("/download-images-zip")
async def download_images_zip(request: DownloadImagesZipRequest):
    """
    Download multiple images as a zip file.
    Fetches images from S3 server-side and creates a zip file.
    """
    try:
        from urllib.parse import urlparse, unquote
        from botocore.exceptions import ClientError
        
        image_urls = request.image_urls
        tab_name = request.tab_name
        
        if not image_urls or len(image_urls) == 0:
            raise HTTPException(status_code=400, detail="No image URLs provided")
        
        s3 = boto3.client('s3', region_name='us-east-2')
        zip_buffer = BytesIO()
        
        # Create zip file in memory
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, url in enumerate(image_urls):
                try:
                    # Decode URL
                    decoded_url = unquote(url)
                    parsed_url = urlparse(decoded_url)
                    
                    # Validate it's an S3 URL
                    if 's3' not in parsed_url.netloc or 'amazonaws.com' not in parsed_url.netloc:
                        print(f"Warning: Skipping non-S3 URL: {url}")
                        continue
                    
                    # Extract bucket and key
                    netloc = parsed_url.netloc
                    dot_index = netloc.find('.')
                    if dot_index == -1:
                        print(f"Warning: Invalid S3 URL format: {url}")
                        continue
                    
                    bucket = netloc[:dot_index]
                    key = parsed_url.path.lstrip('/')
                    
                    # Extract filename from URL for zip entry
                    filename = key.split('/')[-1] or f"image_{idx + 1}.png"
                    
                    # Fetch image from S3
                    try:
                        obj = s3.get_object(Bucket=bucket, Key=key)
                        image_data = obj['Body'].read()
                        
                        if not image_data or len(image_data) == 0:
                            print(f"Warning: Empty image data for {url}")
                            continue
                        
                        # Add to zip
                        zip_file.writestr(filename, image_data)
                        print(f"✓ Added to zip: {filename} ({len(image_data)} bytes)")
                        
                    except ClientError as s3_error:
                        error_code = s3_error.response.get('Error', {}).get('Code', '')
                        print(f"✗ S3 error for {url}: {error_code}")
                        # Continue with other images
                        continue
                        
                except Exception as e:
                    print(f"✗ Error processing {url}: {str(e)}")
                    # Continue with other images
                    continue
        
        # Check if zip has any files
        zip_buffer.seek(0)
        if zip_buffer.getvalue() == b'':
            raise HTTPException(status_code=404, detail="No images could be downloaded")
        
        # Prepare zip for download
        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()
        
        return StreamingResponse(
            iter([zip_data]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={tab_name}_{int(__import__('time').time())}.zip",
                "Content-Length": str(len(zip_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating zip file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating zip file: {str(e)}")

@router.get("/proxy-image")
def proxy_image(url: str = Query(..., description="URL of the image to proxy")):
    """
    Proxy endpoint to fetch images from S3 using boto3.
    This bypasses CORS restrictions by fetching images server-side.
    
    Example URL: https://plant-analysis-data.s3.us-east-2.amazonaws.com/results/Sorghum_results/timeline_images/plant10/2024-12-10/mask.png
    """
    try:
        from urllib.parse import urlparse, unquote
        from botocore.exceptions import ClientError
        
        # Decode URL in case it's encoded (handles %2F, %3A, etc.)
        original_url = url
        url = unquote(url)
        
        if not url:
            raise HTTPException(status_code=400, detail="URL parameter is required")
        
        parsed_url = urlparse(url)
        
        # Validate it's an S3 URL
        if 's3' not in parsed_url.netloc or 'amazonaws.com' not in parsed_url.netloc:
            raise HTTPException(status_code=403, detail="Only S3 URLs are allowed")
        
        # Extract bucket and key from S3 URL
        # Format: https://bucket.s3.region.amazonaws.com/key
        # Example: https://plant-analysis-data.s3.us-east-2.amazonaws.com/results/Sorghum_results/timeline_images/plant10/2024-12-10/mask.png
        netloc = parsed_url.netloc
        
        # Parse bucket name (everything before the first dot)
        # For: plant-analysis-data.s3.us-east-2.amazonaws.com
        # Bucket is: plant-analysis-data
        dot_index = netloc.find('.')
        if dot_index == -1:
            raise HTTPException(status_code=400, detail="Invalid S3 URL format: no bucket found")
        
        bucket = netloc[:dot_index]
        
        # Key is the full path after the domain (remove leading slash)
        key = parsed_url.path.lstrip('/')
        
        # Debug logging
        print(f"=== PROXY IMAGE REQUEST ===")
        print(f"Original URL param: {original_url}")
        print(f"Decoded URL: {url}")
        print(f"Parsed netloc: {netloc}")
        print(f"Bucket: '{bucket}'")
        print(f"Key: '{key}'")
        print(f"Full path: {parsed_url.path}")
        print(f"==========================")
        
        # Fetch from S3 using boto3
        s3 = boto3.client('s3', region_name='us-east-2')
        
        try:
            # First, verify the object exists (this gives better error messages)
            try:
                s3.head_object(Bucket=bucket, Key=key)
                print(f"✓ Object exists in S3: {key}")
            except ClientError as head_error:
                error_code = head_error.response.get('Error', {}).get('Code', '')
                if error_code == '404' or error_code == 'NoSuchKey':
                    print(f"✗ Image NOT FOUND in S3: bucket={bucket}, key={key}")
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Image not found in S3. Bucket: {bucket}, Key: {key}"
                    )
                else:
                    print(f"✗ S3 head_object error: {head_error}")
                    raise
            
            # Now get the object
            obj = s3.get_object(Bucket=bucket, Key=key)
            print(f"✓ Successfully retrieved object from S3")
        except HTTPException:
            raise
        except ClientError as s3_error:
            error_code = s3_error.response.get('Error', {}).get('Code', '')
            error_msg = s3_error.response.get('Error', {}).get('Message', str(s3_error))
            print(f"✗ S3 ClientError: Code={error_code}, Message={error_msg}")
            if error_code == 'NoSuchKey' or error_code == '404':
                raise HTTPException(
                    status_code=404, 
                    detail=f"Image not found in S3. Bucket: {bucket}, Key: {key}"
                )
            raise HTTPException(
                status_code=500, 
                detail=f"S3 error ({error_code}): {error_msg}"
            )
        
        # Read image data as bytes
        image_data = obj['Body'].read()
        
        # Verify we got actual binary data
        if not isinstance(image_data, bytes):
            image_data = bytes(image_data)
        
        # Verify it's not empty
        if len(image_data) == 0:
            raise HTTPException(status_code=500, detail="Received empty image from S3")
        
        # Verify it's actually an image (check PNG/JPEG magic bytes)
        is_png = image_data[:8] == b'\x89PNG\r\n\x1a\n'
        is_jpeg = image_data[:2] == b'\xff\xd8'
        
        if not (is_png or is_jpeg):
            print(f"Warning: Image doesn't have valid PNG/JPEG magic bytes. First 8 bytes: {image_data[:8]}")
        
        # Determine content type
        if is_png or key.lower().endswith('.png'):
            content_type = 'image/png'
        elif is_jpeg or key.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        else:
            content_type = 'image/png'  # Default to PNG
        
        print(f"Returning image: {len(image_data)} bytes, type: {content_type}")
        
        # Return the image as binary data with proper headers
        return Response(
            content=image_data,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "*",
                "Content-Disposition": f'inline; filename="{key.split("/")[-1]}"',
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(image_data))
            }
        )
    except HTTPException as http_ex:
        # Re-raise HTTP exceptions as-is (they're already properly formatted)
        raise http_ex
    except Exception as e:
        print(f"Unexpected error in proxy-image: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return JSON error instead of letting FastAPI return HTML
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching image: {str(e)}"
        )