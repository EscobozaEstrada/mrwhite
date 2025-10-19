"""
Vision Service - Image processing and OpenAI Vision API integration
Handles image analysis, gallery storage, and vision-based chat responses
"""

import os
import uuid
import base64
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from PIL import Image as PILImage
import io

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import AsyncSessionLocal, UserImage, Message, Conversation
from services.shared.async_s3_service import AsyncS3Service
from services.shared.async_openai_pool_service import get_openai_pool
from services.shared.async_pinecone_service import AsyncPineconeService
from repositories.pet_repository import PetRepository

logger = logging.getLogger(__name__)

class VisionService:
    """
    Vision Service for image processing and OpenAI Vision API integration
    Handles image analysis, gallery storage, and chat integration
    """
    
    def __init__(self, cache_service=None, vector_service=None):
        self.cache_service = cache_service
        self.s3_service = AsyncS3Service()
        self.pet_repository = None  # Will be lazy-loaded when needed
        self.vector_service = vector_service or AsyncPineconeService()
        
        # Bedrock configuration for vision
        self.openai_pool = None  # Will be set by global pool
        # Claude 3 Haiku supports vision! Use it as default
        self.vision_model = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        # All these Claude 3+ models support vision
        self.vision_capable_models = [
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        ]
        self.max_tokens = 500
        self.temperature = 0.1
        
        # Image processing settings
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.allowed_formats = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
        
        # Performance tracking
        self.processing_stats = {
            "total_images_processed": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "gallery_saves": 0,
            "total_processing_time": 0.0
        }
        
    async def _get_openai_pool(self):
        """Get or initialize the OpenAI client pool"""
        if self.openai_pool is None:
            self.openai_pool = await get_openai_pool(pool_size=5)
        return self.openai_pool
    
    async def _get_user_pet_context_for_vision(self, user_id: int) -> Dict[str, Any]:
        """Get existing pet data to inform vision prompts"""
        try:
            from models import AsyncSessionLocal
            
            # Create proper async session and get pet profiles
            async with AsyncSessionLocal() as session:
                pet_repository = PetRepository(session)
                pet_profiles = await pet_repository.get_user_pets(user_id)
            
            context = {
                "has_pets": len(pet_profiles) > 0,
                "pets": [],
                "needs_basic_info": False
            }
            
            if pet_profiles:
                for pet in pet_profiles:
                    pet_dict = pet.to_dict() if hasattr(pet, 'to_dict') else {
                        'name': pet.name,
                        'breed': pet.breed,
                        'age': pet.age,
                        'weight': pet.weight,
                        'gender': pet.gender
                    }
                    
                    # Check if basic info is complete
                    basic_info_complete = bool(pet.name and pet.breed and pet.age)
                    missing_fields = []
                    
                    if hasattr(pet, 'get_missing_fields'):
                        missing_fields = pet.get_missing_fields()
                    else:
                        # Manual check for missing basic fields
                        if not pet.breed:
                            missing_fields.append('breed')
                        if not pet.age:
                            missing_fields.append('age')
                        if not pet.weight:
                            missing_fields.append('weight')
                        if not pet.gender:
                            missing_fields.append('gender')
                    
                    context["pets"].append({
                        "name": pet.name or "Unknown",
                        "breed": pet.breed,
                        "age": pet.age,
                        "basic_info_complete": basic_info_complete,
                        "missing_basic_fields": missing_fields
                    })
                    
                    # Mark if any pet needs basic info
                    if not basic_info_complete:
                        context["needs_basic_info"] = True
            
            logger.info(f"🐕 Pet context for user {user_id}: {len(context['pets'])} pets, needs_basic_info: {context['needs_basic_info']}")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error getting pet context: {str(e)}")
            return {"has_pets": False, "pets": [], "needs_basic_info": False}
    
    async def _generate_smart_vision_prompt(self, user_message: str, pet_context: Dict[str, Any]) -> str:
        """Generate contextually aware vision prompts based on existing pet data"""
        
        # Extract pet names for personalization
        pet_names = [pet["name"] for pet in pet_context.get("pets", []) if pet["name"] != "Unknown"]
        pet_names_str = ", ".join(pet_names) if pet_names else "your pet"
        
        if pet_context["has_pets"] and not pet_context["needs_basic_info"]:
            # User has complete pet info - ask CONTEXTUAL questions about the photo
            if user_message:
                prompt = f"""The user says: "{user_message}" and shared an image. 

You are Mr. White, a friendly dog trainer having a conversation with this user. You already know about their pet(s): {pet_names_str}. The user has told you this is a photo of them with their dog, so acknowledge this as their photo.

Look at the image and respond naturally and conversationally. Acknowledge what you see in the photo, then ask 2-3 engaging questions about the moment. For example:
- "What a lovely photo of you and {pet_names_str}! You both look so happy together."  
- "Where did you take this photo? It looks like a wonderful spot for you and {pet_names_str}."
- "What were you both up to in this moment? {pet_names_str} looks like they're having such a great time!"

Be warm, personal, and genuinely interested in their story. Use "you" and "your" when referring to the user since they've told you this is their photo. Avoid clinical language, structured lists, or overly cautious statements about identifying people."""
            else:
                prompt = f"""The user shared an image and has pet(s): {pet_names_str}.

You are Mr. White, a friendly dog trainer. Since you already know their pet details, focus on having a natural conversation about THIS SPECIFIC PHOTO/MOMENT.

Look at the image and respond warmly and conversationally. Acknowledge what you see, then ask 2-3 engaging questions about the moment. For example:
- "What a wonderful photo of you and {pet_names_str}! Where did you take this?"
- "I love seeing you both together - what were you up to in this moment?"
- "This looks like such a special time! What's the story behind this photo?"

Be warm, personal, and genuinely interested in their story. Use "you" and "your" when referring to the user. Avoid clinical language, structured lists, or overly cautious statements about identifying people."""

        elif pet_context["has_pets"] and pet_context["needs_basic_info"]:
            # User has pets but missing basic info - ALWAYS acknowledge user message first
            missing_fields = []
            for pet in pet_context["pets"]:
                missing_fields.extend(pet.get("missing_basic_fields", []))
            missing_fields = list(set(missing_fields))  # Remove duplicates
            
            if user_message:
                prompt = f"""The user says: "{user_message}" and shared an image. 

You are Mr. White, a friendly dog trainer. FIRST: Acknowledge what they told you and respond to their message directly.

THEN: Ask 1-2 follow-up questions naturally, balancing any missing pet info with photo context:
- If missing basic info: ask 1 question about {', '.join(missing_fields[:2]) if missing_fields else 'pet details'}
- Ask 1-2 questions about this photo: "Where did you take this?" or "What's happening in this moment?"

Be conversational, warm, and personal. Use "you" and "your" when referring to the user. Avoid structured lists or clinical language."""
            else:
                prompt = f"""The user shared an image and has pet(s) with some missing basic info.

Ask 1 question about missing basic info ({', '.join(missing_fields[:2]) if missing_fields else 'pet details'}), then 1-2 questions about the photo context:

Example structure:
• "I'd love to know more about {pet_names_str} - what breed are they?" (if breed missing)
• "Where was this photo taken? It looks like a beautiful spot!"
• "What's the story behind this moment?"

Balance learning about their pet with understanding this specific photo."""

        else:
            # No pet info - ask basic questions first
            if user_message:
                prompt = f"""The user says: "{user_message}" and shared an image.

You are Mr. White, a friendly dog trainer. FIRST: Acknowledge what they told you and respond to their message directly.

THEN: Ask 2-3 follow-up questions naturally to learn both basic pet info AND photo context:
- Basic pet info: "What's your dog's name and breed?"
- Photo context: "Where did you take this photo?" or "What's the story behind this moment?"

Be conversational, warm, and personal. Use "you" and "your" when referring to the user. Avoid structured lists or clinical language."""
            else:
                prompt = """You are Mr. White, a friendly dog trainer. The user shared an image but you don't know about their pets yet.

Ask 2-3 questions naturally to learn both basic pet info AND photo context:
- "What's your pet's name and breed?"
- "Where did you take this photo?"
- "What's the story behind this moment?"

Be conversational, warm, and personal. Use "you" and "your" when referring to the user. Avoid structured lists or clinical language."""

        return prompt
    
    async def _store_image_analysis_in_vector_db(
        self,
        user_id: int,
        image_id: int,
        filename: str,
        description: str,
        analysis_data: Dict[str, Any],
        s3_url: str,
        conversation_id: Optional[int] = None
    ):
        """Store image analysis in vector database for future retrieval"""
        try:
            # Extract analysis text content for vector storage
            analysis_text = description
            
            # Extract additional context from analysis_data if available
            content_analysis = analysis_data.get("content_analysis", "")
            objects_detected = analysis_data.get("objects_detected", [])
            colors_detected = analysis_data.get("colors_detected", [])
            
            # Build comprehensive text for vector storage
            vector_text_parts = [
                f"Image Analysis: {analysis_text}",
                f"Filename: {filename}",
            ]
            
            if content_analysis:
                vector_text_parts.append(f"Content: {content_analysis}")
            
            if objects_detected:
                vector_text_parts.append(f"Objects: {', '.join(objects_detected)}")
                
            if colors_detected:
                vector_text_parts.append(f"Colors: {', '.join(colors_detected)}")
            
            # Combine all text
            vector_text = " | ".join(vector_text_parts)
            
            # Create metadata for the vector record
            vector_metadata = {
                "type": "image_memory",
                "user_id": user_id,
                "image_id": image_id,
                "s3_url": s3_url,
                "filename": filename,
                "conversation_id": conversation_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "description": description,
                "objects": objects_detected,
                "colors": colors_detected
            }
            
            # Store in vector database
            success, message = await self.vector_service.store_document_vectors(
                user_id=user_id,
                document_id=f"image_{image_id}_{int(datetime.now().timestamp())}",
                text_chunks=[vector_text],
                metadata=vector_metadata
            )
            
            if success:
                logger.info(f"✅ Image analysis stored in vector DB: user={user_id}, image_id={image_id}")
            else:
                logger.warning(f"⚠️ Failed to store image analysis in vector DB: {message}")
                
        except Exception as e:
            logger.error(f"❌ Error storing image analysis in vector DB: {str(e)}")
    
    def _resize_image_if_needed(self, image_content: bytes, max_dimension: int = 7500) -> bytes:
        """
        Resize image if either dimension exceeds the max_dimension limit.
        AWS Bedrock has a limit of 8000px, so we use 7500px as a safe margin.
        
        Args:
            image_content: Raw image bytes
            max_dimension: Maximum allowed dimension in pixels
            
        Returns:
            Resized image bytes (or original if no resize needed)
        """
        try:
            # Open image from bytes
            image = PILImage.open(io.BytesIO(image_content))
            original_width, original_height = image.size
            
            # Check if resize is needed
            if original_width <= max_dimension and original_height <= max_dimension:
                # No resize needed
                return image_content
            
            # Calculate new dimensions while maintaining aspect ratio
            if original_width > original_height:
                # Width is the limiting dimension
                new_width = max_dimension
                new_height = int((original_height * max_dimension) / original_width)
            else:
                # Height is the limiting dimension
                new_height = max_dimension
                new_width = int((original_width * max_dimension) / original_height)
            
            # Resize image (use LANCZOS for high quality, with fallback for older PIL versions)
            try:
                resized_image = image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            except AttributeError:
                # Fallback for older PIL versions
                resized_image = image.resize((new_width, new_height), PILImage.LANCZOS)
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            # Preserve original format if possible, otherwise use PNG
            format_to_use = image.format if image.format in ['JPEG', 'PNG', 'WEBP'] else 'PNG'
            resized_image.save(output_buffer, format=format_to_use, quality=85, optimize=True)
            
            logger.info(f"🖼️ Resized image from {original_width}x{original_height} to {new_width}x{new_height}")
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Error resizing image: {str(e)}")
            # Return original image if resize fails
            return image_content
    
    async def analyze_image_with_bedrock(self, image_content: bytes, content_type: str, user_message: str = "", user_id: int = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Analyze image using AWS Bedrock Claude vision
        
        Args:
            image_content: Raw image bytes
            content_type: MIME type of the image
            user_message: Optional user message for context
            
        Returns:
            Tuple of (success, description, analysis_metadata)
        """
        try:
            # Resize image if it's too large for Bedrock (8000px limit)
            resized_image_content = self._resize_image_if_needed(image_content)
            
            # Convert to base64
            base64_image = base64.b64encode(resized_image_content).decode('utf-8')
            
            # Get pet context for smart questioning
            pet_context = {"has_pets": False, "pets": [], "needs_basic_info": False}
            if user_id:
                pet_context = await self._get_user_pet_context_for_vision(user_id)
            
            # Generate context-aware prompts
            prompt = await self._generate_smart_vision_prompt(user_message, pet_context)

            # Get Bedrock client from the pool
            openai_pool = await self._get_openai_pool()
            async with openai_pool.get_client() as client:
                # Use Bedrock's invoke_model for Claude vision
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": content_type,
                                        "data": base64_image
                                    }
                                }
                            ]
                        }
                    ]
                }
                
                # Call Bedrock Claude vision model
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.invoke_model(
                        modelId=self.vision_model,
                        body=json.dumps(body),
                        contentType="application/json"
                    )
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                description = response_body['content'][0]['text']
            
            # Extract analysis metadata
            analysis_data = {
                'model_used': self.vision_model,
                'input_tokens': response_body.get('usage', {}).get('input_tokens', 0),
                'output_tokens': response_body.get('usage', {}).get('output_tokens', 0),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'confidence': 'high',
                'user_message_provided': bool(user_message),
                'service': 'aws_bedrock_claude'
            }
            
            self.processing_stats["successful_analyses"] += 1
            logger.info(f"✅ Bedrock Claude image analysis successful: {len(description)} characters")
            return True, description, analysis_data
            
        except Exception as e:
            self.processing_stats["failed_analyses"] += 1
            error_message = str(e)
            logger.error(f"❌ Error analyzing image with Bedrock: {error_message}")
            
            # Provide user-friendly error messages
            if "exceed max allowed size" in error_message:
                user_friendly_message = "The image you uploaded is too large. The image has been automatically resized, but there was still an issue. Please try uploading a smaller image or a different format."
            elif "content filtering" in error_message.lower():
                user_friendly_message = "I'm unable to analyze this image due to content restrictions. Please try uploading a different image."
            elif "format not supported" in error_message.lower():
                user_friendly_message = "The image format you uploaded is not supported. Please try uploading a JPEG, PNG, or WebP image."
            else:
                user_friendly_message = f"I encountered an issue while analyzing your image. Please try uploading a different image or try again later."
            
            return False, user_friendly_message, {}
    
    def _extract_image_metadata(self, image_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract metadata from image"""
        try:
            # Get file size
            file_size = len(image_content)
            
            # Get image dimensions and format
            image = PILImage.open(io.BytesIO(image_content))
            
            metadata = {
                'file_size': file_size,
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode,
                'filename': filename
            }
            
            # Try to get EXIF data
            try:
                exif = image._getexif()
                metadata['has_exif'] = bool(exif)
            except:
                metadata['has_exif'] = False
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error extracting image metadata: {str(e)}")
            return {'file_size': len(image_content), 'error': str(e)}
    
    async def store_image_to_gallery(
        self, 
        user_id: int, 
        image_content: bytes, 
        filename: str, 
        content_type: str,
        description: str,
        analysis_data: Dict[str, Any],
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Store image to gallery (user_images table) and S3
        
        Args:
            user_id: User ID
            image_content: Raw image bytes
            filename: Original filename
            content_type: MIME type
            description: AI analysis or user description
            analysis_data: OpenAI analysis metadata
            conversation_id: Optional conversation context
            message_id: Optional message context
            
        Returns:
            Dictionary with success status and image data
        """
        try:
            # Generate unique filename for S3
            file_extension = filename.split('.')[-1].lower()
            unique_filename = f"upload_{uuid.uuid4()}.{file_extension}"
            
            # Upload to S3
            s3_result = await self.s3_service.upload_image_to_s3(
                file_content=image_content,
                filename=unique_filename,
                user_id=user_id,
                content_type=content_type
            )
            
            if not s3_result.get("success"):
                logger.error(f"❌ S3 upload failed: {s3_result.get('error')}")
                return {"success": False, "error": "Failed to upload image to storage"}
            
            # Extract image metadata
            image_metadata = self._extract_image_metadata(image_content, filename)
            
            # Get next display order
            async with AsyncSessionLocal() as session:
                # Get current max display order for user
                max_order_query = select(UserImage.display_order).where(
                    UserImage.user_id == user_id,
                    UserImage.is_deleted == False
                ).order_by(UserImage.display_order.desc()).limit(1)
                
                result = await session.execute(max_order_query)
                max_order = result.scalar()
                next_order = (max_order or 0) + 1
                
                # Create UserImage record
                image_record = UserImage(
                    user_id=user_id,
                    filename=unique_filename,
                    original_filename=filename,
                    s3_url=s3_result["download_url"],
                    s3_key=s3_result["s3_key"],
                    description=description,
                    analysis_data=analysis_data,
                    image_metadata=image_metadata,
                    display_order=next_order,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(image_record)
                await session.commit()
                await session.refresh(image_record)
                
                # Store image analysis in vector database for future retrieval
                await self._store_image_analysis_in_vector_db(
                    user_id=user_id,
                    image_id=image_record.id,
                    filename=filename,
                    description=description,
                    analysis_data=analysis_data,
                    s3_url=s3_result["download_url"],
                    conversation_id=conversation_id
                )
                
                self.processing_stats["gallery_saves"] += 1
                logger.info(f"✅ Image saved to gallery: user={user_id}, id={image_record.id}")
                
                return {
                    "success": True,
                    "image_id": image_record.id,
                    "s3_url": s3_result["download_url"],
                    "description": description,
                    "metadata": image_metadata
                }
                
        except Exception as e:
            logger.error(f"❌ Error storing image to gallery: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def process_vision_request(
        self, 
        user_id: int, 
        user_message: str, 
        images: List[Dict[str, Any]], 
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a vision request with images and optional user message
        
        Args:
            user_id: User ID
            user_message: User's text message (can be empty)
            images: List of image dictionaries with content, filename, content_type
            conversation_id: Optional conversation context
            message_id: Optional message context
            
        Returns:
            Dictionary with AI response and processed images info
        """
        try:
            self.processing_stats["total_images_processed"] += len(images)
            
            processed_images = []
            ai_responses = []
            
            for image_dict in images:
                try:
                    # Extract image data
                    if isinstance(image_dict.get('content'), str):
                        # Base64 encoded content
                        image_content = base64.b64decode(image_dict['content'])
                    else:
                        # Raw bytes
                        image_content = image_dict['content']
                    
                    filename = image_dict.get('filename', 'image.jpg')
                    content_type = image_dict.get('content_type', 'image/jpeg')
                    
                    # Analyze image with Bedrock Claude Vision
                    success, analysis, analysis_data = await self.analyze_image_with_bedrock(
                        image_content, content_type, user_message, user_id
                    )
                    
                    if not success:
                        logger.error(f"❌ Vision analysis failed for {filename}: {analysis}")
                        continue
                    
                    # Determine description for gallery
                    if user_message.strip():
                        # User provided message - use it as description
                        gallery_description = user_message.strip()
                        # AI response acknowledges both message and image
                        ai_response = analysis
                    else:
                        # No user message - use AI analysis as description
                        gallery_description = analysis
                        # AI response is the analysis itself
                        ai_response = analysis
                    
                    # Store to gallery
                    storage_result = await self.store_image_to_gallery(
                        user_id=user_id,
                        image_content=image_content,
                        filename=filename,
                        content_type=content_type,
                        description=gallery_description,
                        analysis_data=analysis_data,
                        conversation_id=conversation_id,
                        message_id=message_id
                    )
                    
                    if storage_result.get("success"):
                        processed_images.append({
                            "filename": filename,
                            "image_id": storage_result["image_id"],
                            "s3_url": storage_result["s3_url"],
                            "description": gallery_description,
                            "analysis": analysis
                        })
                        ai_responses.append(ai_response)
                    else:
                        logger.error(f"❌ Failed to store image {filename}: {storage_result.get('error')}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing image {image_dict.get('filename', 'unknown')}: {str(e)}")
                    continue
            
            # Generate combined AI response
            if ai_responses:
                if len(ai_responses) == 1:
                    combined_response = ai_responses[0]
                else:
                    combined_response = "I can see the images you've shared:\n\n" + "\n\n".join([
                        f"Image {i+1}: {response}" for i, response in enumerate(ai_responses)
                    ])
            else:
                combined_response = "I apologize, but I wasn't able to analyze the images you shared. Please try again."
            
            # GALLERY LINK ENHANCEMENT: Add gallery link if images were successfully processed and not shown before
            logger.info(f"🖼️ GALLERY DEBUG: processed_images={len(processed_images) if processed_images else 0}, conversation_id={conversation_id}, cache_service_available={self.cache_service is not None}")
            
            if processed_images and conversation_id:
                try:
                    # Check if gallery link was already shown in this conversation
                    gallery_link_shown = await self._check_gallery_link_shown(conversation_id)
                    logger.info(f"🖼️ GALLERY DEBUG: gallery_link_shown={gallery_link_shown} for conversation {conversation_id}")
                    
                    if not gallery_link_shown:
                        # Generate and append gallery link message
                        gallery_message = self._generate_gallery_link_message(len(processed_images))
                        combined_response += gallery_message
                        
                        # Mark gallery link as shown for this conversation
                        mark_result = await self._mark_gallery_link_shown(conversation_id)
                        logger.info(f"🖼️ Added gallery link to vision response for conversation {conversation_id}, mark_result={mark_result}")
                    else:
                        logger.info(f"🖼️ Gallery link already shown for conversation {conversation_id}, skipping")
                except Exception as e:
                    logger.error(f"❌ Error adding gallery link to vision response: {str(e)}")
                    # Continue without gallery link if there's an error
            elif not conversation_id:
                logger.warning(f"🖼️ GALLERY DEBUG: No conversation_id provided, cannot track gallery link display")
            elif not processed_images:
                logger.info(f"🖼️ GALLERY DEBUG: No processed images, skipping gallery link")
            
            return {
                "success": True,
                "content": combined_response,
                "processed_images": processed_images,
                "images_count": len(processed_images),
                "processing_stats": {
                    "total_processed": len(images),
                    "successful": len(processed_images),
                    "failed": len(images) - len(processed_images)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in process_vision_request: {str(e)}")
            return {
                "success": False,
                "content": "I apologize, but I encountered an error processing your images. Please try again.",
                "error": str(e)
            }
    
    async def update_image_message_ids(self, image_ids: List[int], user_message_id: int, ai_message_id: int) -> bool:
        """
        Update user_images table with message IDs after messages are saved
        
        Args:
            image_ids: List of image IDs from user_images table
            user_message_id: ID of the user message that uploaded the images
            ai_message_id: ID of the AI response message
            
        Returns:
            bool: Success status
        """
        try:
            from models import AsyncSessionLocal, UserImage
            from sqlalchemy import update
            
            async with AsyncSessionLocal() as session:
                # Update all images with the user message ID (the message that uploaded them)
                for image_id in image_ids:
                    await session.execute(
                        update(UserImage)
                        .where(UserImage.id == image_id)
                        .values(message_id=user_message_id)
                    )
                
                await session.commit()
                logger.info(f"✅ Updated {len(image_ids)} images with message_id {user_message_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating image message IDs: {str(e)}")
            return False

    async def _check_gallery_link_shown(self, conversation_id: Optional[int]) -> bool:
        """
        Check if gallery link has already been shown in this conversation
        
        Args:
            conversation_id: Optional conversation ID
            
        Returns:
            bool: True if gallery link was already shown
        """
        if not conversation_id:
            logger.warning(f"🖼️ CACHE DEBUG: No conversation_id provided for gallery link check")
            return False
            
        if not self.cache_service:
            logger.warning(f"🖼️ CACHE DEBUG: No cache_service available for gallery link check")
            return False
            
        try:
            cache_key = f"gallery_link_shown:conversation_{conversation_id}"
            logger.info(f"🖼️ CACHE DEBUG: Checking cache key: {cache_key}")
            result = await self.cache_service.get(cache_key)
            shown = result is not None
            logger.info(f"🖼️ CACHE DEBUG: Gallery link shown check for conv {conversation_id}: {shown}, cache_result={result}")
            return shown
        except Exception as e:
            logger.error(f"❌ Error checking gallery link status: {str(e)}")
            return False
    
    async def _mark_gallery_link_shown(self, conversation_id: Optional[int]) -> bool:
        """
        Mark gallery link as shown for this conversation
        
        Args:
            conversation_id: Optional conversation ID
            
        Returns:
            bool: Success status
        """
        if not conversation_id:
            logger.warning(f"🖼️ CACHE DEBUG: No conversation_id provided for marking gallery link")
            return False
            
        if not self.cache_service:
            logger.warning(f"🖼️ CACHE DEBUG: No cache_service available for marking gallery link")
            return False
            
        try:
            cache_key = f"gallery_link_shown:conversation_{conversation_id}"
            logger.info(f"🖼️ CACHE DEBUG: Setting cache key: {cache_key} with 24h expiration")
            # Set with 24 hour expiration (conversation lifetime)
            await self.cache_service.set(cache_key, "shown", ttl=86400)
            logger.info(f"🖼️ CACHE DEBUG: Successfully marked gallery link as shown for conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error marking gallery link as shown: {str(e)}")
            return False
    
    def _generate_gallery_link_message(self, images_count: int = 1) -> str:
        """
        Generate gallery link message for vision responses
        
        Args:
            images_count: Number of images processed
            
        Returns:
            str: Gallery link message
        """
        if images_count == 1:
            intro = "🖼️ **Your image has been saved to your personal gallery!**"
        else:
            intro = f"🖼️ **Your {images_count} images have been saved to your personal gallery!**"
        
        return f"""

{intro}

Visit your **[Gallery](/gallery)** to:
• View all your uploaded images in one organized place
• Create folders to organize your pet photos  
• Search through images by description or filename
• Edit image titles and descriptions
• Reorder images in your preferred sequence
• View detailed upload statistics

*Explore your complete photo collection with powerful management tools.*"""

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get vision service processing statistics"""
        return {
            "vision_service_stats": self.processing_stats,
            "s3_service_stats": self.s3_service.get_upload_stats() if hasattr(self.s3_service, 'get_upload_stats') else {}
        }
