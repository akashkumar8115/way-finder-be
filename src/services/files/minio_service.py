# import os
# import io
# import uuid
# import logging
# import cv2
# import numpy as np
# from datetime import datetime
# from typing import List, Dict, Optional, BinaryIO
# from fastapi import UploadFile, HTTPException
# from minio import Minio
# from PIL import Image
# import urllib.parse
# from src.core.authentication.cred_load import (
#     MINIO_ENDPOINT,
#     MINIO_ACCESS_KEY,
#     MINIO_SECRET_KEY,
#     MINIO_USE_SSL,
#     MINIO_BUCKET,
# )

# # Logging configuration
# logger = logging.getLogger(__name__)

# # MinIO configuration - use environment variables in production
# MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "bucket-dev-b5be.up.railway.app")
# MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "1EW9qnL6dXW39M45uWMz")
# MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "kRMFiEnoGhu4LjgqHyEFyyr3ETmKuDOEm69fXoOa")
# MINIO_BUCKET = os.getenv("MINIO_BUCKET", "my-bucket")
# MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "true").lower() == "true"
# MINIO_PORT = int(os.getenv("MINIO_PORT", "443"))

# # Allowed file types
# ALLOWED_EXTENSIONS = {
#     'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
#     'video': ['mp4', 'avi', 'mov', 'wmv', 'webm', 'mkv'],
#     'document': ['pdf']
# }

# class MinioService:
#     def __init__(self):
#         # Initialize MinIO client
#         self.minio_client = Minio(
#             MINIO_ENDPOINT,
#             access_key=MINIO_ACCESS_KEY,
#             secret_key=MINIO_SECRET_KEY,
#             secure=MINIO_USE_SSL
#         )
        
#         # Create bucket if it doesn't exist
#         try:
#             if not self.minio_client.bucket_exists(MINIO_BUCKET):
#                 self.minio_client.make_bucket(MINIO_BUCKET)
#             logger.info(f"MinIO bucket '{MINIO_BUCKET}' is ready")
#         except Exception as e:
#             logger.error(f"Error initializing MinIO bucket: {str(e)}")
    
#     def get_file_extension(self, filename: str) -> str:
#         """Extract file extension from filename"""
#         return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
#     def get_file_type(self, extension: str) -> Optional[str]:
#         """Determine file type based on extension"""
#         for file_type, extensions in ALLOWED_EXTENSIONS.items():
#             if extension in extensions:
#                 return file_type
#         return None
    
#     def get_file_resolution(self, file_type: str, file_content: bytes) -> str:
#         """
#         Get resolution for any file type (image, video, etc.)
        
#         Args:
#             file_type: Type of the file ('image', 'video', etc.)
#             file_content: Binary content of the file
            
#         Returns:
#             String representation of resolution (e.g., "1920x1080")
#         """
#         try:
#             if file_type == 'image':
#                 # Get resolution for images using PIL
#                 img = Image.open(io.BytesIO(file_content))
#                 return f"{img.width}x{img.height}"
            
#             elif file_type == 'video':
#                 # Create a temporary file to analyze with OpenCV
#                 temp_file = f"/tmp/{uuid.uuid4()}.mp4"
#                 with open(temp_file, 'wb') as f:
#                     f.write(file_content)
                
#                 try:
#                     cap = cv2.VideoCapture(temp_file)
#                     if not cap.isOpened():
#                         return "unknown"
                    
#                     width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#                     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#                     cap.release()
                    
#                     return f"{width}x{height}"
#                 finally:
#                     # Clean up the temporary file
#                     if os.path.exists(temp_file):
#                         os.remove(temp_file)
            
#             # For other file types
#             return "unknown"
            
#         except Exception as e:
#             logger.error(f"Error getting file resolution: {str(e)}")
#             return "unknown"
    
#     def get_video_length(self, file_type: str, file_content: bytes) -> Optional[float]:
#         """
#         Get video length or default length for images
        
