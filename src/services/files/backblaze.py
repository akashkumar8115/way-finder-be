import os
import io
import uuid
import logging
import cv2
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, BinaryIO, Tuple
from fastapi import UploadFile, HTTPException
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from PIL import Image
import urllib.parse

# Logging configuration
logger = logging.getLogger(__name__)

# Backblaze B2 configuration
# B2_KEY_ID = os.getenv("B2_KEY_ID", "0030e0811d615e5000000000c")
# B2_APP_KEY = os.getenv("B2_APP_KEY", "K003FzyWYqeXgLkC9a85822BubupHkU")
# B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "dev-wf-saas-objs")
# B2_ENDPOINT = os.getenv("B2_ENDPOINT", "s3.eu-central-003.backblazeb2.com")
# B2_REGION = os.getenv("B2_REGION", "us-east-005")

# B2_KEY_ID=30030e0811d615e5000000000b
# B2_APP_KEY=K0030NgFDxhPyyI5VlIBHj9zM1ZmvJE
# B2_BUCKET_NAME=dev-wf-saas-objs
# B2_ENDPOINT=s3.eu-central-003.backblazeb2.com
# B2_REGION=us-east-005
#backblaze b2 
# B2_KEY_ID=0030e0811d615e50000000009
# B2_APP_KEY=K003w8p01FG2pFOD3VJkH9rbJX4DtSA
# B2_BUCKET_NAME=uat-ds-saas-objs
# B2_ENDPOINT=https://s3.eu-central-003.backblazeb2.com
# B2_REGION=us-east-005

B2_KEY_ID = os.getenv("B2_KEY_ID", "0030e0811d615e5000000000c")
B2_APP_KEY = os.getenv("B2_APP_KEY", "K003FzyWYqeXgLkC9a85822BubupHkU")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "dev-wf-saas-objs")
B2_ENDPOINT = os.getenv("B2_ENDPOINT", "s3.eu-central-003.backblazeb2.com")
B2_REGION = os.getenv("B2_REGION", "us-east-005")

# Allowed file types
ALLOWED_EXTENSIONS = {
    'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
    'video': ['mp4', 'avi', 'mov', 'wmv', 'webm', 'mkv'],
    'document': ['pdf']
}

# Floor plan specific configurations
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
    'image/webp', 'image/bmp'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

