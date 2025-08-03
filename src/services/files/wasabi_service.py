# import boto3
# import uuid
# import logging
# from typing import Optional, Tuple
# from botocore.exceptions import ClientError, NoCredentialsError
# from fastapi import HTTPException, UploadFile
# import os
# from PIL import Image
# import io

# logger = logging.getLogger(__name__)

# # Wasabi configuration
# WASABI_ACCESS_KEY = os.getenv("WASABI_ACCESS_KEY", "LYM37MA11OBK6KFJYQ0A")
# WASABI_SECRET_KEY = os.getenv("WASABI_SECRET_KEY", "B0zlbYlzQF70sa9PACRRraVOoJ0qEKQjB83VNwN1")
# WASABI_BUCKET_NAME = os.getenv("WASABI_BUCKET_NAME", "way-finder")
# WASABI_REGION = os.getenv("WASABI_REGION", "ap-southeast-1")
# WASABI_ENDPOINT_URL = os.getenv("WASABI_ENDPOINT_URL", "https://s3.wasabisys.com")

# # Allowed file types and extensions
# ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
# ALLOWED_MIME_TYPES = {
#     'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
#     'image/webp', 'image/bmp'
# }
# MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# class WasabiService:
#     """Service for handling file uploads to Wasabi storage"""
    
#     def __init__(self):
#         """Initialize Wasabi S3 client - lazy initialization"""
#         self.s3_client = None
#         self.initialized = False
#         self.initialization_error = None
        
#     def _initialize_client(self):
#         """Initialize the S3 client when first needed"""
#         if self.initialized:
#             return
            
#         try:
#             if not WASABI_ACCESS_KEY or not WASABI_SECRET_KEY:
#                 raise Exception("Wasabi credentials not provided")
                
#             self.s3_client = boto3.client(
#                 's3',
#                 endpoint_url=WASABI_ENDPOINT_URL,
#                 aws_access_key_id=WASABI_ACCESS_KEY,
#                 aws_secret_access_key=WASABI_SECRET_KEY,
#                 region_name=WASABI_REGION
#             )
            
#             # Test connection by listing buckets instead of checking specific bucket
#             try:
#                 self.s3_client.list_buckets()
#                 logger.info("Wasabi service initialized successfully")
#             except Exception as e:
#                 logger.warning(f"Wasabi connection test failed: {str(e)}")
#                 # Don't fail initialization, just log the warning
            
#             self.initialized = True
            
#         except Exception as e:
#             self.initialization_error = str(e)
#             logger.error(f"Failed to initialize Wasabi service: {str(e)}")
#             self.initialized = False
    
#     def _ensure_bucket_exists(self):
#         """Ensure the bucket exists, create if it doesn't"""
#         if not self.s3_client:
#             return False
            
#         try:
#             self.s3_client.head_bucket(Bucket=WASABI_BUCKET_NAME)
#             return True
#         except ClientError as e:
#             error_code = int(e.response['Error']['Code'])
#             if error_code == 404:
#                 # Bucket doesn't exist, try to create it
#                 try:
#                     self.s3_client.create_bucket(Bucket=WASABI_BUCKET_NAME)
#                     logger.info(f"Created bucket: {WASABI_BUCKET_NAME}")
#                     return True
#                 except ClientError as create_error:
#                     logger.error(f"Failed to create bucket: {str(create_error)}")
#                     return False
#             else:
#                 logger.error(f"Error checking bucket: {str(e)}")
#                 return False
    
#     def _validate_file(self, file: UploadFile) -> Tuple[bool, str]:
#         """Validate uploaded file"""
#         # Check file size
#         if file.size and file.size > MAX_FILE_SIZE:
#             return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        
#         # Check MIME type
#         if file.content_type not in ALLOWED_MIME_TYPES:
#             return False, f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        
#         # Check file extension
#         if file.filename:
#             file_extension = file.filename.lower().split('.')[-1]
#             if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
#                 return False, f"File extension '.{file_extension}' not allowed. Allowed extensions: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        
#         return True, ""
    
#     def _get_file_info(self, file_content: bytes, content_type: str) -> dict:
#         """Extract file information like dimensions"""
#         info = {
#             "size": len(file_content),
#             "dimensions": None
#         }
        
#         try:
#             if content_type.startswith('image/'):
#                 with Image.open(io.BytesIO(file_content)) as img:
#                     info["dimensions"] = f"{img.width}x{img.height}"
#                     info["format"] = img.format
#         except Exception as e:
#             logger.warning(f"Could not extract image info: {str(e)}")
        
#         return info
    
#     async def upload_floor_plan(self, file: UploadFile, floor_id: str, building_id: str) -> dict:
#         """Upload floor plan image to Wasabi"""
#         try:
#             # Initialize client if not already done
#             self._initialize_client()
            