#         Args:
#             file_type: Type of the file ('image', 'video', etc.)
#             file_content: Binary content of the file
            
#         Returns:
#             Duration in seconds as a float
#         """
#         try:
#             if file_type == 'image':
#                 # Default length for images: 15 seconds
#                 return 15.0
            
#             elif file_type == 'video':
#                 # Create a temporary file to analyze with OpenCV
#                 temp_file = f"/tmp/{uuid.uuid4()}.mp4"
#                 with open(temp_file, 'wb') as f:
#                     f.write(file_content)
                
#                 try:
#                     cap = cv2.VideoCapture(temp_file)
#                     if not cap.isOpened():
#                         return None
                    
#                     # Get frame count and fps to calculate duration
#                     fps = cap.get(cv2.CAP_PROP_FPS)
#                     frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    
#                     # Calculate duration in seconds
#                     duration = frame_count / fps if fps > 0 else None
#                     cap.release()
                    
#                     return duration
#                 finally:
#                     # Clean up the temporary file
#                     if os.path.exists(temp_file):
#                         os.remove(temp_file)
            
#             # For other file types
#             return None
            
#         except Exception as e:
#             logger.error(f"Error getting video length: {str(e)}")
#             return None
        
#     def get_file_size_in_mb(self, file_size: str) -> float:
#         return str(round(file_size / (1024 * 1024), 2))
    
    
#     async def upload_file(self, file: UploadFile, folder: str = "default") -> Dict:
#         """Upload a single file to MinIO and return its metadata"""
#         try:
#             # Generate a unique filename
#             extension = self.get_file_extension(file.filename)
#             file_type = self.get_file_type(extension)
            
#             if not file_type:
#                 raise ValueError(f"File has unsupported extension: {extension}")
                
#             # Create a unique filename with timestamp and UUID
#             timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#             unique_id = str(uuid.uuid4())[:8]
#             new_filename = f"{timestamp}_{unique_id}.{extension}"
            
#             # Define the object path in MinIO
#             object_name = f"{folder}/{file_type}/{new_filename}"
            
#             # Read file content
#             file_content = await file.read()
#             file_size = len(file_content)

#             file_size_mb = self.get_file_size_in_mb(file_size)

            
#             # Get resolution for all file types
#             resolution = self.get_file_resolution(file_type, file_content)
            
#             # Calculate length for videos and images
#             length = self.get_video_length(file_type, file_content)
            
#             # Convert bytes to BytesIO object
#             file_data = io.BytesIO(file_content)
            
#             # Upload to MinIO
#             self.minio_client.put_object(
#                 bucket_name=MINIO_BUCKET,
#                 object_name=object_name,
#                 data=file_data,
#                 length=file_size,
#                 content_type=file.content_type
#             )
            
#             # Generate URL
#             protocol = "https" if MINIO_USE_SSL else "http"
#             port_part = f":{MINIO_PORT}" if (MINIO_PORT != 443 and MINIO_USE_SSL) or (MINIO_PORT != 80 and not MINIO_USE_SSL) else ""
#             url = f"{protocol}://{MINIO_ENDPOINT}{port_part}/{MINIO_BUCKET}/{object_name}"
            
#             return {
#                 "name": file.filename,
#                 "stored_name": new_filename,
#                 "type": file_type,
#                 "size": file_size_mb + " MB",
#                 "resolution": resolution,
#                 "length": length,
#                 "content_url": url,
#                 "description": "",
#                 "metadata": {
#                     "original_filename": file.filename,
#                     "content_type": file.content_type,
#                     "upload_timestamp": timestamp
#                 }
#             }
        
#         except Exception as e:
#             logger.error(f"Error uploading {file.filename}: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
#     async def upload_files(self, files: List[UploadFile], folder: str = "default") -> Dict:
#         """Upload multiple files to MinIO and return their metadata"""
#         result = []
#         errors = []
        
#         for file in files:
#             try:
#                 file_result = await self.upload_file(file, folder)
#                 result.append(file_result)
#             except Exception as e:
#                 errors.append({
#                     "name": file.filename,
#                     "status": "error",
#                     "message": str(e)
#                 })
        
