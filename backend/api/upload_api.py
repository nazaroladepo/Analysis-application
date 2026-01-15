# upload_api.py - File upload to S3 with automatic analysis processing

import logging
import os
from typing import List, Dict
from pathlib import Path
import asyncio

import boto3
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file in root directory
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists() and not os.environ.get("AWS_ACCESS_KEY_ID"):
        load_dotenv(env_file)
        logger.info(f"upload_api: Loaded environment variables from {env_file}")
except (ImportError, Exception):
    pass

# S3 Configuration - load from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "plant-analysis-data")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("REGION", "us-east-2"))
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

router = APIRouter()

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

async def upload_file_to_s3(file: UploadFile, s3_key: str) -> bool:
    """Upload a file to S3. Returns True if successful, False otherwise."""
    try:
        s3 = get_s3_client()
        
        # Read file content
        content = await file.read()
        
        # Upload to S3
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or 'application/octet-stream'
        )
        
        logger.info(f"Successfully uploaded {file.filename} to S3: {s3_key}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upload {file.filename} to S3: {e}")
        return False

@router.post("/upload/raw-files")
async def upload_raw_files(
    files: List[UploadFile] = File(...),
    segmentation_method: str = Query("sam3", description="Segmentation method: 'sam3' (default) or 'rmbg'")
):
    """
    Upload raw plant image files to S3 and trigger analysis pipeline.
    
    Process:
    1. Upload files to S3 in 'Uploaded files' folder
    2. Trigger analysis pipeline for each file
    3. Save results to crop-specific folders nested under Uploaded_results:
       'results/Uploaded_results/{Species}_results/...'
    4. Save data to database using species parsed from filename
    
    Args:
        files: List of image files to upload
        segmentation_method: Segmentation method to use ("sam3" or "rmbg"). Default is "sam3".
    
    Returns upload status and processing status.
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        uploaded_files = []
        failed_uploads = []
        
        # Step 1: Upload files to S3
        logger.info(f"Starting upload of {len(files)} file(s)")
        for file in files:
            s3_key = f"Uploaded files/{file.filename}"
            success = await upload_file_to_s3(file, s3_key)
            
            if success:
                uploaded_files.append({
                    "filename": file.filename,
                    "s3_key": s3_key,
                    "status": "uploaded"
                })
            else:
                failed_uploads.append(file.filename)
        
        # Determine upload success
        total_files = len(files)
        files_uploaded = len(uploaded_files)
        files_failed_upload = len(failed_uploads)
        
        if files_uploaded == 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload all {total_files} file(s) to S3. Please check your AWS credentials and try again."
            )
        
        # Step 2: Process files through analysis pipeline
        logger.info(f"Starting analysis for {files_uploaded} file(s)")
        processing_results = []
        
        for file_info in uploaded_files:
            try:
                from backend.services.upload_processor import process_uploaded_file
                
                # Process file (this runs synchronously, but we could make it async)
                result = process_uploaded_file(file_info['s3_key'], file_info['filename'], segmentation_method=segmentation_method)
                file_info['status'] = "processed"
                file_info['processing_result'] = result
                processing_results.append({
                    'filename': file_info['filename'],
                    'success': True
                })
                logger.info(f"Successfully processed: {file_info['filename']}")
                
            except Exception as e:
                logger.error(f"Error processing {file_info['filename']}: {e}")
                file_info['status'] = "processing_failed"
                file_info['error'] = str(e)
                processing_results.append({
                    'filename': file_info['filename'],
                    'success': False,
                    'error': str(e)
                })
        
        # Count processing results
        files_processed = sum(1 for r in processing_results if r.get('success'))
        files_failed_processing = len(processing_results) - files_processed
        
        # If all files failed processing, delete them from S3
        if files_processed == 0 and files_uploaded > 0:
            logger.warning(f"All {files_uploaded} file(s) failed processing. Cleaning up uploaded files from S3.")
            s3 = get_s3_client()
            for file_info in uploaded_files:
                try:
                    s3.delete_object(Bucket=S3_BUCKET, Key=file_info['s3_key'])
                    logger.info(f"Deleted failed file from S3: {file_info['s3_key']}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_info['s3_key']} from S3: {e}")
        
        # Build response
        if files_processed == 0 and files_uploaded > 0:
            result = {
                "message": f"Upload failed: All {files_uploaded} file(s) failed during analysis. Files have been removed from storage.",
                "files_uploaded": files_uploaded,
                "files_failed_upload": files_failed_upload,
                "files_processed": files_processed,
                "files_failed_processing": files_failed_processing,
                "total_files": total_files,
                "uploaded_files": uploaded_files,
                "processing_results": processing_results,
                "all_processing_failed": True
            }
            # Return 200 so frontend can access the response data
            return JSONResponse(content=result, status_code=200)
        
        result = {
            "message": f"Upload and analysis complete! Processed {files_processed} of {files_uploaded} file(s)",
            "files_uploaded": files_uploaded,
            "files_failed_upload": files_failed_upload,
            "files_processed": files_processed,
            "files_failed_processing": files_failed_processing,
            "total_files": total_files,
            "uploaded_files": uploaded_files,
            "processing_results": processing_results
        }
        
        if failed_uploads:
            result["failed_uploads"] = failed_uploads
            result["warning"] = f"{files_failed_upload} file(s) failed to upload"
        
        if files_failed_processing > 0:
            result["processing_warning"] = f"{files_failed_processing} file(s) failed during analysis"
        
        # Return appropriate status code
        if files_failed_upload > 0 or files_failed_processing > 0:
            return JSONResponse(content=result, status_code=207)  # Multi-Status
        
        return JSONResponse(content=result, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_raw_files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/upload/result-files")
async def upload_result_files(files: List[UploadFile] = File(...)):
    """
    Upload result files to S3 in 'Uploaded files' folder.
    Returns success/failure based on actual S3 uploads.
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            # Upload to S3 in "Uploaded files" folder
            s3_key = f"Uploaded files/{file.filename}"
            success = await upload_file_to_s3(file, s3_key)
            
            if success:
                uploaded_files.append({
                    "filename": file.filename,
                    "s3_key": s3_key
                })
            else:
                failed_files.append(file.filename)
        
        # Determine overall success
        total_files = len(files)
        files_uploaded = len(uploaded_files)
        files_failed = len(failed_files)
        
        if files_uploaded == 0:
            # All files failed
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload all {total_files} file(s) to S3. Please check your AWS credentials and try again."
            )
        
        # Build response
        result = {
            "message": f"Successfully uploaded {files_uploaded} of {total_files} file(s) to S3",
            "files_uploaded": files_uploaded,
            "files_failed": files_failed,
            "total_files": total_files,
            "uploaded_files": uploaded_files
        }
        
        if failed_files:
            result["failed_files"] = failed_files
            result["warning"] = f"{files_failed} file(s) failed to upload"
            # Return 207 Multi-Status for partial success
            return JSONResponse(content=result, status_code=207)
        
        return JSONResponse(content=result, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_result_files: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