#             if not self.initialized:
#                 return {
#                     "success": False,
#                     "error": f"Wasabi service not available: {self.initialization_error or 'Unknown error'}"
#                 }
            
#             # Validate file
#             is_valid, error_message = self._validate_file(file)
#             if not is_valid:
#                 return {
#                     "success": False,
#                     "error": error_message
#                 }
            
#             # Ensure bucket exists
#             if not self._ensure_bucket_exists():
#                 return {
#                     "success": False,
#                     "error": "Could not access or create storage bucket"
#                 }
            
#             # Read file content
#             file_content = await file.read()
            
#             # Generate unique filename
#             file_extension = file.filename.lower().split('.')[-1] if file.filename else 'jpg'
#             unique_filename = f"floor-plans/{building_id}/{floor_id}/{uuid.uuid4()}.{file_extension}"
            
#             # Get file info
#             file_info = self._get_file_info(file_content, file.content_type)
            
#             # Upload to Wasabi
#             self.s3_client.put_object(
#                 Bucket=WASABI_BUCKET_NAME,
#                 Key=unique_filename,
#                 Body=file_content,
#                 ContentType=file.content_type,
#                 Metadata={
#                     'floor_id': floor_id,
#                     'building_id': building_id,
#                     'original_filename': file.filename or 'unknown',
#                     'dimensions': file_info.get('dimensions', ''),
#                     'uploaded_by': 'system'
#                 }
#             )
            
#             # Generate public URL
#             file_url = f"{WASABI_ENDPOINT_URL}/{WASABI_BUCKET_NAME}/{unique_filename}"
            
#             logger.info(f"Successfully uploaded floor plan: {unique_filename}")
            
#             return {
#                 "success": True,
#                 "file_url": file_url,
#                 "filename": unique_filename,
#                 "original_filename": file.filename,
#                 "file_size": file_info["size"],
#                 "dimensions": file_info.get("dimensions"),
#                 "content_type": file.content_type
#             }
            
#         except Exception as e:
#             logger.error(f"Unexpected error uploading file: {str(e)}")
#             return {
#                 "success": False,
#                 "error": f"File upload failed: {str(e)}"
#             }
    
#     async def delete_floor_plan(self, file_url: str) -> bool:
#         """Delete floor plan from Wasabi"""
#         try:
#             self._initialize_client()
            
#             if not self.initialized or not self.s3_client:
#                 return False
            
#             # Extract filename from URL
#             filename = file_url.replace(f"{WASABI_ENDPOINT_URL}/{WASABI_BUCKET_NAME}/", "")
            
#             # Delete from Wasabi
#             self.s3_client.delete_object(
#                 Bucket=WASABI_BUCKET_NAME,
#                 Key=filename
#             )
            
#             logger.info(f"Successfully deleted floor plan: {filename}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error deleting file {file_url}: {str(e)}")
#             return False


# # Create a singleton instance - but don't initialize it yet
# wasabi_service = WasabiService()
















import boto3
import uuid
import logging
from typing import Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile
import os
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Wasabi configuration with corrected defaults
WASABI_ACCESS_KEY = os.getenv("WASABI_ACCESS_KEY", "LYM37MA11OBK6KFJYQ0A")
WASABI_SECRET_KEY = os.getenv("WASABI_SECRET_KEY", "B0zlbYlzQF70sa9PACRRraVOoJ0qEKQjB83VNwN1")
WASABI_BUCKET_NAME = os.getenv("WASABI_BUCKET_NAME", "way-finder")
WASABI_REGION = os.getenv("WASABI_REGION", "us-east-1")  # Fixed region
WASABI_ENDPOINT_URL = os.getenv("WASABI_ENDPOINT_URL", "https://s3.us-east-1.wasabisys.com")  # Fixed endpoint