#         return {
#             "status": "success",
#             "message": f"Uploaded {len(result)} files successfully" if not errors else f"Uploaded {len(result)} files with {len(errors)} errors",
#             "data": result,
#             "errors": errors
#         }
    
#     async def delete_content_from_minio(self, content_path: str) -> bool:
#         """Delete a file from MinIO storage"""
#         try:
            
#             # Parse the URL to extract bucket name and object path
#             parsed_url = urllib.parse.urlparse(content_path)
#             path_parts = parsed_url.path.strip('/').split('/', 1)
            
#             if len(path_parts) < 2:
#                 logger.error(f"Invalid MinIO URL format: {content_path}")
#                 return False
            
#             bucket_name = path_parts[0]
#             object_name = path_parts[1]
            
#             # Remove the object from MinIO
#             self.minio_client.remove_object(bucket_name, object_name)
#             logger.info(f"Successfully deleted file from MinIO: {object_name}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error deleting file from MinIO: {e}")
#             return False


#     async def delete_file(self, object_name: str) -> Dict:
    
#         try:
#             # Remove the object from MinIO
#             self.minio_client.remove_object(
#                 bucket_name=MINIO_BUCKET,
#                 object_name=object_name
#             )
            
#             return {
#                 "status": "success",
#                 "message": f"File {object_name} deleted successfully"
#             }
#         except Exception as e:
#             logger.error(f"Error deleting file {object_name}: {str(e)}")
#             return {
#                 "status": "error",
#                 "message": f"Failed to delete file: {str(e)}"
#             }







import os
import io
import uuid
import logging
import cv2
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, BinaryIO, Tuple
from fastapi import UploadFile, HTTPException
from minio import Minio
from minio.error import S3Error
from PIL import Image
import urllib.parse
from src.core.authentication.cred_load import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_USE_SSL,
    MINIO_BUCKET,
)

# Logging configuration
logger = logging.getLogger(__name__)

# MinIO configuration - use environment variables in production
# https://bucket-dev-52d1.up.railway.app:443
# MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "bucket-dev-b5be.up.railway.app")
# MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "1EW9qnL6dXW39M45uWMz")
# MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "kRMFiEnoGhu4LjgqHyEFyyr3ETmKuDOEm69fXoOa")
# MINIO_BUCKET = os.getenv("MINIO_BUCKET", "my-bucket")
# MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "true").lower() == "true"
# MINIO_PORT = int(os.getenv("MINIO_PORT", "443"))

# new way finder 
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "bucket-dev-52d1.up.railway.app")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "TR6mpX0tGjqNPp8Zi9RJ")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "f4k88MoaLBr3gg9cA94AjoRNlKw6jyeqnp2zDc4V")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "way-finder")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "true").lower() == "true"
MINIO_PORT = int(os.getenv("MINIO_PORT", "443"))
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

