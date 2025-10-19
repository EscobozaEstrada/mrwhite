from typing import Optional, Tuple, Dict, Any, List
import os
from flask import current_app
from werkzeug.datastructures import FileStorage
from app.utils.file_handler import extract_and_store, query_user_docs
from app.utils.s3_handler import upload_file_to_s3, get_s3_url, delete_file_from_s3


class FileService:
    """Service class for handling file operations"""
    
    @staticmethod
    def process_document_file(file: FileStorage, user_id: int) -> Tuple[bool, str, Optional[str]]:
        """
        Process and store a document file
        
        Returns:
            Tuple of (success: bool, message: str, s3_url: Optional[str])
        """
        try:
            return extract_and_store(file, user_id)
        except Exception as e:
            current_app.logger.error(f"Error processing document file: {str(e)}")
            return False, f"Error processing document: {str(e)}", None
    
    @staticmethod
    def process_image_file(file: FileStorage) -> Dict[str, Any]:
        """
        Process and store an image file
        
        Returns:
            Dictionary with success status, message, and URL
        """
        try:
            # Debug log
            current_app.logger.info(f"Starting process_image_file for {file.filename}")
            
            # Try to use the ImageService if available
            try:
                from app.services.image_service import ImageService
                current_app.logger.info("ImageService imported successfully")
                image_service = ImageService()
                current_app.logger.info("ImageService instance created")
                
                # Get user_id from Flask g object if available
                from flask import g
                user_id = getattr(g, 'user_id', None)
                current_app.logger.info(f"Retrieved user_id from Flask g: {user_id}")
                
                if user_id:
                    # Use the comprehensive image service
                    current_app.logger.info(f"Calling ImageService.process_image_upload for user_id: {user_id}")
                    success, message, image_data = image_service.process_image_upload(
                        file=file,
                        user_id=user_id
                    )
                    current_app.logger.info(f"ImageService.process_image_upload result: success={success}, message={message}")
                    
                    if success and image_data:
                        current_app.logger.info(f"ImageService processed image successfully: {image_data.get('url')}")
                        return {
                            'success': True,
                            'message': message,
                            'url': image_data.get('url'),
                            'description': image_data.get('description'),
                            'type': 'image'
                        }
                else:
                    current_app.logger.error(f"Cannot use ImageService: No user_id in Flask g object")
            except Exception as img_error:
                current_app.logger.error(f"Could not use ImageService, falling back to basic image handling: {str(img_error)}")
                import traceback
                current_app.logger.error(f"ImageService error traceback: {traceback.format_exc()}")
            
            # Fallback to basic image handling
            current_app.logger.info(f"Using fallback image handling for {file.filename}")
            
            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(os.getcwd(), 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            # Save file locally
            file_path = os.path.join(uploads_dir, file.filename)
            file.save(file_path)
            current_app.logger.info(f"Saved file locally to {file_path}")
            
            # Optionally upload to S3
            try:
                current_app.logger.info(f"Attempting S3 upload for {file_path}")
                s3_success, s3_url = FileService.upload_to_s3(file_path, file.filename, file.content_type)
                if s3_success:
                    # Remove local file after successful S3 upload
                    os.remove(file_path)
                    current_app.logger.info(f"S3 upload successful, URL: {s3_url}")
                    return {
                        'success': True,
                        'message': f'Image {file.filename} uploaded successfully to S3',
                        'url': s3_url,
                        'type': 'image',
                        'file_type': 'image/' + file_path.split('.')[-1].lower()
                    }
                else:
                    current_app.logger.warning(f"S3 upload failed, s3_url: {s3_url}")
            except Exception as s3_error:
                current_app.logger.warning(f"S3 upload failed, keeping local file: {str(s3_error)}")
                import traceback
                current_app.logger.warning(f"S3 upload error traceback: {traceback.format_exc()}")
            
            current_app.logger.info(f"Using local file URL: /uploads/{file.filename}")
            return {
                'success': True,
                'message': f'Image {file.filename} saved locally',
                'url': f'/uploads/{file.filename}',
                'type': 'image',
                'file_type': 'image/' + file.filename.split('.')[-1].lower()
            }
            
        except Exception as e:
            current_app.logger.error(f"Error processing image file: {str(e)}")
            import traceback
            current_app.logger.error(f"Image processing error traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'Error processing image: {str(e)}',
                'url': None,
                'type': 'image'
            }
    
    @staticmethod
    def upload_to_s3(file_path: str, object_name: str, content_type: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Upload file to S3
        
        Returns:
            Tuple of (success: bool, s3_url: Optional[str])
        """
        try:
            success, message, s3_url = upload_file_to_s3(file_path, object_name, content_type)
            if success:
                return True, s3_url
            else:
                return False, None
        except Exception as e:
            current_app.logger.error(f"Error uploading to S3: {str(e)}")
            return False, None
    
    @staticmethod
    def delete_from_s3(object_name: str) -> bool:
        """
        Delete file from S3
        
        Returns:
            Success status
        """
        try:
            return delete_file_from_s3(object_name)
        except Exception as e:
            current_app.logger.error(f"Error deleting from S3: {str(e)}")
            return False
    
    @staticmethod
    def query_user_documents(user_id: int, query: str, top_k: int = 3) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Query user's uploaded documents
        
        Returns:
            Tuple of (success: bool, message: str, documents: Optional[List[Dict]])
        """
        try:
            success, docs = query_user_docs(query, user_id, top_k)
            
            if not success:
                return False, "Error querying documents", None
            
            if not docs:
                return True, "No relevant documents found", []
            
            # Convert documents to dictionaries
            doc_results = []
            for doc in docs:
                doc_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'source': doc.metadata.get('source', 'Unknown')
                })
            
            return True, "Documents retrieved successfully", doc_results
            
        except Exception as e:
            current_app.logger.error(f"Error querying documents: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_allowed_file_types() -> Dict[str, List[str]]:
        """
        Get allowed file types for upload
        
        Returns:
            Dictionary of file type categories and their extensions
        """
        return {
            'documents': ['.pdf', '.txt', '.doc', '.docx'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'archives': ['.zip', '.rar', '.7z']
        }
    
    @staticmethod
    def is_allowed_file(filename: str) -> Tuple[bool, str]:
        """
        Check if file type is allowed
        
        Returns:
            Tuple of (is_allowed: bool, file_category: str)
        """
        if not filename or '.' not in filename:
            return False, 'unknown'
        
        extension = '.' + filename.rsplit('.', 1)[1].lower()
        allowed_types = FileService.get_allowed_file_types()
        
        for category, extensions in allowed_types.items():
            if extension in extensions:
                return True, category
        
        return False, 'unknown' 