# Allowed file types and extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
    'image/webp', 'image/bmp'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class WasabiService:
    """Service for handling file uploads to Wasabi storage"""
    
    def __init__(self):
        """Initialize Wasabi S3 client - lazy initialization"""
        self.s3_client = None
        self.initialized = False
        self.initialization_error = None
        
    def _initialize_client(self):
        """Initialize the S3 client when first needed"""
        if self.initialized:
            return
            
        try:
            if not WASABI_ACCESS_KEY or not WASABI_SECRET_KEY:
                raise Exception("Wasabi credentials not provided")
            
            logger.info(f"Initializing Wasabi client with region: {WASABI_REGION}")
            logger.info(f"Using endpoint: {WASABI_ENDPOINT_URL}")
            
            self.s3_client = boto3.client(
                's3',
                endpoint_url=WASABI_ENDPOINT_URL,
                aws_access_key_id=WASABI_ACCESS_KEY,
                aws_secret_access_key=WASABI_SECRET_KEY,
                region_name=WASABI_REGION,
                config=boto3.session.Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'virtual'
                    }
                )
            )
            
            # Test connection with better error handling
            try:
                response = self.s3_client.list_buckets()
                logger.info("Wasabi service initialized successfully")
                logger.info(f"Available buckets: {[bucket['Name'] for bucket in response.get('Buckets', [])]}")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'AuthorizationHeaderMalformed':
                    logger.error(f"Authorization header malformed. Check region setting. Current: {WASABI_REGION}")
                    raise Exception(f"Wasabi region configuration error. Expected region might be different from {WASABI_REGION}")
                else:
                    logger.warning(f"Wasabi connection test failed: {str(e)}")
                    # Don't fail initialization for other errors
            
            self.initialized = True
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Failed to initialize Wasabi service: {str(e)}")
            self.initialized = False
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        if not self.s3_client:
            return False
            
        try:
            # Try to get bucket location first
            try:
                location_response = self.s3_client.get_bucket_location(Bucket=WASABI_BUCKET_NAME)
                logger.info(f"Bucket {WASABI_BUCKET_NAME} exists in region: {location_response.get('LocationConstraint', 'us-east-1')}")
                return True
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    # Bucket doesn't exist, try to create it
                    try:
                        if WASABI_REGION == 'us-east-1':
                            # For us-east-1, don't specify LocationConstraint
                            self.s3_client.create_bucket(Bucket=WASABI_BUCKET_NAME)
                        else:
                            # For other regions, specify LocationConstraint
                            self.s3_client.create_bucket(
                                Bucket=WASABI_BUCKET_NAME,
                                CreateBucketConfiguration={'LocationConstraint': WASABI_REGION}
                            )
                        logger.info(f"Created bucket: {WASABI_BUCKET_NAME}")
                        return True
                    except ClientError as create_error:
                        logger.error(f"Failed to create bucket: {str(create_error)}")
                        return False
                elif error_code == 301:
                    logger.error(f"Bucket exists but in wrong region. Check your region configuration.")
                    return False
                else:
                    logger.error(f"Error checking bucket: {str(e)}")
                    return False
        except Exception as e:
            logger.error(f"Unexpected error checking bucket: {str(e)}")
            return False
    
    def _validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """Validate uploaded file"""
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
    
    async def upload_floor_plan(self, file: UploadFile, floor_id: str, building_id: str) -> dict:
        """Upload floor plan image to Wasabi"""
        try:
            # Initialize client if not already done
            self._initialize_client()
            
            if not self.initialized:
                return {
                    "success": False,
                    "error": f"Wasabi service not available: {self.initialization_error or 'Unknown error'}"
                }
            
            # Validate file
            is_valid, error_message = self._validate_file(file)
            if not is_valid:
                return {
                    "success": False,
                    "error": error_message
                }
            
            # Ensure bucket exists
            if not self._ensure_bucket_exists():
                return {
                    "success": False,
                    "error": "Could not access or create storage bucket. Check your Wasabi configuration and region settings."
                }
            
            # Read file content
            file_content = await file.read()
            
            # Generate unique filename
            file_extension = file.filename.lower().split('.')[-1] if file.filename else 'jpg'
            unique_filename = f"floor-plans/{building_id}/{floor_id}/{uuid.uuid4()}.{file_extension}"
            
            # Get file info
            file_info = self._get_file_info(file_content, file.content_type)
            
            # Upload to Wasabi
            self.s3_client.put_object(
                Bucket=WASABI_BUCKET_NAME,
                Key=unique_filename,
                Body=file_content,
                ContentType=file.content_type,
                Metadata={
                    'floor_id': floor_id,
                    'building_id': building_id,
                    'original_filename': file.filename or 'unknown',
                    'dimensions': file_info.get('dimensions', ''),
                    'uploaded_by': 'system'
                }
            )
            
            # Generate public URL
            file_url = f"{WASABI_ENDPOINT_URL}/{WASABI_BUCKET_NAME}/{unique_filename}"
            
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
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Wasabi ClientError uploading file: {error_code} - {str(e)}")
            return {
                "success": False,
                "error": f"Storage service error: {error_code}"
            }
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            return {
                "success": False,
                "error": f"File upload failed: {str(e)}"
            }
    
    async def delete_floor_plan(self, file_url: str) -> bool:
        """Delete floor plan from Wasabi"""
        try:
            self._initialize_client()
            
            if not self.initialized or not self.s3_client:
                return False
            
            # Extract filename from URL
            filename = file_url.replace(f"{WASABI_ENDPOINT_URL}/{WASABI_BUCKET_NAME}/", "")
            
            # Delete from Wasabi
            self.s3_client.delete_object(
                Bucket=WASABI_BUCKET_NAME,
                Key=filename
            )
            
            logger.info(f"Successfully deleted floor plan: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_url}: {str(e)}")
            return False


# Create a singleton instance
wasabi_service = WasabiService()