class MinioService:
    def __init__(self):
        # Initialize MinIO client with lazy initialization
        self.minio_client = None
        self.initialized = False
        self.initialization_error = None
        
    def _initialize_client(self):
        """Initialize the MinIO client when first needed"""
        if self.initialized:
            return
            
        try:
            if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
                raise Exception("MinIO credentials not provided")
                
            logger.info(f"Initializing MinIO client with endpoint: {MINIO_ENDPOINT}")
            
            self.minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_USE_SSL
            )
            
            # Test connection and create bucket if it doesn't exist
            try:
                if not self.minio_client.bucket_exists(MINIO_BUCKET):
                    self.minio_client.make_bucket(MINIO_BUCKET)
                    logger.info(f"Created MinIO bucket '{MINIO_BUCKET}'")
                else:
                    logger.info(f"MinIO bucket '{MINIO_BUCKET}' already exists")
                    
                logger.info("MinIO service initialized successfully")
                self.initialized = True
                
            except S3Error as e:
                logger.error(f"MinIO S3 error during initialization: {str(e)}")
                self.initialization_error = f"MinIO S3 error: {str(e)}"
                self.initialized = False
                
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Failed to initialize MinIO service: {str(e)}")
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
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        
        # Check MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            return False, f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        
        # Check file extension
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
        """
        Get resolution for any file type (image, video, etc.)
        
        Args:
            file_type: Type of the file ('image', 'video', etc.)
            file_content: Binary content of the file
            
        Returns:
            String representation of resolution (e.g., "1920x1080")
        """
        try:
            if file_type == 'image':
                # Get resolution for images using PIL
                img = Image.open(io.BytesIO(file_content))
                return f"{img.width}x{img.height}"
            
            elif file_type == 'video':
                # Create a temporary file to analyze with OpenCV
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
                    # Clean up the temporary file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            
            # For other file types
            return "unknown"
            
        except Exception as e:
            logger.error(f"Error getting file resolution: {str(e)}")
            return "unknown"
    
    def get_video_length(self, file_type: str, file_content: bytes) -> Optional[float]:
        """
        Get video length or default length for images
        
        Args:
            file_type: Type of the file ('image', 'video', etc.)
            file_content: Binary content of the file
            
        Returns:
            Duration in seconds as a float
        """
        try:
            if file_type == 'image':
                # Default length for images: 15 seconds
                return 15.0
            
            elif file_type == 'video':
                # Create a temporary file to analyze with OpenCV
                temp_file = f"/tmp/{uuid.uuid4()}.mp4"
                with open(temp_file, 'wb') as f:
                    f.write(file_content)
                
                try:
                    cap = cv2.VideoCapture(temp_file)
                    if not cap.isOpened():
                        return None
                    
                    # Get frame count and fps to calculate duration
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    
                    # Calculate duration in seconds
                    duration = frame_count / fps if fps > 0 else None
                    cap.release()
                    
                    return duration
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            
            # For other file types
            return None
            
        except Exception as e:
            logger.error(f"Error getting video length: {str(e)}")
            return None
        
    def get_file_size_in_mb(self, file_size: int) -> str:
        """Convert file size from bytes to MB"""
        return str(round(file_size / (1024 * 1024), 2))
    
    async def upload_floor_plan(self, file: UploadFile, floor_id: str, building_id: str) -> dict:
        """Upload floor plan image to MinIO - similar to Wasabi service"""
        try:
            # Initialize client if not already done
            self._initialize_client()
            
            if not self.initialized:
                return {
                    "success": False,
                    "error": f"MinIO service not available: {self.initialization_error or 'Unknown error'}"
                }
            
            # Validate file
            is_valid, error_message = self._validate_file(file)
            if not is_valid:
                return {
                    "success": False,
                    "error": error_message
                }
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Generate unique filename
            file_extension = file.filename.lower().split('.')[-1] if file.filename else 'jpg'
            unique_filename = f"floor-plans/{building_id}/{floor_id}/{uuid.uuid4()}.{file_extension}"
            
            # Get file info
            file_info = self._get_file_info(file_content, file.content_type)
            
            # Convert bytes to BytesIO object
            file_data = io.BytesIO(file_content)
            
            # Upload to MinIO
            self.minio_client.put_object(
                bucket_name=MINIO_BUCKET,
                object_name=unique_filename,
                data=file_data,
                length=file_size,
                content_type=file.content_type,
                metadata={
                    'floor_id': floor_id,
                    'building_id': building_id,
                    'original_filename': file.filename or 'unknown',
                    'dimensions': file_info.get('dimensions', ''),
                    'uploaded_by': 'system'
                }
            )
            
            # Generate public URL
            protocol = "https" if MINIO_USE_SSL else "http"
            port_part = f":{MINIO_PORT}" if (MINIO_PORT != 443 and MINIO_USE_SSL) or (MINIO_PORT != 80 and not MINIO_USE_SSL) else ""
            file_url = f"{protocol}://{MINIO_ENDPOINT}{port_part}/{MINIO_BUCKET}/{unique_filename}"
            
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
            
        except S3Error as e:
            logger.error(f"MinIO S3Error uploading file: {str(e)}")
            return {
                "success": False,
                "error": f"Storage service error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            return {
                "success": False,
                "error": f"File upload failed: {str(e)}"
            }



    async def delete_floor_plan(self, file_url: str) -> bool:
        """Delete floor plan from MinIO"""
        try:
            self._initialize_client()
            
            if not self.initialized or not self.minio_client:
                return False
            
            # Extract filename from URL
            # Parse the URL to extract object path
            parsed_url = urllib.parse.urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                logger.error(f"Invalid MinIO URL format: {file_url}")
                return False
            
            object_name = path_parts[1]  # Skip bucket name, get object path
            
            # Delete from MinIO
            self.minio_client.remove_object(MINIO_BUCKET, object_name)
            
            logger.info(f"Successfully deleted floor plan: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_url}: {str(e)}")
            return False
    
    async def upload_file(self, file: UploadFile, folder: str = "default") -> Dict:
        """Upload a single file to MinIO and return its metadata"""
        try:
            # Initialize client if not already done
            self._initialize_client()
            
            if not self.initialized:
                raise HTTPException(status_code=500, detail=f"MinIO service not available: {self.initialization_error}")
            
            # Generate a unique filename
            extension = self.get_file_extension(file.filename)
            file_type = self.get_file_type(extension)
            
            if not file_type:
                raise ValueError(f"File has unsupported extension: {extension}")
                
            # Create a unique filename with timestamp and UUID
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            new_filename = f"{timestamp}_{unique_id}.{extension}"
            
            # Define the object path in MinIO
            object_name = f"{folder}/{file_type}/{new_filename}"
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)

            file_size_mb = self.get_file_size_in_mb(file_size)
            
            # Get resolution for all file types
            resolution = self.get_file_resolution(file_type, file_content)
            
            # Calculate length for videos and images
            length = self.get_video_length(file_type, file_content)
            
            # Convert bytes to BytesIO object
            file_data = io.BytesIO(file_content)
            
            # Upload to MinIO
            self.minio_client.put_object(
                bucket_name=MINIO_BUCKET,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=file.content_type
            )
            
            # Generate URL
            protocol = "https" if MINIO_USE_SSL else "http"
            port_part = f":{MINIO_PORT}" if (MINIO_PORT != 443 and MINIO_USE_SSL) or (MINIO_PORT != 80 and not MINIO_USE_SSL) else ""
            url = f"{protocol}://{MINIO_ENDPOINT}{port_part}/{MINIO_BUCKET}/{object_name}"
            
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
        """Upload multiple files to MinIO and return their metadata"""
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
    
    async def delete_content_from_minio(self, content_path: str) -> bool:
        """Delete a file from MinIO storage"""
        try:
            # Initialize client if not already done
            self._initialize_client()
            
            if not self.initialized:
                return False
            
            # Parse the URL to extract bucket name and object path
            parsed_url = urllib.parse.urlparse(content_path)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                logger.error(f"Invalid MinIO URL format: {content_path}")
                return False
            
            bucket_name = path_parts[0]
            object_name = path_parts[1]
            
            # Remove the object from MinIO
            self.minio_client.remove_object(bucket_name, object_name)
            logger.info(f"Successfully deleted file from MinIO: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            return False

    async def delete_file(self, object_name: str) -> Dict:
        """Delete a specific file from MinIO by object name"""
        try:
            # Initialize client if not already done
            self._initialize_client()
            
            if not self.initialized:
                return {
                    "status": "error",
                    "message": f"MinIO service not available: {self.initialization_error}"
                }
            
            # Remove the object from MinIO
            self.minio_client.remove_object(
                bucket_name=MINIO_BUCKET,
                object_name=object_name
            )
            
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


# Create a singleton instance - similar to wasabi_service
minio_service = MinioService()


