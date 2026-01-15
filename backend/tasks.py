import boto3
import json
import os
from backend.celery_worker import celery_app
from backend.services.pipeline_runner import process_plant_image

# Expose Celery app under the conventional name so `celery -A backend.tasks` finds it
app = celery_app

@celery_app.task
def analyze_plant_task(bucket, key, species, segmentation_method="sam3"):
    s3 = boto3.client('s3')
    # key example: Sorghum_dataset/2024-12-04/plant7/plant7_frame8.tif
    parts = key.split('/')
    date = parts[1]
    plant_id = parts[2]
    input_filename = os.path.basename(key)  # e.g., 'plant7_frame8.tif'
    base, _ = os.path.splitext(input_filename)  # e.g., 'plant7_frame8'
    result_filename = f"{base}_result.json"  # e.g., 'plant7_frame8_result.json'
    result = process_plant_image(bucket, key, segmentation_method=segmentation_method)
    # Save ONLY in results/ folder
    # result_key = f"results/{date}/{plant_id}/{result_filename}"
    result_key = f"results/{species}_results/{plant_id}/{date}/{result_filename}"
    s3.put_object(Bucket=bucket, Key=result_key, Body=json.dumps(result))
    return {"result_key": result_key}
