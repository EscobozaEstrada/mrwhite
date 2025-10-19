"""
Shared File Processing Utility for FastAPI Chat Service

This utility provides common file processing functionality that can be used
by both AsyncChatService and AsyncHealthService to avoid code duplication.
Enhanced with image processing capabilities.
"""

import logging
import base64
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AsyncFileProcessor:
    """Shared async file processing utility"""
    
    @staticmethod
    async def extract_text_content(content: bytes, content_type: str) -> Optional[str]:
        """Extract text content from file using appropriate processing"""
        try:
            if content_type.startswith("text/"):
                return content.decode("utf-8")
            elif content_type == "application/pdf":
                return await AsyncFileProcessor._extract_pdf_text(content)
            elif content_type.startswith("image/"):
                return await AsyncFileProcessor._extract_image_text(content)
            elif content_type.startswith("audio/"):
                # Audio files require transcription, not text extraction
                # Return None here as audio will be handled by VoiceService
                logger.info(f"Audio file detected: {content_type} - will be processed by VoiceService")
                return None
            else:
                logger.warning(f"Unsupported file type for text extraction: {content_type}")
                return None
                
        except Exception as e:
            logger.error(f"Text extraction error: {str(e)}")
            return None
    
    @staticmethod
    async def _extract_pdf_text(content: bytes) -> Optional[str]:
        """Extract text from PDF using PyPDF2"""
        try:
            import io
            from PyPDF2 import PdfReader
            
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"Page {page_num + 1}:\n{page_text.strip()}")
                except Exception as e:
                    logger.warning(f"Error extracting text from PDF page {page_num + 1}: {str(e)}")
                    continue
            
            if text_content:
                extracted_text = "\n\n".join(text_content)
                logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF ({len(pdf_reader.pages)} pages)")
                return extracted_text
            else:
                logger.warning("No text could be extracted from PDF")
                return "PDF processed but no readable text found"
                
        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            return "PDF processing unavailable - PyPDF2 not installed"
        except Exception as e:
            logger.error(f"PDF text extraction error: {str(e)}")
            return f"PDF processing error: {str(e)}"
    
    @staticmethod
    async def _extract_image_text(content: bytes) -> Optional[str]:
        """Extract text from image using OCR (pytesseract)"""
        try:
            import io
            from PIL import Image
            import pytesseract
            
            # Load image from bytes
            image = Image.open(io.BytesIO(content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using OCR
            extracted_text = pytesseract.image_to_string(image, lang='eng')
            
            if extracted_text.strip():
                logger.info(f"Successfully extracted {len(extracted_text)} characters from image using OCR")
                return extracted_text.strip()
            else:
                logger.warning("No text found in image")
                return "Image processed but no text detected"
                
        except ImportError:
            logger.error("OCR dependencies not installed. Install with: pip install pytesseract Pillow")
            return "Image text extraction unavailable - OCR libraries not installed"
        except Exception as e:
            logger.error(f"Image OCR error: {str(e)}")
            return f"Image processing error: {str(e)}. Note: Tesseract OCR must be installed on the system."
    
    @staticmethod
    def create_file_metadata(
        filename: str,
        content_type: str,
        description: str = "",
        conversation_id: Optional[int] = None,
        file_type: str = "general"
    ) -> dict:
        """Create standardized file metadata with smart document prioritization support"""
        from datetime import datetime, timezone
        
        return {
            "filename": filename,
            "content_type": content_type,
            "description": description,
            "conversation_id": conversation_id,
            "file_type": file_type,
            "upload_time": datetime.now().isoformat(),
            # 🎯 Smart document prioritization metadata
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": None,  # Will be set by document service
            "upload_sequence": None  # Will be set by document service
        }
    
    @staticmethod
    def create_processing_result(
        filename: str,
        success: bool,
        message: str,
        content_length: int = 0,
        extracted_text: str = None
    ) -> dict:
        """Create standardized file processing result"""
        result = {
            "filename": filename,
            "status": "success" if success else "error",
            "message": message
        }
        
        if content_length > 0:
            result["content_length"] = content_length
            
        if extracted_text:
            result["text_preview"] = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            result["extracted_text"] = extracted_text  # Include full text for analysis
            
        return result
    
    @staticmethod
    async def process_image_for_vision(content: bytes, content_type: str, filename: str) -> Dict[str, Any]:
        """
        Process image for vision analysis
        
        Args:
            content: Raw image bytes
            content_type: MIME type
            filename: Original filename
            
        Returns:
            Dictionary with processed image data
        """
        try:
            # Convert to base64 for API transmission
            base64_content = base64.b64encode(content).decode('utf-8')
            
            # Basic validation
            if not content_type.startswith('image/'):
                raise ValueError(f"Invalid image type: {content_type}")
            
            # Get file size
            file_size = len(content)
            
            return {
                "content": base64_content,
                "content_type": content_type,
                "filename": filename,
                "size": file_size,
                "is_image": True,
                "ready_for_vision": True
            }
            
        except Exception as e:
            logger.error(f"Error processing image for vision: {str(e)}")
            return {
                "content": None,
                "content_type": content_type,
                "filename": filename,
                "size": len(content),
                "is_image": True,
                "ready_for_vision": False,
                "error": str(e)
            }
    
    @staticmethod
    async def categorize_files(files: list) -> Dict[str, Any]:
        """
        Categorize files into images, audio, and documents
        
        Args:
            files: List of file dictionaries
            
        Returns:
            Dictionary with 'images', 'audio', and 'documents' lists
        """
        images = []
        audio = []
        documents = []
        
        for file in files:
            content_type = file.get('content_type', '')
            if content_type.startswith('image/'):
                images.append(file)
            elif content_type.startswith('audio/'):
                audio.append(file)
            else:
                documents.append(file)
        
        return {
            "images": images,
            "audio": audio,
            "documents": documents,
            "has_images": len(images) > 0,
            "has_audio": len(audio) > 0,
            "has_documents": len(documents) > 0,
            "total_files": len(files)
        }