class B2Service:
    def __init__(self):
        # Initialize B2 client with lazy initialization
        self.b2_api = None
        self.bucket = None
        self.initialized = False
        self.initialization_error = None
        
    def _initialize_client(self):
        """Initialize the Backblaze B2 client when first needed"""
        if self.initialized:
            return
            
        try:
            if not B2_KEY_ID or not B2_APP_KEY:
                raise Exception("B2 credentials not provided")
                
            logger.info(f"Initializing B2 client with endpoint: {B2_ENDPOINT}")
            
            info = InMemoryAccountInfo()
            self.b2_api = B2Api(info)
            self.b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
            
            try:
                self.bucket = self.b2_api.get_bucket_by_name(B2_BUCKET_NAME)
                logger.info(f"Connected to B2 bucket '{B2_BUCKET_NAME}'")
                self.initialized = True
                
            except Exception as e:
                logger.error(f"B2 error during bucket access: {str(e)}")
                self.initialization_error = f"B2 error: {str(e)}"
                self.initialized = False
                
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Failed to initialize B2 service: {str(e)}")
            self.initialized = False
    
    def get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    def get_file_type(self, extension: str) -> Optional[str]:
        """Determine file type based on extension"""
        for file_type, extensions in ALLOWED_EXTENSIONS.items():
            if extension in extensions:
                return file_type
        return None
    
    def _validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """Validate uploaded file for floor plans"""
        if file.size and file.size > MAX_FILE_SIZE:
            return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        
        if file.content_type not in ALLOWED_MIME_TYPES:
            return False, f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        
        if file.filename:
            file_extension = file.filename.lower().split('.')[-1]
            if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
                return False, f"File extension '.{file_extension}' not allowed. Allowed extensions: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        
        return True, ""
    
    def _get_file_info(self, file_content: bytes, content_type: str) -> dict:
        """Extract file information like dimensions"""
        info = {
            "size": len(file_content),
            "dimensions": None
        }
        
        try:
            if content_type.startswith('image/'):
                with Image.open(io.BytesIO(file_content)) as img:
                    info["dimensions"] = f"{img.width}x{img.height}"
                    info["format"] = img.format
        except Exception as e:
            logger.warning(f"Could not extract image info: {str(e)}")
        
        return info

    def get_file_resolution(self, file_type: str, file_content: bytes) -> str:
        """Get resolution for any file type"""
        try:
            if file_type == 'image':
                img = Image.open(io.BytesIO(file_content))
                return f"{img.width}x{img.height}"
            elif file_type == 'video':
                temp_file = f"/tmp/{uuid.uuid4()}.mp4"
                with open(temp_file, 'wb') as f:
                    f.write(file_content)
                
                try:
                    cap = cv2.VideoCapture(temp_file)
                    if not cap.isOpened():
                        return "unknown"
                    
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    return f"{width}x{height}"
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            return "unknown"
        except Exception as e:
            logger.error(f"Error getting file resolution: {str(e)}")
            return "unknown"
    
    def get_video_length(self, file_type: str, file_content: bytes) -> Optional[float]:
        """Get video length or default length for images"""
        try:
            if file_type == 'image':
                return 15.0
            elif file_type == 'video':
                temp_file = f"/tmp/{uuid.uuid4()}.mp4"
                with open(temp_file, 'wb') as f:
                    f.write(file_content)
                
                try:
                    cap = cv2.VideoCapture(temp_file)
                    if not cap.isOpened():
                        return None
                    
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else None
                    cap.release()
                    return duration
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            return None
        except Exception as e:
            logger.error(f"Error getting video length: {str(e)}")
            return None
        
    def get_file_size_in_mb(self, file_size: int) -> str:
        """Convert file size from bytes to MB"""
        return str(round(file_size / (1024 * 1024), 2))
    
    async def upload_floor_plan(self, file: UploadFile, floor_id: str, building_id: str) -> dict:
        """Upload floor plan image to Backblaze B2"""
        try:
            self._initialize_client()
            
            if not self.initialized:
                return {
                    "success": False,
                    "error": f"B2 service not available: {self.initialization_error or 'Unknown error'}"
                }
            
            is_valid, error_message = self._validate_file(file)
            if not is_valid:
                return {
                    "success": False,
                    "error": error_message
                }
            
            file_content = await file.read()
            file_size = len(file_content)
            
            file_extension = file.filename.lower().split('.')[-1] if file.filename else 'jpg'
            unique_filename = f"floor-plans/{building_id}/{floor_id}/{uuid.uuid4()}.{file_extension}"
            
            file_info = self._get_file_info(file_content, file.content_type)
            
            file_data = io.BytesIO(file_content)
            
            self.bucket.upload_bytes(
                data_bytes=file_content,
                file_name=unique_filename,
                content_type=file.content_type,
                file_infos={
                    'floor_id': floor_id,
                    'building_id': building_id,
                    'original_filename': file.filename or 'unknown',
                    'dimensions': file_info.get('dimensions', ''),
                    'uploaded_by': 'system'
                }
            )
            
            file_url = f"https://{B2_ENDPOINT}/{B2_BUCKET_NAME}/{unique_filename}"
            
            logger.info(f"Successfully uploaded floor plan: {unique_filename}")
            
            return {
                "success": True,
                "file_url": file_url,
                "filename": unique_filename,
                "original_filename": file.filename,
                "file_size": file_info["size"],
                "dimensions": file_info.get("dimensions"),
                "content_type": file.content_type
            }
            
        except Exception as e:
            logger.error(f"B2 error uploading file: {str(e)}")
            return {
                "success": False,
                "error": f"Storage service error: {str(e)}"
            }

    async def delete_floor_plan(self, file_url: str) -> bool:
        """Delete floor plan from Backblaze B2"""
        try:
            self._initialize_client()
            
            if not self.initialized or not self.bucket:
                return False
            
            parsed_url = urllib.parse.urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                logger.error(f"Invalid B2 URL format: {file_url}")
                return False
            
            object_name = path_parts[1]
            
            self.bucket.delete_file_version(self.bucket.get_file_info_by_name(object_name).id_)
            
            logger.info(f"Successfully deleted floor plan: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_url}: {str(e)}")
            return False
    
    async def upload_file(self, file: UploadFile, folder: str = "default") -> Dict:
        """Upload a single file to Backblaze B2 and return its metadata"""
        try:
            self._initialize_client()
            
            if not self.initialized:
                raise HTTPException(status_code=500, detail=f"B2 service not available: {self.initialization_error}")
            
            extension = self.get_file_extension(file.filename)
            file_type = self.get_file_type(extension)
            
            if not file_type:
                raise ValueError(f"File has unsupported extension: {extension}")
                
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            new_filename = f"{timestamp}_{unique_id}.{extension}"
            
            object_name = f"{folder}/{file_type}/{new_filename}"
            
            file_content = await file.read()
            file_size = len(file_content)
            file_size_mb = self.get_file_size_in_mb(file_size)
            
            resolution = self.get_file_resolution(file_type, file_content)
            length = self.get_video_length(file_type, file_content)
            
            self.bucket.upload_bytes(
                data_bytes=file_content,
                file_name=object_name,
                content_type=file.content_type
            )
            
            url = f"https://{B2_ENDPOINT}/{B2_BUCKET_NAME}/{object_name}"
            
            return {
                "name": file.filename,
                "stored_name": new_filename,
                "type": file_type,
                "size": file_size_mb + " MB",
                "resolution": resolution,
                "length": length,
                "content_url": url,
                "description": "",
                "metadata": {
                    "original_filename": file.filename,
                    "content_type": file.content_type,
                    "upload_timestamp": timestamp
                }
            }
        
        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    async def upload_files(self, files: List[UploadFile], folder: str = "default") -> Dict:
        """Upload multiple files to Backblaze B2 and return their metadata"""
        result = []
        errors = []
        
        for file in files:
            try:
                file_result = await self.upload_file(file, folder)
                result.append(file_result)
            except Exception as e:
                errors.append({
                    "name": file.filename,
                    "status": "error",
                    "message": str(e)
                })
        
        return {
            "status": "success",
            "message": f"Uploaded {len(result)} files successfully" if not errors else f"Uploaded {len(result)} files with {len(errors)} errors",
            "data": result,
            "errors": errors
        }
    
    async def delete_content_from_b2(self, content_path: str) -> bool:
        """Delete a file from Backblaze B2 storage"""
        try:
            self._initialize_client()
            
            if not self.initialized:
                return False
            
            parsed_url = urllib.parse.urlparse(content_path)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                logger.error(f"Invalid B2 URL format: {content_path}")
                return False
            
            object_name = path_parts[1]
            
            self.bucket.delete_file_version(self.bucket.get_file_info_by_name(object_name).id_)
            logger.info(f"Successfully deleted file from B2: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from B2: {e}")
            return False

    async def delete_file(self, object_name: str) -> Dict:
        """Delete a specific file from Backblaze B2 by object name"""
        try:
            self._initialize_client()
            
            if not self.initialized:
                return {
                    "status": "error",
                    "message": f"B2 service not available: {self.initialization_error}"
                }
            
            self.bucket.delete_file_version(self.bucket.get_file_info_by_name(object_name).id_)
            
            return {
                "status": "success",
                "message": f"File {object_name} deleted successfully"
            }
        except Exception as e:
            logger.error(f"Error deleting file {object_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to delete file: {str(e)}"
            }

# Create a singleton instance
b2_service = B2Service()